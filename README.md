# RAG vs PAG

**Disclosure:** I work on [LogicPearl](https://github.com/LogicPearlHQ/logicpearl).
This demo exercises it against a classic RAG baseline. All code, scenarios,
trace generator, and captured transcripts are in this repo — the eval is
fully reproducible.

I replaced the "LLM synthesizes your answer" step of a RAG pipeline with a
deterministic rule artifact — a "pearl" from LogicPearl — and ran both
against the same FOIA corpus on 15 scenarios.

**PAG — Pearl-Augmented Generation.** RAG extends an LLM with what's
retrieved from documents. PAG extends it with a reviewed, deterministic
rule artifact. One adds recall to an LLM; the other adds reviewed
judgment. The LLM writes the surrounding prose; the pearl makes the call.

This is a demonstration of a pattern, not a statistical benchmark. 15
scenarios on one corpus won't tell you anything significant on its own —
the value is being able to inspect the whole pipeline end-to-end, run it
yourself, and swap in your own corpus and scenarios.

Same model (gpt-4o, temp=0), same corpus (5 U.S.C. § 552 + DOJ OIP FOIA
Guide + 28 C.F.R. Part 16), same scenarios, three backends.

| | RAG | PAG (LLM extract) | PAG (keyword extract) |
|---|---|---|---|
| Correct | 45/45 (100%) | 42/45 (93%) | 42/45 (93%) |
| Byte-identical reruns | 25/45 | 20/45 | 45/45 |
| **Citation faithfulness** | **70/94 (74%)** | **57/57 (100%)** | **72/72 (100%)** |
| LLM calls / scenario | 1 | 2 | 0 |
| Latency | 3.7 s | 3.8 s | <1 ms |
| Marginal cost / run | ~$0.01 | ~$0.005 | $0 |

The RAG baseline is specifically: hybrid BM25 + dense embeddings
(text-embedding-3-small), cross-encoder rerank (ms-marco-MiniLM-L-6-v2),
top-k=8, strict-JSON output with citations required, refusal path
(`insufficient_context`) when retrieval doesn't support a confident
answer. No agentic scaffolding — deliberately, to keep the comparison
legible.

**A stronger RAG implementation can reach 100% citation faithfulness.**
Have the LLM reference chunk IDs instead of writing excerpts, then look
up the excerpt server-side (Cohere, LangChain, and Anthropic Citations
all do versions of this). That's real engineering and it works. The
point here isn't that RAG can't be fixed — it's that PAG's 100% is
structural: citations come from a lookup table, one line of code. RAG's
100% is custom scaffolding you'd build and maintain per pipeline.

## The metric that actually matters

"Correct" and "citations are real" aren't the same question. A system
can answer correctly with excerpts it made up.

24 of RAG's 94 citations in this run are **not substrings of the
retrieved text**. The LLM wrote convincing quotes that don't exist.
Caught only by a post-hoc substring check — a human skimming the output
wouldn't flag any of them.

Three of them, verbatim from the run:

### 1. Ellipsis compression

Cited as one passage from 5 U.S.C. § 552(b)(7):

> *records or information compiled for law enforcement purposes, but
> only to the extent that the production of such law enforcement
> records or information**...** (D) could reasonably be expected to
> disclose...*

The `...` hides the whole of subclauses (A)(B)(C) — hundreds of words of
statute. The "quote" is a stitch-up.

### 2. Plausible fabrication

Cited as `DOJ FOIA Guide, Exemption 6, p. 14`:

> *Similarly, civilian federal employees who are not involved in law
> enforcement generally have no expectation of privacy regarding their
> names, titles, grades, salaries, and duty stations...*

Clean. On topic. Real page number. Not actually on page 14 of what the
retrieval fetched. The LLM pulled from training data (the DOJ Guide is
public) instead of the retrieved chunk.

### 3. Memory-mixed

Cited as `DOJ FOIA Guide, Exemption 3, p. 40`:

> *Exemption 3 or return information of other taxpayers. Specifically,
> section 6103 provides that '[r]eturns and return information shall be
> confidential,' subject to a number of enumerated exceptions.*

Page 40 was retrieved — the real text was in the LLM's context. It
ignored the retrieved text and wrote its own phrasing that blends with
what it remembers. Not a substring of anything retrieved.

All three look credible. All three would slip past a human reviewer.

PAG's citations come from a lookup table built from the feature
dictionary, so every one is a real substring by construction. No prompt
engineering, no retry loop, no self-critique.

## PAG's three misses

Both PAG modes scored 42/45. All three misses on each side are **one
scenario failing three times** — the decision determinism working as
intended, wrong answer included.

**Scenario 15** — *"Summarize the legislative history of FOIA
Exemption 5 and the two Supreme Court opinions most responsible for
shaping its current scope."*

Both systems correctly recognized this isn't a classification request.
RAG returned `insufficient_context` (its JSON schema's refusal code),
which the gold label accepts. PAG-LLM misclassified it — the feature
extractor got fooled by the prompt mentioning "Exemption 5" and set
(b)(5) features TRUE, so the pearl faithfully applied its (b)(5) rule
to a record that didn't exist. Keeping scenario 15 in the eval rather
than dropping it (which would score PAG-LLM at 45/45) is a deliberate
hedge against cherry-picking — synthesis tasks are RAG's job, not
PAG's, and the eval should reflect that.

**Scenario 14** — *"...would not reveal a confidential source... would
not disclose techniques..."*.

PAG-keyword fires on the substrings `confidential source` and
`disclose techniques` without scoping the negation. Fixable by
widening the `negative_keywords` list or by using a negation-aware
parser. Not a fundamental ceiling.

Both PAG misses have a locatable, fixable cause. RAG's 24 fabrications
are spread across scenarios it answered *correctly* and have no cause
beyond "the LLM wrote plausible text."

## How PAG works

```
RAG:            text → retrieve 8 chunks → LLM synthesizes + cites
PAG (LLM):      text → LLM extracts {feature: bool} → pearl decides → LLM explains (can't override)
PAG (keyword):  text → substring match → pearl decides → Python template rationale
```

The pearl is a compiled Rust rule evaluator. 10 ms per scenario. Zero
LLM calls — that part is provably deterministic. The LLM (in the first
PAG mode) only turns free text into a feature vector on the way in and
turns the pearl's rule output into prose on the way out. The code
architecturally overwrites any verdict the LLM tries to assert in the
explanation — the pearl's action is authoritative.

For the demo the pearl runs as a subprocess (`logicpearl run ...`) once
per scenario. In production you'd use the library directly; the
subprocess is fine for 15 scenarios and isn't the latency bottleneck.

Keyword-mode PAG removes the LLM from both ends. ~50-line substring
matcher for extraction, Python string template for the rationale.
Microsecond latency, no network, no API key after the build.

## What a pearl is (and isn't)

Two existing ways to put deterministic decisions under an LLM:

- **Hand-written rule code** (OPA/Rego, decision tables, hardcoded
  `if` ladders). Works. Problem: who wrote the rules, did they match
  actual reviewed behavior, how do you diff a rule change across
  deployments?
- **Fine-tuned classifiers** (BERT etc.). Deterministic once trained.
  Problem: opaque weights, no citation surface, no provenance you
  can show in an audit.

A LogicPearl pearl is the middle ground: rules **learned from labeled
examples**, compiled into a small artifact bundle with:

- explicit, inspectable rules (`logicpearl inspect`)
- byte-level manifest + sha256 hashes (verify integrity before deploy)
- semantic diffs between artifact versions (`logicpearl diff`)
- compile targets (native, Wasm) for embedding in other runtimes
- no LLM in the runtime

In this demo the "labeled examples" are statute-derived: every trace
row is generated from
[`pearl/statute_structure.json`](pearl/statute_structure.json), whose
entries each carry a verbatim quote from § 552(b). A test asserts every
quote is a real substring of the fetched statute. LogicPearl also
supports **behavior-derived** pearls (distilled from reviewed past
decisions — the original garden-actions demo in the main repo is that).

## Audit it yourself

The whole trust surface is ~40 lines of JSON + 15 scenarios + one
generator script:

- [`pearl/feature_dictionary.json`](pearl/feature_dictionary.json) — 20
  features, each with a statute cite and (optionally) keyword triggers.
- [`pearl/statute_structure.json`](pearl/statute_structure.json) —
  element groups per exemption, each with a verbatim statute quote
  that's auto-verified as a substring of the fetched statute.
- [`scenarios/*.json`](scenarios/) — 15 record descriptions with gold
  labels.
- [`pearl/generate_traces.py`](pearl/generate_traces.py) — produces the
  CSV the pearl learns from. Deterministic; idempotence is tested.

Flip a row, change a quote, swap a scenario — the whole eval rebuilds
in ~30 seconds for PAG, a few minutes for the full RAG + PAG sweep.
If you think the comparison is rigged, this is where you'd look.

## Quick start

```bash
git clone git@github.com:LogicPearlHQ/rag-vs-pag.git
cd rag-vs-pag
uv sync --extra dev
cp .env.example .env         # OPENAI_API_KEY
make fetch index build demo  # ~10 min, ~$0.50 of gpt-4o tokens
```

For just the offline keyword-mode PAG (no API key after build):

```bash
uv run python compare.py --pearl-extractor keyword --skip-rag --repeat 3
```

Captured runs are in [`transcripts/`](transcripts/). Long-form writeup
with every prompt verbatim and full failure-mode analysis in
[`docs/findings.md`](docs/findings.md).

## Scope: when PAG pays for itself

PAG is useful when decisions need to be **bounded, auditable, and
reproducible**. You trade domain generality for those properties. If
your questions are open-ended synthesis, use RAG. If they're bounded
classifications in a regulated domain — refunds, eligibility, access,
compliance, triage, routing — PAG is worth the pearl-building effort.

The cost: one pearl per domain. RAG scales to new documents for free.
PAG's rule artifact has to be rebuilt when the underlying behavior
shifts. You pay once per domain, not per query.

Byte-identical reruns aren't worth the engineering cost for most LLM
use cases. They are worth it for regulated audits (legal, medical,
financial, defense) where the same input producing the same output on
the same hash is a compliance requirement, not a nicety.

## Limitations

- **15 scenarios is small.** This is a pattern demo, not a benchmark.
  The percentages are robust only qualitatively.
- **Pedagogical corpus.** Statute + 9 DOJ Guide chapters + 28 CFR
  Part 16. No case law (CourtListener's API now requires a token).
  Real FOIA involves segregability, foreseeable-harm balancing, and
  case-law nuance the trace set doesn't encode.
- **RAG wasn't refined a second time.** PAG got one trace-expansion
  pass after the initial run surfaced a greedy-rule issue. Chunk-ID
  citation lookup would likely push RAG to 100% faithfulness; that
  wasn't implemented.
- **Scenario 14 was swapped between the first and second runs.** The
  original asked for `insufficient_context` as the gold label, which
  neither system could produce without a preflight LLM-judgment layer
  that would undermine the demo's thesis. Equal-treatment change;
  documented in [`docs/findings.md`](docs/findings.md).
- **Only gpt-4o at temp=0.** Provider is pluggable (Anthropic and
  Ollama backends are implemented and smoke-tested), but the full
  15-scenario sweep has only been run on OpenAI. The pipeline topology
  is identical across providers; specific fabrication rates may shift.
- Not legal advice.

## Layout

```
corpus/        fetched federal docs, sha256-verified, snapshot fallback
ragdemo/       shared libs (LLM providers, chunking, scenarios)
rag/           RAG baseline (hybrid retrieval + cross-encoder rerank + citation check)
pearl/         PAG: trace generator, build script, LLM + keyword extractors
scenarios/     15 FOIA record descriptions
compare.py     side-by-side harness
transcripts/   captured runs (one per backend/config)
docs/          design, implementation plan, findings
```

## Pluggable LLM provider

```bash
LP_LLM_PROVIDER=openai          # or anthropic | ollama
LP_LLM_MODEL=gpt-4o
LP_EMBEDDING_PROVIDER=openai    # or sentence_transformers (offline)
LP_PEARL_EXTRACTOR=llm          # or keyword (offline PAG)
```

Local provider with Ollama gets you the full PAG demo with zero API
calls end-to-end.

## Built on

- **[LogicPearl](https://github.com/LogicPearlHQ/logicpearl)** — the
  deterministic rule engine and `logicpearl` CLI.
- Corpus fetched from
  [law.cornell.edu](https://www.law.cornell.edu/uscode/text/5/552),
  [justice.gov/oip/foia-guide](https://www.justice.gov/oip/foia-guide),
  [ecfr.gov](https://www.ecfr.gov/). Federal works are public domain.
- `gpt-4o` for the demo LLM calls.
