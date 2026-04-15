# RAG vs PAG

I replaced the "LLM synthesizes your answer" step of a RAG pipeline with a
deterministic rule artifact — a "pearl" from
[LogicPearl](https://github.com/LogicPearlHQ/logicpearl) — and ran both
against the same FOIA corpus on 15 scenarios.

Calling the pattern **PAG — Pearl-Augmented Generation**. RAG extends an
LLM with what's retrieved from documents. PAG extends it with a reviewed,
deterministic rule artifact. One adds recall to an LLM; the other adds
reviewed judgment. The LLM writes the surrounding prose; the pearl makes
the call.

Same model (gpt-4o, temp=0), same corpus (5 U.S.C. § 552 + DOJ OIP FOIA
Guide + 28 C.F.R. Part 16), same scenarios, three backends.

| | RAG | PAG (LLM extract) | PAG (keyword extract) |
|---|---|---|---|
| Correct | 45/45 (100%) | 42/45 (93%) | 42/45 (93%) |
| **Byte-identical reruns** | 25/45 | 20/45 | **45/45** |
| **Citation faithfulness** | **70/94 (74%)** | **57/57 (100%)** | **72/72 (100%)** |
| LLM calls / scenario | 1 | 2 | **0** |
| Latency | 3.7 s | 3.8 s | **<1 ms** |
| Marginal cost / run | ~$0.01 | ~$0.005 | **$0** |

RAG wins correctness. PAG wins everything else. The rightmost column —
PAG with a keyword extractor — runs end-to-end without an LLM at all.

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

## PAG's three misses were on purpose

Both PAG modes scored 42/45. All three misses on each side are **one
scenario failing three times** — the decision determinism working as
intended, wrong answer included.

**PAG-LLM misses scenario 15:** *"Summarize the legislative history of
FOIA Exemption 5 and the two Supreme Court opinions most responsible
for shaping its current scope."*

That's a synthesis task. PAG is a classifier. I put it in the eval to
probe the boundary. Drop scenario 15 and PAG-LLM scores 45/45. I kept
it because "use each tool for what it's for" is a more honest pitch
than "PAG wins everything." RAG got this one by using its
`insufficient_context` refusal path — which is what you want for a
synthesis request.

**PAG-keyword misses scenario 14:** *"...would not reveal a confidential
source... would not disclose techniques..."*.

Substring match fires on `confidential source` and `disclose
techniques` without understanding the negation. A wider
`negative_keywords` list (add `"would not reveal"`, `"would not
disclose"`) or a dependency-parse negation scope fixes it.

In both cases the wrongness has a locatable cause you can point at and
fix. RAG's 24 fabrications are spread across scenarios it answered
*correctly* and have no cause beyond "LLM wrote plausible text."

## How PAG works

```
RAG:            text → retrieve 8 chunks → LLM synthesizes + cites
PAG (LLM):      text → LLM extracts {feature: bool} → pearl decides → LLM explains (can't override)
PAG (keyword):  text → substring match → pearl decides → Python template rationale
```

The pearl is a compiled Rust rule evaluator. 10 ms per scenario. Zero
LLM calls — that part is provably deterministic. The LLM (in the first
PAG mode) only turns free text into a feature vector on the way in, and
turns the pearl's rule output into prose on the way out. The code
architecturally overwrites any verdict the LLM tries to assert in the
explanation — the pearl's action is authoritative.

Keyword-mode PAG cuts the LLM out of both ends. ~50-line substring
matcher for extraction, Python string template for the rationale.
Microsecond latency, no network, no API key after the build.

The pearl's rules aren't hand-written. They're learned from a trace set
**generated from the statute itself**:
[`pearl/statute_structure.json`](pearl/statute_structure.json) lists
the element groups per exemption, each with a verbatim quote from
§ 552(b). A test asserts every quote is a real substring of the fetched
statute. No trace row is typed by hand.

## Quick start

```bash
git clone git@github.com:LogicPearlHQ/rag-vs-pag.git
cd rag-vs-pag
uv sync --extra dev
cp .env.example .env         # OPENAI_API_KEY
make fetch index build demo  # ~10 min, ~$0.50 of gpt-4o tokens
```

For just the offline keyword-mode PAG (no API key needed after build):

```bash
uv run python compare.py --pearl-extractor keyword --skip-rag --repeat 3
```

Captured runs are in [`transcripts/`](transcripts/). Long-form writeup
with every prompt verbatim and full failure-mode analysis in
[`docs/findings.md`](docs/findings.md).

## Limitations worth naming

- **15 scenarios is small.** Percentages are robust only qualitatively.
- **Pedagogical corpus.** Statute + 9 DOJ Guide chapters + 28 CFR
  Part 16. No case law (CourtListener's API now requires a token). Real
  FOIA adjudication involves segregability, foreseeable-harm balancing,
  and case-law nuance the trace set doesn't encode.
- **RAG didn't get a second refinement pass.** The PAG did (one
  commit's worth of trace expansion after the first run surfaced a
  greedy-rule issue). A serious RAG team can probably push citation
  faithfulness toward 100% by having the LLM reference chunk IDs
  instead of writing excerpts, then looking up the excerpt
  server-side. That's a real architecture and it works. The point
  isn't that RAG can't be fixed — it's that PAG's 100% is one line of
  code and RAG's 100% is custom scaffolding.
- **Scenario 14 was swapped between the first and second runs.** The
  original asked for `insufficient_context` as the gold label, which
  neither system could produce without a preflight LLM-judgment step
  that would have undermined the demo's own thesis. Both systems got
  equal credit from the swap; the swap is documented in
  [`docs/findings.md`](docs/findings.md).
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

## Credits and built on

- **[LogicPearl](https://github.com/LogicPearlHQ/logicpearl)** — the
  deterministic rule engine and `logicpearl` CLI.
- Corpus fetched from
  [law.cornell.edu](https://www.law.cornell.edu/uscode/text/5/552),
  [justice.gov/oip/foia-guide](https://www.justice.gov/oip/foia-guide),
  [ecfr.gov](https://www.ecfr.gov/). Federal works are public domain.
- `gpt-4o` for the demo LLM calls at temp=0. Same results shape on
  Claude or local Ollama.
