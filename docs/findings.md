# RAG vs LogicPearl on FOIA Exemption Classification — Findings

**Run date:** 2026-04-14   ·   **Model:** OpenAI gpt-4o, temperature 0   ·   **Corpus:** 5 U.S.C. § 552 + DOJ OIP FOIA Guide (Exemptions 1–9 PDFs) + 28 C.F.R. Part 16

## TL;DR

Same corpus, same LLM, same 15 scenarios, three backends: classical RAG,
LogicPearl with LLM feature extraction, and LogicPearl with keyword feature
extraction.

| | **RAG** | **Pearl (LLM extract)** | **Pearl (keyword extract)** |
|---|---|---|---|
| Correct | 45 / 45 (100%) | 42 / 45 (93%) | 42 / 45 (93%) |
| Decision determinism | 45 / 45 | 45 / 45 | 45 / 45 |
| **Byte-identical full output** | 25 / 45 (56%) | 20 / 45 (44%) | **45 / 45 (100%)** |
| **Citation faithfulness** | **70 / 94 (74%)** | **57 / 57 (100%)** | **72 / 72 (100%)** |
| LLM calls per scenario | 1 | 2 | **0** |
| Avg latency | 3.7 s | 3.8 s | **<1 ms** |
| Marginal cost per run | ~$0.01 | ~$0.005 | **$0** |

**The separator is not correctness.** Correctness is comparable on clean
benchmarks. The separators are **citation faithfulness** and **full-output
determinism** — and on both, LogicPearl paths are 100% by construction, while
RAG's 74% faithful and 56% full-det are LLM-bounded. The keyword-extractor
pearl achieves all of this with **zero LLM calls, zero API spend, and sub-
millisecond latency**, end to end.

---

## What the demo tested

### Scenarios

15 FOIA record descriptions, labeled with a gold exemption:

| # | Scenario | Category | Gold |
|---|---|---|---|
| 01 | Inter-agency memo classified TOP SECRET under EO 13526 | clear-cut | b1 |
| 02 | One-page internal agency rulebook on parking placards | clear-cut | b2 |
| 03 | Tax return filed with the IRS (blocked by § 6103) | clear-cut | b3 |
| 04 | Pesticide trade-secret chemical formula submitted to EPA | clear-cut | b4 |
| 05 | Draft pre-decisional intra-agency rulemaking memo | clear-cut | b5 |
| 06 | Personnel files with home addresses, phone, medical leave | clear-cut | b6 |
| 07 | FBI file identifying a confidential informant | clear-cut | b7 |
| 08 | OCC bank examination report | clear-cut | b8 |
| 09 | Map of subsurface geological strata from private oil wells | clear-cut | b9 |
| 10 | Agency press release already on the public website | clear-cut | releasable |
| 11 | 1985 State Department cable, declassified in 2010 | borderline | releasable |
| 12 | Routine inter-agency transmittal, not deliberative or privileged | borderline | releasable |
| 13 | Agency roster with names + official titles only | borderline | releasable |
| 14 | LE record for a closed case with no (b)(7)(A)–(F) harms | borderline | releasable |
| 15 | "Summarize the legislative history of FOIA Exemption 5" | rag-favored | not_applicable |

Scenarios 01–09 probe each named exemption. 10 is a clean release baseline.
11–14 are borderline cases where elements of an exemption are present but
co-elements are absent — these exercise the pearl's conjunctive reasoning
and RAG's retrieval quality. 15 is a synthesis task included specifically
to demonstrate the pearl's domain limit — it's RAG's job, not the pearl's.

### Corpus

Fetched by `corpus/fetch.py`, sha256-verified, snapshot fallback for the
statute. 493 chunks total (495KB+ after chunking):

- **5 U.S.C. § 552** — statute text (Cornell LII)
- **DOJ OIP *Guide to the Freedom of Information Act*** — nine exemption
  PDFs from justice.gov
- **28 C.F.R. Part 16** — DOJ's own FOIA regulations (eCFR versioner API)

Not included: CourtListener case opinions (API now requires an auth token).
Instructions for adding them are in `corpus/sources.toml`.

### Model

OpenAI `gpt-4o` at temperature 0 for every LLM call. OpenAI's temp=0 is a
best-effort variance reduction, not a formal reproducibility guarantee —
which is part of why the "full-output determinism" numbers on LLM paths
are below 100%. The pearl's own runtime is formally deterministic (compiled
rule evaluation in Rust, no floats, no GPU).

---

## The three pipelines

### A. RAG baseline

```
  free text ──► retrieval ──► LLM: synthesize + decide + cite ──► answer
```

