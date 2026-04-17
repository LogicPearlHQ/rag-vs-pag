# Scenarios

The files in this directory are the active benchmark inputs and review
sidecars. Historical scrape and corpus-construction artifacts live in
`scenarios/archive/`.

## Active Inputs

- `muckrock_snapshot.100.live.json`: deterministic 100-record live benchmark.
- `split.100.live.json`: deterministic dev/test split for the 100-record benchmark.
- `adjudication.100.live.json`: clean/ambiguous/invalid labels and acceptable-label sets.
- `muckrock_snapshot.100.live.clean.json`: mechanically clean subset from adjudication.
- `split.100.live.clean.json`: split for the mechanically clean subset.
- `manual_review.100.live.clean.json`: human review decisions for mechanically clean cases.
- `muckrock_snapshot.100.live.clean.approved.json`: manually approved clean benchmark.
- `split.100.live.clean.approved.json`: split for the manually approved clean benchmark.

The current `make final-report` path reads only these files from
`scenarios/`. It regenerates the adjudication and clean subset files before
running the benchmark.

## Archive

`scenarios/archive/` keeps the intermediate scrape snapshots, relabeling
reports, selection reports, old fixture files, and the raw MuckRock file
cache. Those files document how the current benchmark corpus was assembled,
but they are not read by the benchmark runner.

Pipelines may read only:

- `request_text`
- `agency_name`

They must not read `status`, `response_text`, `primary_exemption`,
`all_cited_exemptions`, or `muckrock_url`.
