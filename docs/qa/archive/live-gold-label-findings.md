# Live Gold Label QA Findings

Date: 2026-04-17

Source sample: `docs/qa/archive/live-gold-label-review.md`

## Summary

The QA pass found one mechanical gold-label bug and several expected
ambiguities in the live MuckRock corpus.

The mechanical bug was broad matching of bare `(b)(N)` citations. This
incorrectly treated non-exemption citations such as `28 C.F.R. 16.10(b)(1)`
fee-category references as FOIA Exemption 1.

Fix applied:

- `scripts/corpus_build/extract_gold_labels.py` now treats bare `(b)(N)` as an exemption
  only when nearby context references FOIA, exemption, withholding,
  redaction, `552`, or `U.S.C.`.
- It rejects nearby non-exemption contexts such as `C.F.R.`, `16.10`, fee
  discussions, and commercial-use request categories.

## Relabel Result

Relabel source:

`scenarios/archive/muckrock_snapshot.combined.live.json`

Relabel output:

- `scenarios/archive/muckrock_snapshot.relabelled.live.json`
- `scenarios/muckrock_snapshot.100.live.json`
- `scenarios/archive/muckrock_relabel_report.live.json`

Result:

```text
Original merged records: 116
Kept after relabel: 111
Dropped after relabel: 5
Changed exemption lists: 6
Final 100-record benchmark snapshot: 100
```

Final 100-record distribution:

```text
b1: 2
b2: 1
b3: 11
b4: 3
b5: 18
b6: 37
b7: 25
b8: 3
```

## Dropped Records

The relabel pass dropped records where the stricter extractor found no
reliable FOIA exemption citation in the saved response text. The most
important dropped pattern was EOIR fee-category language that looked like
`16.10(b)(1)` but was not Exemption 1.

Dropped request IDs:

```text
68546
72945
87595
87596
98149
```

## Remaining Ambiguities

Some records remain valid but hard:

- Multi-exemption letters often cite `b6` and `b7` together. A request for
  FBI files about a person can plausibly trigger both; predicting the
  agency's first-cited exemption is not always possible from request text.
- Partial-production letters often cite privacy exemptions for redacted
  names even when the request topic is not privacy-shaped.
- Some agency response text comes from long email chains. The scraper
  truncates standard exemption appendices, but email-chain context can still
  include more than one agency communication.
- The benchmark gold label remains "agency-cited primary exemption," not
  legally correct exemption.

## Policy Changes After QA

Policy tuning was limited to the dev split and general FOIA patterns:

- Generic personnel/named-person privacy now resolves to `b6` before
  generic `b7`.
- Stronger `b7` subfeatures, such as confidential source or investigative
  techniques, still resolve to `b7`.
- Correspondence about named people can resolve to `b6` only when no
  stronger record category is present.
- FinCEN/SAR, IRS return-information, financial-supervision, procurement,
  and grant/proposal request shapes were added to the feature dictionary.

## Current Held-Out Result

Current held-out test split: 61 records.

```text
Track A, end-to-end:
PAG:             26/61 strict, 35/61 lenient, 42/61 acceptable
RAG:             4/61 strict, 6/61 lenient, 7/61 acceptable
RAG-ChunkLookup: 4/61 strict, 6/61 lenient, 7/61 acceptable

Track B, shared OpenAI facts:
PAG:             26/61 strict, 35/61 lenient, 42/61 acceptable
RAG:             7/61 strict, 13/61 lenient, 14/61 acceptable
RAG-ChunkLookup: 7/61 strict, 11/61 lenient, 12/61 acceptable
```

The important LogicPearl result remains governance: fixed facts produce a
stable, inspectable rule decision. Accuracy is now good enough to show the
workflow, but not yet strong enough for a headline claim of legal
classification quality.

## Follow-On Benchmark Adjudication

A separate adjudication layer now records benchmark quality without using
system predictions:

- `scenarios/adjudication.100.live.json`
- `scenarios/muckrock_snapshot.100.live.clean.json`
- `scenarios/split.100.live.clean.json`
- `scenarios/manual_review.100.live.clean.json`
- `scenarios/muckrock_snapshot.100.live.clean.approved.json`
- `scenarios/split.100.live.clean.approved.json`
- `docs/qa/live-benchmark-adjudication.md`
- `docs/qa/manual-clean-review.md`
- `docs/qa/benchmark-methodology-log.md`

Current full 100-record adjudication:

```text
clean: 25
ambiguous: 75
invalid: 0
```

Current held-out approved-clean test split:

```text
approved clean test records: 13
```

Current approved-clean held-out result:

```text
Track A:
PAG:             6/13 strict, 6/13 acceptable
RAG:             3/13 strict, 3/13 acceptable
RAG-ChunkLookup: 3/13 strict, 3/13 acceptable

Track B:
PAG:             6/13 strict, 6/13 acceptable
RAG:             4/13 strict, 4/13 acceptable
RAG-ChunkLookup: 5/13 strict, 5/13 acceptable
```

These are the single-path OpenAI results. The old controlled heuristic
benchmark path has been removed; tests now mock the OpenAI call boundary
instead of running an alternate evaluator.

LogicPearl now uses `insufficient_facts` rather than `releasable` when the
request text does not support an exemption-shaped classification. This is
an abstention, not a correctness claim.