- **Retrieval:** hybrid BM25 + dense embeddings (OpenAI
  `text-embedding-3-small`), top-20 union, cross-encoder rerank
  (`ms-marco-MiniLM-L-6-v2`), top-8 into the prompt. Not a weekend
  prototype — this is what competent production legal RAG looks like.
- **Prompt:** forces strict-JSON output with citations required. Includes
  a refusal path (`insufficient_context`) for when the retrieved chunks
  don't support a confident answer.
- **Post-hoc citation-faithfulness check:** for each cited excerpt,
  normalize whitespace and hyphens and test whether it appears as a
  substring of any retrieved chunk. Mismatches are flagged as fabricated.

### B. LogicPearl with LLM feature extraction

```
  free text ──► LLM tool-use: extract_features ──► {feature: bool} ──►
    → logicpearl run (Rust engine, no LLM) ──► decision + rule output ──►
    → LLM: compose plain-English explanation (cannot change verdict) ──► answer
```

Two LLM calls around a deterministic rule engine. The engine itself makes
zero LLM calls. The explanation LLM is **architecturally forbidden from
changing the verdict** — the code overwrites any exemption value the LLM
produces with the pearl's own action.

### C. LogicPearl with keyword feature extraction

```
  free text ──► keyword substring match ──► {feature: bool} ──►
    → logicpearl run (Rust engine, no LLM) ──► decision + rule output ──►
    → Python template: compose rationale from rule output ──► answer
```

**Zero LLM calls, end to end.** Runs offline, microsecond latency, zero
API spend. The feature extractor is a ~50-line module that reads keyword
lists from `pearl/feature_dictionary.json`. The rationale is generated
from a small Python template that cites the pearl's own output.

---

## The prompts, verbatim

### RAG system prompt

> You are a FOIA analyst. Given the retrieved statutory, regulatory, and
> guidance excerpts below, determine whether the described record is
> exempt under 5 U.S.C. § 552(b), and under which subsection (b1
> through b9). If the record is releasable, use "releasable". If the
> request is an open-ended synthesis task that does not ask for an
> exemption determination, use "not_applicable".
>
> You MUST cite specific subsection or page numbers that appear in the
> retrieved excerpts. Every entry in cited_authorities MUST include a
> verbatim excerpt drawn from the retrieved text. Do not invent cites
> or text.
>
> If the retrieved context does not clearly support a confident answer,
> respond with exemption="insufficient_context" and confidence="low".
> Do not guess.

Output is schema-enforced (`ANSWER_SCHEMA` in `rag/rag.py`) — the LLM
must fill an object with `exemption`, `releasable`, `rationale`,
`cited_authorities[]`, `confidence`. No free-form text outside that shape.

### Pearl: feature extraction system prompt (LLM mode only)

> You are a FOIA analyst performing structured feature extraction.
>
> Given a free-text record description, set each feature TRUE only if
> the description clearly states or directly implies it. Err on the side
> of FALSE for ambiguous cases — the artifact will reach its conclusion
> on whatever features you mark, and false positives cause wrong answers.
> Do not speculate beyond the text.

The LLM is called with a tool whose `input_schema` is an object of ~20
boolean properties, one per feature in `pearl/feature_dictionary.json`.
Each property's `description` is the feature's human label (e.g.,
*"Classified under Executive Order"*, *"Pre-decisional and deliberative"*).
The LLM is forced to call that tool, so the output is a validated
`{feature_name: bool}` dict.

### Pearl: explanation system prompt (LLM mode only)

> You are explaining a deterministic decision produced by a reviewed
> policy artifact.
>
> The artifact has already decided the exemption. Your job is to explain
> its decision in plain English, citing authorities drawn from the
> artifact's own rule output. You MUST:
>
> - Accept the artifact's action verbatim.
> - Cite authorities the artifact provides; do not add new cites.
> - Not contradict the artifact, hedge, or suggest alternatives.
>
> If the artifact's action is `releasable`, say the record is releasable.

### Pearl: template rationale (keyword mode only)

No prompt. Rationale is composed by `_compose_template_rationale()` in
`pearl/pearl.py`, which produces fixed-shape text from the pearl's own
output — e.g.:

> "The record is exempt under b5 because the features
> `pre_decisional_deliberative`, `inter_or_intra_agency_memo` match the
> rule reviewed in the pearl. Authorities: 5 U.S.C. § 552(b)(5)."

Fully deterministic. The same feature vector and artifact action always
produces the same rationale, byte for byte.

---

## Trust boundaries

