# rag-vs-pag — RAG vs Pearl-Augmented Generation

An end-to-end demo on 15 FOIA record-classification scenarios against real
federal primary sources (5 U.S.C. § 552, DOJ OIP FOIA Guide, 28 C.F.R.
Part 16). Same LLM, same corpus, three backends compared side by side.

**PAG = Pearl-Augmented Generation.** RAG extends an LLM with *what's
retrieved from documents* (fetch passages → synthesize). PAG extends it
with *a reviewed, deterministic rule artifact* (extract features →
pearl decides → verdict + cited authority). One adds recall to an LLM;
the other adds reviewed judgment. The LLM generates the surrounding
prose; the pearl makes the call.

## Results

| | **RAG** | **PAG — LLM extract** | **PAG — keyword extract** |
|---|---|---|---|
| Correct | 45 / 45 (100%) | 42 / 45 (93%) | 42 / 45 (93%) |
| **Byte-identical full output** | 25 / 45 (56%) | 20 / 45 (44%) | **45 / 45 (100%)** |
| **Citation faithfulness** | **70 / 94 (74%)** | **57 / 57 (100%)** | **72 / 72 (100%)** |
| LLM calls per scenario | 1 | 2 | **0** |
| Avg latency | 3.7 s | 3.8 s | **<1 ms** |
| Marginal cost per run | ~$0.01 | ~$0.005 | **$0** |

Correctness is comparable on this benchmark. The separators are
**citation faithfulness** (PAG paths are 100% by construction; RAG's 74%
is LLM-bounded) and **full-output reproducibility** (only keyword-extract
PAG achieves 100% byte-identical reruns, because there is no LLM in its
pipeline to drift).

**Full writeup with prompts, all failure modes, and fairness
notes:** [`docs/findings.md`](docs/findings.md).

## Correctness and citation faithfulness are two different questions

**Correctness** — did the system's decision match the scenario's gold
label?

**Citation faithfulness** — does each cited authority actually appear,
as a real substring, in the source it claims to come from? Auto-checked
by normalized-substring match against retrieved chunks (RAG) or the
feature dictionary (PAG).

The two metrics are independent. A system can answer correctly while
citing excerpts that don't exist anywhere in the source. A system can
answer wrong while citing everything faithfully. Production audits care
about both, not just the first. On these 15 scenarios, RAG aced
correctness (45/45) while **24 of its 94 cited excerpts are not real
substrings of the retrieved text**. PAG's cites come from a lookup
table, so every one of them is real by construction.

## What "unfaithful citation" looks like — three real captured examples

Copy-pasted from live RAG runs against the real DOJ FOIA Guide and
statute corpus.

**1. Ellipsis compression** (scenario 07, LE source). RAG cited as a
single continuous passage from `5 U.S.C. § 552(b)(7)`:

> *"records or information compiled for law enforcement purposes, but
> only to the extent that the production of such law enforcement
> records or information**...** (D) could reasonably be expected to
> disclose..."*

The `...` silently elides subclauses (A), (B), and (C) — hundreds of
words of statute text. The stitched-together quote doesn't exist
verbatim anywhere in the statute.

**2. Plausible fabrication from training data** (scenario 13,
personnel roster). Cited as `DOJ FOIA Guide, Exemption 6, p. 14`:

> *"Similarly, civilian federal employees who are not involved in law
> enforcement generally have no expectation of privacy regarding their
> names, titles, grades, salaries, and duty stations as employees."*

Plausible, on-topic, grammatically clean. Not actually on page 14 of
the retrieved chunk. The LLM is recalling from its training data (the
DOJ Guide is public), not quoting the retrieval.

**3. Memory-mixed quote** (scenario 03, tax return). Cited as `DOJ
FOIA Guide, Exemption 3, p. 40`:

> *"Exemption 3 or return information of other taxpayers. Specifically,
> section 6103 provides that '[r]eturns and return information shall
> be confidential,' subject to a number of enumerated exceptions."*

Retrieval actually fetched page 40 — the LLM had real text in context.
Rather than quote it, the LLM blended retrieved content with remembered
phrasing into a new "quote" that reads authoritative but isn't a
substring.

**Common pattern:** all three failures are grammatically clean,
plausible, and paired with real page numbers. A human reader skimming
the output wouldn't flag any of them. Only the automated substring
check catches them.

## Why PAG missed 3 of 45 — and why that's the intended story

Both PAG modes scored 42/45. The 3 misses on each side are **a single
scenario failing across 3 reruns** (decision determinism at work — the
same answer every time, wrong or right).

