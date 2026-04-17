# Benchmark Methodology Log

This log tracks benchmark-quality changes so the public write-up can distinguish corpus cleaning, adjudication, ruleset changes, and model evaluation.

## 2026-04-17: Live Gold Relabel Pass

Input:

- `scenarios/archive/muckrock_snapshot.combined.live.json`

Outputs:

- `scenarios/archive/muckrock_snapshot.relabelled.live.json`
- `scenarios/muckrock_snapshot.100.live.json`
- `scenarios/split.100.live.json`
- `scenarios/archive/muckrock_relabel_report.live.json`

Change:

- Fixed broad gold-label matching of bare `(b)(N)` citations.
- Bare `(b)(N)` is now counted only when nearby context references FOIA, exemption, withholding, redaction, `552`, or `U.S.C.`
- Nearby `C.F.R.`, `16.10`, fee, and commercial-use request contexts are rejected.

Fairness note:

- This pass changed labels only from agency response text.
- It did not inspect RAG, RAG-ChunkLookup, LogicPearl, or OpenAI extractor predictions.

## 2026-04-17: Shared Extractor Fairness Pass

Input:

- `scenarios/muckrock_snapshot.100.live.json`

Output:

- `extraction/outputs/shared_features.100.live.openai.json`

Change:

- Added OpenAI structured extraction as a shared Track B feature source.
- RAG, RAG-ChunkLookup, and LogicPearl consume the same extracted feature vector in Track B.
- The extractor returns features and evidence only; it does not choose a FOIA exemption.

Fairness note:

- Track B isolates the decision layer.
- Track B should not be described as end-to-end model accuracy.

## 2026-04-17: Benchmark Adjudication Layer

Inputs:

- `scenarios/muckrock_snapshot.100.live.json`
- `scenarios/split.100.live.json`

Outputs:

- `scenarios/adjudication.100.live.json`
- `scenarios/muckrock_snapshot.100.live.clean.json`
- `scenarios/split.100.live.clean.json`
- `docs/qa/live-benchmark-adjudication.md`

Change:

- Added deterministic sidecar adjudication with three buckets:
  - `clean`: single cited exemption with applied withholding/redaction context.
  - `ambiguous`: valid citation with overlap, multi-exemption, generic request, weak context, or procedural/nonfinal flags.
  - `invalid`: no reliable applied FOIA exemption label in saved response text.
- Added acceptable-label scoring for overlap cases.
- Added LogicPearl trace-valid scoring: an acceptable verdict must come from a non-default rule with authority IDs.
- Added LogicPearl abstention/default reporting by adjudication bucket.

Fairness note:

- Adjudication does not use system predictions.
- The clean benchmark is a filtered subset, not a retuned replacement for the live benchmark.
- Messy live and clean adjudicated results should be reported separately.

## Write-Up Rules

- Report the data source, sample size, split, and adjudication bucket counts before reporting accuracy.
- Keep Track A and Track B separate.
- Do not compare clean-benchmark numbers against messy-live numbers as if they were the same task.
- Describe acceptable-label accuracy as an ambiguity-aware score, not as strict accuracy.
- Describe `insufficient_facts`/default LogicPearl decisions on ambiguous cases as abstentions only when the ruleset trace shows the default rule.

## 2026-04-17: Manual Clean Review

Inputs:

- `scenarios/muckrock_snapshot.100.live.clean.json`
- `scenarios/adjudication.100.live.json`

Outputs:

- `scenarios/manual_review.100.live.clean.json`
- `scenarios/muckrock_snapshot.100.live.clean.approved.json`
- `scenarios/split.100.live.clean.approved.json`
- `docs/qa/manual-clean-review.md`

Change:

- Manually reviewed every mechanically clean record.
- Approved records only when the evidence span supported a single-label clean gold answer.
- Excluded three mechanically clean records from the approved-clean benchmark:
  - `14161`: nonfinal Exemption 4 recommendation pending Initial Denial Authority decision.
  - `33143`: response cites both Exemption 5 and Exemption 6; mechanical primary was not defensible as a clean single-label gold.
  - `118656`: status-style notice says the agency routinely applies Exemption 6 but does not cleanly apply it to located responsive records.

Fairness note:

- Manual review did not inspect system predictions.
- Mechanical clean and approved-clean subsets are both preserved.

## 2026-04-17: Explicit Insufficient-Facts Mode

Change:

- Ruleset defaults now return `insufficient_facts` instead of `releasable`.
- OpenAI RAG baseline prompts require `insufficient_facts` when request text and facts do not support an exemption-shaped classification.
- Abstention/default reporting counts `insufficient_facts` decisions.

Fairness note:

- This does not create correct labels for existing exemption-only gold cases.
- It separates “under-determined from request text” from “legally releasable.”

## 2026-04-17: Single OpenAI Runtime Path

Change:

- Removed the old heuristic RAG/RAG-ChunkLookup runtime path.
- Removed the heuristic shared extractor runtime path.
- Plain RAG now asks the model for verdict, rationale, and cited excerpts.
- RAG-ChunkLookup now asks the model for verdict, rationale, and retrieved chunk IDs only; server code resolves citation text from stored chunks.
- Added citation-support accounting in addition to fabricated-excerpt accounting.
- Tests mock the OpenAI call boundary instead of running a second benchmark path.

Fairness note:

- There is now one benchmark/report path: OpenAI extraction, OpenAI RAG, OpenAI ChunkLookup, and the LogicPearl decision artifact.
- Unit tests are not an alternate evaluation mode; they are mocks around the single OpenAI runtime boundary.