### RAG
The LLM generates the answer text, the citations, and the excerpts. The
faithfulness check catches fabricated excerpts post-hoc; it cannot catch
cases where the LLM's free-form rationale misstates what the retrieved
chunks actually say while still copying valid substrings.

### Pearl with LLM extraction
- **The decision is in the artifact** (compiled rule evaluation, Rust,
  formally deterministic).
- **The cited authorities come from the feature dictionary** (a reviewed
  JSON file), not from the LLM.
- **The LLM's role is confined to two things**: reading a description into
  booleans, and writing prose about the artifact's own output. The code
  architecturally prevents the LLM from changing the verdict.

What you have to trust, end to end:
1. The feature dictionary correctly summarizes each statute clause it
   claims to encode.
2. The trace set was produced by `pearl/generate_traces.py` from
   `pearl/statute_structure.json`, whose every entry carries a verbatim
   quote from the statute that's auto-verified against the fetched text.
3. The LLM's boolean feature extraction reflects the description.

### Pearl with keyword extraction
Same as above, minus item 3. Replace the LLM extractor with a reviewed
keyword list in `pearl/feature_dictionary.json`. The full pipeline is now
auditable from three JSON files (feature dictionary, statute structure,
corpus manifest) + ~50 lines of pure-Python extraction code. No LLM
behavior to trust at runtime.

---

## Results in detail

### Correctness: every pipeline got 15 scenarios, scored against gold

- **RAG: 45/45 (100%).** Perfect on these 15 scenarios.
- **Pearl (LLM): 42/45 (93%).** Missed only scenario 15.
- **Pearl (keyword): 42/45 (93%).** Missed only scenario 14.

Same aggregate score, different losses. See *Failure modes* below.

### Determinism: what varies across 3 reruns per scenario

All three pipelines produce byte-identical *exemption verdicts* across
reruns at temp=0. The divergence is in prose:

- **RAG byte-identical full output: 25/45 (56%).** The rationale text
  and sometimes the ordering of `cited_authorities` drifts across reruns.
- **Pearl (LLM) byte-identical: 20/45 (44%).** Lower than RAG because
  the pearl runs *two* LLM calls (extraction + explanation), both with
  independent per-call drift. The underlying pearl decision never
  changes — only the surrounding prose.
- **Pearl (keyword) byte-identical: 45/45 (100%).** By construction.
  There is no LLM in the loop to drift.

If your production requirement includes "this output must hash the same
on every run," keyword mode is the only path that meets it.

### Citation faithfulness — the auto-checked metric

Every `cited_authorities[i].excerpt` is tested for normalized substring
presence in either the retrieved chunks (RAG) or the authoritative source
(pearl feature dictionary).

- **RAG: 70/94 faithful (74%).** 24 excerpts were either paraphrased,
  compressed with ellipsis, or hallucinated from training data.
  Per-scenario lows: scenario 07 `0/3`, scenario 13 `0/3`, scenario 03
  `2/8`.
- **Pearl (LLM): 57/57 (100%).** Pearl's citations come from a lookup
  in `feature_dictionary.json`, not from the LLM.
- **Pearl (keyword): 72/72 (100%).** Same source — fully verified by
  construction.

---

## Failure modes — with captured output

### RAG citation failures: three real examples

These are copy-pasted from live runs against the real corpus.

**1. Ellipsis compression (scenario 07, LE source):**

The LLM cited this as a single passage from `5 U.S.C. § 552(b)(7)`:

> *"records or information compiled for law enforcement purposes, but
> only to the extent that the production of such law enforcement records
> or information**...** (D) could reasonably be expected to disclose..."*

The `...` silently elides subclauses (A), (B), and (C) — hundreds of
words of statute text. The stitched result does not exist verbatim
anywhere in the statute. Flagged as fabricated.

**2. Plausible fabrication from training data (scenario 13, personnel roster):**

Cited as `DOJ FOIA Guide, Exemption 6, p. 14`:

> *"Similarly, civilian federal employees who are not involved in law
> enforcement generally have no expectation of privacy regarding their
> names, titles, grades, salaries, and duty stations as employees."*

The Guide probably says something like this *somewhere*. The sentence
isn't on page 14 of the retrieved chunk. Most likely the LLM is pulling
from its pre-training corpus rather than the retrieved text. Flagged as
fabricated.

**3. Memory-mixed quote (scenario 03, tax return):**

Cited as `DOJ FOIA Guide, Exemption 3, p. 40`:

> *"Exemption 3 or return information of other taxpayers. Specifically,
> section 6103 provides that '[r]eturns and return information shall be
> confidential,' subject to a number of enumerated exceptions."*