- **PAG-LLM misses scenario 15** (all 3 reruns). The scenario is:
  *"Summarize the legislative history of FOIA Exemption 5 and the two
  Supreme Court opinions most responsible for shaping its current
  scope."* This is a **synthesis task**, not a classification — PAG is
  for bounded decisions, not for writing paragraphs about legislative
  history. We deliberately included it to test the boundary. The LLM
  feature extractor gets fooled because the prompt mentions *"Exemption
  5"* and confidently sets (b)(5) features TRUE; the pearl then
  faithfully applies its (b)(5) rule to a record that never existed.
  **This is by design.** If you drop scenario 15 from the eval,
  PAG-LLM scores 45/45. We kept it because *"use each tool for what
  it's for"* is a more honest framing than *"PAG wins everything."*
  RAG is the right tool for this prompt — and indeed RAG used its
  `insufficient_context` refusal path on it.

- **PAG-keyword misses scenario 14** (all 3 reruns). The description
  reads *"...would not reveal a confidential source... would not
  disclose techniques..."*. The keyword extractor fires on
  *"confidential source"* and *"disclose techniques"* because
  substring matching doesn't understand negation. Fixable by widening
  the `negative_keywords` lists (e.g., add *"would not reveal"*) or
  by using a negation-aware parser. Not a fundamental ceiling.

The takeaway isn't "PAG would get 45/45 with more effort." The
takeaway is that PAG's wrongness has a **locatable cause** — a
scenario that's out of its design scope, or a specific keyword gap we
can point at and fix. RAG's 24 unfaithful citations are spread across
scenarios it got *right*, and they have no such locatable cause beyond
"the LLM wrote plausible text instead of quoting the retrieval."

## How it works

Three pipelines over the same FOIA corpus:

```
RAG:            text ──► retrieve 8 chunks ──► LLM synthesizes answer + cites

PAG (LLM ext):  text ──► LLM extracts {feature: bool} ──►
                ──► logicpearl run (Rust engine, no LLM) ──► decision ──►
                ──► LLM writes prose (cannot change the verdict)

PAG (keyword):  text ──► keyword substring match ──►
                ──► logicpearl run (Rust engine, no LLM) ──► decision ──►
                ──► Python template rationale
```

The LogicPearl engine at the heart of PAG makes **zero LLM calls** —
it's a compiled rule evaluator in Rust (~10 ms per scenario). The
demo's wrapper around it uses either an LLM or a keyword matcher to
normalize free text into a feature vector. In both modes, the pearl's
verdict is authoritative — the code architecturally prevents any LLM
from overriding it.

## Trust boundary

The pearl's trust boundary is two small JSON files:

- [`pearl/feature_dictionary.json`](pearl/feature_dictionary.json) —
  20 features, each with a statute cite and (optional) keyword list.
- [`pearl/statute_structure.json`](pearl/statute_structure.json) —
  element groups per exemption, each carrying a **verbatim quote from
  § 552(b)**. A test asserts every quote is a substring of the fetched
  statute; drift fails fast.

The traces that train the pearl are then generated from those files by
[`pearl/generate_traces.py`](pearl/generate_traces.py) — no row is
hand-typed. The audit artifact
[`pearl/traces_review.md`](pearl/traces_review.md) renders every
exemplar next to the quoted statute paragraph it was derived from.

## Quick start

```bash
uv sync --extra dev
cp .env.example .env            # OPENAI_API_KEY
make fetch                      # pull the corpus (11 docs, sha256-verified)
make index                      # chunk + embed for the RAG baseline
make build                      # build the LogicPearl artifact
make demo                       # full 15 × 5 × both sides comparison
```

Captured sample runs live in [`transcripts/`](transcripts/). The
keyword-mode pearl runs offline after build — no API key needed.

## Pluggable LLM

```bash
LP_LLM_PROVIDER=openai          # or anthropic | ollama
LP_LLM_MODEL=gpt-4o
LP_EMBEDDING_PROVIDER=openai    # or sentence_transformers (fully offline)
LP_PEARL_EXTRACTOR=llm          # or keyword (fully LLM-free PAG)
```

## Documentation

- [`docs/findings.md`](docs/findings.md) — results, prompts, failure
  modes with captured output, fairness notes, when-to-use-which.
- [`docs/plans/2026-04-14-rag-demo-design.md`](docs/plans/2026-04-14-rag-demo-design.md)
  — approved design brief.
- [`docs/plans/2026-04-14-rag-demo-implementation.md`](docs/plans/2026-04-14-rag-demo-implementation.md)
  — 23-task implementation plan used during the build.

## Layout

```text
corpus/              # fetched federal docs; sha256-verified
ragdemo/             # shared libs: llm, corpus, scenarios
rag/                 # RAG indexer + runner
pearl/               # LogicPearl traces, generator, build.sh, runner,
                     # keyword extractor, feature dictionary, structure
scenarios/           # 15 FOIA record descriptions
transcripts/         # captured demo runs
compare.py           # side-by-side driver
docs/                # design, implementation plan, findings
```

## Limitations

Pedagogical corpus (no case law), statute-derived trace set (no case-law
nuance), 15 scenarios, not legal advice. See the *Limitations* section
of [`docs/findings.md`](docs/findings.md) for details.
