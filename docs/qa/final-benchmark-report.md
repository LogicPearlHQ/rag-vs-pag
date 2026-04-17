# Final Benchmark Report

Date: 2026-04-17

## Claim Boundary

This benchmark evaluates a governance-oriented claim, not a broad legal-classification claim. The strongest defensible result is that a versioned decision artifact can turn shared extracted facts into stable, inspectable, trace-valid decisions, and explicitly abstain when request text lacks exemption-shaped facts.

Track A is end-to-end. Track B uses one shared OpenAI structured extractor for every pipeline and isolates the decision layer. The reported RAG and RAG-ChunkLookup baselines are real OpenAI calls. There is no heuristic benchmark path.

## Corpus Construction

- Source: public MuckRock FOIA requests and response text/PDF text already downloaded into the repo workspace.
- Live benchmark source: `scenarios/muckrock_snapshot.100.live.json`.
- Raw response-derived labels are agency-cited exemptions, not judicial determinations of legal correctness.
- The OpenAI extractor produces feature vectors only; it does not choose exemption labels.
- The RAG baseline asks OpenAI for verdict, rationale, and quoted excerpts.
- The RAG-ChunkLookup baseline asks OpenAI for verdict, rationale, and retrieved chunk IDs; server code resolves citation text.

## Gold-Label Cleanup

The gold-label extractor was tightened before this report. Bare `(b)(N)` citations are counted only near FOIA/exemption/withholding context, and fee-regulation contexts such as `28 C.F.R. 16.10(b)(1)` are rejected.

## Deterministic Adjudication

| Bucket | Count |
|---|---:|
| clean | 25 |
| ambiguous | 75 |
| invalid | 0 |

Adjudication is deterministic and prediction-independent. It inspects request/response text and records flags such as `multi_exemption_letter`, `privacy_law_enforcement_overlap`, `procedural_or_nonfinal_response`, and `boilerplate_only_or_appendix`.

## Manual Clean Review

| Manual status | Count |
|---|---:|
| approved_clean | 22 |
| needs_rebucket | 2 |
| wrong_primary | 1 |

Approved clean records: 22
Approved clean dev records: 9
Approved clean test records: 13

| Approved primary exemption | Count |
|---|---:|
| b3 | 6 |
| b5 | 4 |
| b6 | 7 |
| b7 | 2 |
| b8 | 3 |

Manual review excluded three mechanically clean records from the approved-clean benchmark: `14161`, `33143`, and `118656`. The reasons are recorded in `docs/qa/manual-clean-review.md`.

## Full Live, Ambiguity-Aware Results

| Track | Pipeline | Strict | Lenient | Acceptable | Trace-valid | Excerpt Fabricated | Citation Supports | Verdict Stable | Byte Identical |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| A | logicpearl | 26/61 | 35/61 | 42/61 | 42/61 | 0 | 55/55 | 61/61 | 61/61 |
| A | rag | 4/61 | 6/61 | 7/61 | - | 0 | 16/16 | 61/61 | 61/61 |
| A | rag_chunklookup | 4/61 | 6/61 | 7/61 | - | 0 | 14/62 | 61/61 | 61/61 |
| B | logicpearl | 26/61 | 35/61 | 42/61 | 42/61 | 0 | 55/55 | 61/61 | 61/61 |
| B | rag | 7/61 | 13/61 | 14/61 | - | 0 | 28/36 | 61/61 | 61/61 |
| B | rag_chunklookup | 7/61 | 11/61 | 12/61 | - | 0 | 21/48 | 61/61 | 61/61 |

Note: real LLM baseline rows are cached. Stability columns measure replay stability for this artifact, not uncached sampling variance.

## Approved-Clean Results

| Track | Pipeline | Strict | Lenient | Acceptable | Trace-valid | Excerpt Fabricated | Citation Supports | Verdict Stable | Byte Identical |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| A | logicpearl | 6/13 | 6/13 | 6/13 | 6/13 | 0 | 11/11 | 13/13 | 13/13 |
| A | rag | 3/13 | 3/13 | 3/13 | - | 0 | 5/5 | 13/13 | 13/13 |
| A | rag_chunklookup | 3/13 | 3/13 | 3/13 | - | 0 | 4/20 | 13/13 | 13/13 |
| B | logicpearl | 6/13 | 6/13 | 6/13 | 6/13 | 0 | 11/11 | 13/13 | 13/13 |
| B | rag | 4/13 | 4/13 | 4/13 | - | 0 | 7/7 | 13/13 | 13/13 |
| B | rag_chunklookup | 5/13 | 5/13 | 5/13 | - | 0 | 6/16 | 13/13 | 13/13 |

Note: real LLM baseline rows are cached. Stability columns measure replay stability for this artifact, not uncached sampling variance.

## Interpretation

- Full live acceptable-label scoring is the right view for noisy real-world FOIA responses with overlapping exemptions.
- Approved-clean scoring is the conservative view; the approved clean held-out test set is small, so it should not be overclaimed.
- `insufficient_facts` is an abstention, not a correct exemption label. It separates underdetermined request text from truly releasable records.
- The LogicPearl row's trace-valid column requires an acceptable verdict from a non-default rule with cited authority IDs.
- RAG-ChunkLookup prevents freeform quote fabrication by resolving chunk IDs server-side, but real model-selected chunk IDs are not always support-valid.
- Plain RAG did not fabricate excerpt bytes in this run, but its quote text is still model-authored rather than server-resolved.

## Trace Viewer

A write-up-friendly trace view is generated at `docs/demo/trace-viewer.md`. It includes one clean rule-match case and one clean agency-withholding case where request text alone produces `insufficient_facts`.

## Write-Up Language

Use: This benchmark tests whether a versioned decision artifact makes FOIA-style classifications easier to audit under shared extracted facts.

Avoid: LogicPearl broadly outperforms RAG on legal exemption classification.