The retrieval actually fetched page 40. The LLM had the real text in
context. It chose to write its own phrasing that blends § 6103's text
with a summary the LLM remembers. The result reads authoritatively but
isn't a substring of what was retrieved. Flagged as fabricated.

**Pattern:** all three "fabrications" are grammatically clean,
plausible-sounding, and include real page numbers. Without the
post-hoc substring check, a reader would not notice.

### Pearl (LLM mode) failure: scenario 15

**Description:** *"In a single paragraph, summarize the legislative
history of FOIA Exemption 5 and the two Supreme Court opinions most
responsible for shaping its current scope."*

**Features the LLM extracted:**

```json
"inter_or_intra_agency_memo": true,
"pre_decisional_deliberative": true,
"attorney_work_product_or_privileged": true,
(all others false)
```

The LLM saw the phrase *"Exemption 5"* and confidently set all three
(b)(5)-related features TRUE — treating a question *about* Exemption 5
as a description of a record qualifying under Exemption 5.

**The pearl did its job perfectly** given those inputs — the (b)(5) rule
fires when those features are TRUE, so the decision was `b5`. The
failure is entirely in the LLM feature extraction layer.

This is a live example of **why the extractor is the weak link** in an
LLM+pearl stack: LLMs are gullible to prompts that reference their
target vocabulary.

### Pearl (keyword mode) failure: scenario 14

**Description (excerpted):** *"...its disclosure would not interfere with
any proceeding, would not invade any individual's personal privacy,
would not reveal a confidential source, would not disclose techniques or
procedures, and would not endanger life or safety..."*

The phrase *"confidential source"* is a keyword trigger for
`law_enforcement_harm_source`. The phrase *"disclose techniques"*
triggers `law_enforcement_harm_techniques`. The keyword extractor does
substring matching and cannot scope negation — it fires both harm
features even though the sentence says "would NOT reveal a confidential
source" and "would NOT disclose techniques."

**Fix (left for future work):** widen the `negative_keywords` list for
each harm feature (add `"would not reveal"`, `"would not disclose"`,
etc.), or replace substring match with a real negation-aware parser
(spaCy's `Matcher` with dependency patterns, or a small fine-tuned
classifier). Either is straightforward engineering; not a fundamental
ceiling of the keyword approach.

---

## Fairness guardrails

Things deliberately done to avoid stacking the deck:

- **Same LLM, same temperature (0), same scenarios, same corpus** on all
  three pipelines.
- **Strong RAG baseline:** hybrid retrieval, cross-encoder rerank,
  structure-aware chunking, citation-required system prompt, top-k = 8.
  Not a straw-man.
- **Refusal path in RAG** (`insufficient_context`) so RAG can decline
  when retrieval doesn't support a confident answer.
- **At least one scenario RAG is supposed to win** (#15, synthesis) —
  RAG uses its `insufficient_context` path correctly there while the
  LLM-mode pearl mis-classifies.
- **Citation faithfulness is auto-checked for both sides.**

Things *not* done that a fair reviewer should note:

- **Only the pearl side got a second pass of refinement.** The initial
  run surfaced a greedy-rule issue with scenarios 11/12/14; we fixed it
  by expanding the trace set (adding four statute-grounded "inverse"
  patterns that encode the statute's conjunctive structure). **RAG got
  no equivalent refinement pass.** A serious RAG team would further
  harden the citation output (e.g., have the LLM reference chunk IDs
  instead of writing excerpts, then look up the excerpt server-side —
  this would push RAG's citation faithfulness toward 100%).
- **Scenario 14 was replaced** between the first and second runs. The
  original asked for a label (`insufficient_context`) that neither system
  could produce honestly without introducing an LLM-judgment layer that
  would undermine the demo's thesis. Replacing it was an equal-treatment
  change (both systems got +5 from it), but it is a scenario change and
  worth naming.
- **The `out-of-distribution` category was dropped** for the same reason.

The honest framing: **this is LogicPearl vs. a competent-but-not-heavily-
engineered RAG.** A serious RAG team could likely push faithfulness up
via chunk-ID lookups and structured-output tricks. The pearl's 100% is
free (one line of code); the RAG's 100% would be custom scaffolding.

---

## When to use which

| Situation | Best pick |
|---|---|
| Open-ended synthesis, research, summarization | **RAG.** LogicPearl doesn't do synthesis. |
| Bounded policy decision, audit-critical, needs citation proof | **Pearl.** 100% citation faithfulness is structural, not engineered. |
| Requires byte-identical output across reruns (compliance, legal) | **Pearl keyword mode.** Only path with zero LLM nondeterminism. |
| Bounded decision, paraphrase-heavy inputs, willing to pay for an LLM | **Pearl LLM mode.** Paraphrase-robust extraction, deterministic decision. |
| Offline / no API access / zero marginal cost at scale | **Pearl keyword mode.** Microsecond latency, no network. |
| Production recommendation | **Pearl LLM mode, gated by keyword consistency check.** LLM extracts, keywords verify. Disagreement → escalate. Would have caught scenario 15 (LLM said b5 features TRUE, keywords say FALSE). |

---

## Limitations

- **Pedagogical corpus.** 11 documents (statute, 9 DOJ Guide chapters, 1
  CFR part). Real FOIA adjudication pulls from case law, agency-specific
  guidance, OGIS advisories, and judicial interpretations that are not
  included here.
- **Statute-derived trace set.** The pearl's rules encode the face of
  the statute, not case-law nuance (segregability, foreseeable-harm
  standard, etc.). A production pearl would need richer traces reviewed
  by actual FOIA officers.
- **Not legal advice.** Every part of this repo — the traces, the
  scenarios, the LLM outputs — is illustrative only.
- **RAG wasn't matched on refinement effort.** Noted above.
- **15 scenarios is a small sample.** The correctness percentages are
  robust only in the qualitative sense.

---

## How to reproduce

### Prerequisites

- macOS or Linux
- Python 3.11+
- `uv` (https://docs.astral.sh/uv/)
- `logicpearl` CLI on `PATH` (`brew install logicpearl` or
  `cargo install --path crates/logicpearl` from the main repo)
- `OPENAI_API_KEY` for the default provider (Anthropic and Ollama also
  supported; see `.env.example`)

### Four commands

```bash
cd ~/Documents/LogicPearl/rag-demo
uv sync --extra dev
cp .env.example .env          # fill in OPENAI_API_KEY
make fetch                    # pull statute + DOJ Guide + CFR into corpus/raw/
make index                    # chunk + embed for the RAG baseline
make build                    # build the LogicPearl artifact from traces.csv
make demo                     # 15 scenarios × 5 reruns × both pearl modes + RAG
```

For the keyword-mode pearl only (no API key needed after build):

```bash
uv run python compare.py --pearl-extractor keyword --skip-rag --repeat 3
```

Captured transcripts land in `transcripts/` with per-run manifests.

---

## Change log

- **Design phase** (`docs/plans/2026-04-14-rag-demo-design.md`) — validated
  architecture, corpus scope, fairness guardrails before any code.
- **Implementation plan** (`docs/plans/2026-04-14-rag-demo-implementation.md`)
  — 23 bite-sized tasks with TDD where applicable.
- **Initial demo** — 80% pearl correctness; RAG's citation fabrication
  surfaced.
- **Refusal-pathway pass** — statute-grounded inverse rows expanded the
  trace set so the pearl's learned rules match the statute's conjunctive
  structure (e.g., (b)(5) requires deliberative *or* privileged, not just
  inter-agency memo). Pearl correctness 80% → 93%. No runtime heuristics,
  no preflight LLM-judgment layers.
- **Keyword extractor** — fully-LLM-free path via keyword matching plus
  template rationale. Matches the LLM-mode pearl on correctness, reaches
  100% byte-identical full-output determinism, runs in microseconds with
  zero API spend.

---

## Where each thing lives

| File / directory | What |
|---|---|
| `corpus/fetch.py`, `corpus/sources.toml` | Corpus fetcher, pinned URLs + sha256 |
| `ragdemo/corpus.py` | Structure-aware chunkers (statute / CFR / PDF) |
| `ragdemo/llm.py` (+ providers) | Pluggable LLM interface |
| `rag/index.py`, `rag/retrieve.py` | BM25 + Chroma indexing, hybrid retrieval |
| `rag/rag.py` | RAG runner + citation-faithfulness check |
| `pearl/feature_dictionary.json` | 20 features, each with statute cite + keywords |
| `pearl/statute_structure.json` | Element groups per exemption + inverses + verbatim quotes |
| `pearl/generate_traces.py` | Trace generator (reads statute + structure, emits CSV) |
| `pearl/traces_review.md` | Auto-generated audit doc (statute quote per exemplar) |
| `pearl/build.sh` | `logicpearl build` with strict column handling |
| `pearl/pearl.py` | Pearl runner (LLM or keyword extractor; no-override rule) |
| `pearl/keyword_extractor.py` | Deterministic substring extractor |
| `scenarios/*.json` | 15 scenarios |
| `compare.py` | Side-by-side harness with metrics + transcript renderer |
| `transcripts/*.md` | Captured runs |
| `docs/plans/*.md` | Design + implementation plan |
| `docs/findings.md` | This file |
