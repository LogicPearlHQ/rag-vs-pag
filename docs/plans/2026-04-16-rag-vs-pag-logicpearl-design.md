# rag-vs-pag: LogicPearl-Centered Design Plan

Date: 2026-04-16
Status: Implemented; retained as design history.
Supersedes: `rag-demo/docs/plans/2026-04-16-rag-vs-pag-design.md`

## 1. Goal

Build a clean, reproducible public demo that shows where LogicPearl is
powerful:

> LLMs are useful for turning messy text into facts. LogicPearl is for
> turning facts into governed decisions: deterministic, inspectable,
> diffable, version-pinnable, and regression-testable.

The demo compares plain RAG, RAG with chunk-ID citation indirection, and
LogicPearl on real FOIA classification requests scraped from
MuckRock.

The central claim is not that LogicPearl eliminates all LLM uncertainty.
The central claim is that once the relevant facts are extracted, the
decision itself should be governed by a rule artifact, not generated as a
token stream.

Target repo: `~/Documents/LogicPearl/rag-vs-pag`

Target audience: technical readers on HN, r/MachineLearning,
r/LocalLLaMA, and skeptical AI engineers who will inspect the scenarios,
prompts, rules, and transcripts before trusting the result.

## 2. Headline Framing

### 2.1 Pitch sentence

> RAG can retrieve evidence, but it cannot govern the decision.
> LogicPearl turns extracted facts into a versioned rule decision:
> deterministic, inspectable, diffable, regression-testable, and
> auditable line by line.

### 2.2 What we claim

- Plain RAG can fabricate citation excerpts.
- Chunk-ID indirection fixes excerpt fabrication by resolving citations
  server-side from retrieved chunks.
- Neither RAG nor ChunkLookup makes the verdict itself governed,
  inspectable, versioned, or regression-testable.
- LogicPearl separates extraction from decision:
  - an LLM extracts facts from messy intake text;
  - a compiled rule artifact produces the verdict;
  - the rule artifact can be diffed, pinned, tested, and audited.

### 2.3 What we do not claim

- We do not claim the LLM extractor is deterministic.
- We do not claim the end-to-end LogicPearl pipeline is fully deterministic
  unless the extracted feature vector is fixed.
- We do not claim the agency-cited exemption is the legally correct
  exemption.
- We do not claim the sample size is statistically definitive.
- We do not claim the DOJ Guide corpus is sufficient for real FOIA work.
- We do not claim LogicPearl is a replacement for retrieval; it is a
  governed decision layer.

## 3. Two-Track Evaluation

The demo has two explicit tracks. This avoids making LogicPearl look like it
gets cleaner inputs than RAG, while still isolating LogicPearl's decision
layer.

### 3.1 Track A: End-to-End From Request Text

Each pipeline receives only:

- `request_text`
- `agency_name`

Each pipeline must produce:

- `verdict`: one of `b1`..`b9` or `releasable`
- `rationale`
- citation data, if applicable

This track answers:

> If I plug each system into the real intake workflow, what happens?

Track A includes all sources of error: messy text, extraction mistakes,
retrieval misses, prompt instability, and decision mistakes.

### 3.2 Track B: Shared Facts / Governed Decision

A single shared extractor converts each request into a feature vector.
Then every decision system receives the same extracted facts.

Inputs:

- `request_text`
- `agency_name`
- `shared_extracted_features`
- retrieval context, for RAG and ChunkLookup only

This track answers:

> Given the same extracted facts, which system makes a governable
> decision?

Track B is not an end-to-end benchmark. It is a decision-layer benchmark.
The README must say this directly.

### 3.3 Why Track B Is Fair

The unfair comparison would be giving LogicPearl structured facts while making
RAG infer facts from raw prose.

This design does not do that. In Track B:

- LogicPearl receives the shared feature vector.
- RAG receives the same shared feature vector in its prompt.
- RAG-ChunkLookup receives the same shared feature vector in its prompt.
- The shared extractor prompt, model, outputs, and hashes are checked in.

The comparison isolates what happens after fact extraction.

## 4. Architecture

```
               ┌─────────────────────────────────────────┐
               │ 100 real FOIA scenarios from MuckRock   │
               │ request_text, agency, gold exemption    │
               └────────────────────┬────────────────────┘
                                    │
                 ┌──────────────────┴──────────────────┐
                 │                                     │
                 ▼                                     ▼
       ┌─────────────────────┐              ┌─────────────────────┐
       │ Track A: End-to-End │              │ Track B: Shared Facts│
       └──────────┬──────────┘              └──────────┬──────────┘
                  │                                    │
                  │                         ┌──────────▼──────────┐
                  │                         │ Shared LLM Extractor │
                  │                         │ request -> features  │
                  │                         └──────────┬──────────┘
                  │                                    │
        ┌─────────┼─────────┐                ┌─────────┼─────────┐
        ▼         ▼         ▼                ▼         ▼         ▼
      RAG   ChunkLookup    LogicPearl              RAG   ChunkLookup    LogicPearl
       │         │         │                │         │         │
       └─────────┴─────────┘                └─────────┴─────────┘
                  │                                    │
                  └──────────────────┬─────────────────┘
                                     ▼
                          compare.py / README tables
```

Model default: `gpt-4o-mini`, temperature 0, configurable through
`LP_LLM_MODEL`.

Retrieval corpus:

- 5 U.S.C. § 552
- DOJ FOIA Guide exemption chapters
- 28 CFR Part 16

No MuckRock agency response text is included in the retrieval corpus.
Gold labels are derived from agency response text, so including it would
be circular.

## 5. Dataset

### 5.1 Source

MuckRock public FOIA request API:

`https://www.muckrock.com/api_v1/`

Use a descriptive User-Agent and authenticated JWT from:

`https://accounts.muckrock.com/api/token/`

### 5.2 Selection Rule

Apply filters in this order and record every yield:

1. Federal jurisdiction only: `jurisdiction=10`.
2. Status in `{partial, rejected}` for v1.
3. At least one non-autogenerated agency response communication.
4. Final agency response text has at least 300 characters of substantive
   prose after boilerplate stripping.
5. Request intake body has at least 200 characters after boilerplate
   stripping.
6. Response text contains at least one FOIA exemption citation.
7. Primary citation is extractable.
8. De-duplicate by normalized first 200 characters of request body.

V1 intentionally focuses on agency-denied or partially denied requests.
The README must describe the task as:

> Predict the exemption the agency cited from the request intake text.

It must not imply full legal adjudication.

### 5.3 Optional Releasable Stratum

If implementation time allows, add a small released/no-exemption stratum:

- 25 federal `done` requests with no exemption citation in final response.
- Gold label: `releasable`.
- Report results both with and without this stratum.

Default for v1: defer this unless it is cheap.

### 5.4 Snapshot

The implemented benchmark saves the selected scenarios to:

`scenarios/muckrock_snapshot.100.live.json`

The snapshot is checked into the repo if license, ToS, and privacy review
permit redistribution.

Record shape:

```json
{
  "id": 156090,
  "muckrock_url": "https://www.muckrock.com/foi/...",
  "agency_name": "Federal Bureau of Investigation",
  "agency_id": 8,
  "filed_date": "2020-06-12",
  "status": "partial",
  "request_text": "<cleaned intake body>",
  "response_text": "<cleaned final agency response>",
  "primary_exemption": "b7",
  "all_cited_exemptions": ["b7", "b6"],
  "extraction_confidence": "regex",
  "retrieved_at": "2026-04-17T12:00:00Z"
}
```

Avoid checking in raw request/response text unless privacy review says it
is safe and necessary. Prefer cleaned text plus MuckRock URLs.

### 5.5 Privacy and ToS Review

Before publishing the snapshot:

- read MuckRock ToS;
- confirm redistribution is permitted;
- scan for emails, phone numbers, addresses, signatures, and sensitive
  personal data;
- redact if needed;
- if redistribution is not safe, ship scenario IDs plus extraction
  scripts instead of full text.

## 6. Gold Labels

Gold labels are the exemptions the agency actually cited in its response.
They are not assumed to be legally correct.

### 6.1 Extraction

Use a three-tier label extractor:

1. Regex tier: assign primary if exactly one distinct exemption appears.
2. Ordered tier: if multiple exemptions appear, assign the first one in
   the substantive denial paragraph.
3. LLM tier: for ambiguous cases, use a strict schema and drop low
   confidence outputs.

Store both:

- `primary_exemption`
- `all_cited_exemptions`

### 6.2 Manual QA

Manually spot-check at least 20 randomly sampled scenarios.

If extraction error exceeds 15%, fix extraction logic and rerun the full
snapshot build.

### 6.3 README Caveat

The README should include this caveat:

> Gold labels are the exemptions agencies cited in their denial or partial
> denial letters. Agencies can be wrong; appeals and litigation exist for
> a reason. This eval measures whether a system predicts the agency-cited
> classification from request intake text.

## 7. Shared Feature Extraction

### 7.1 Purpose

The extractor is a shared LLM component, not a LogicPearl-only advantage.
It converts noisy FOIA request prose into a structured fact vector used by
Track B.

### 7.2 Extractor Inputs

- `request_text`
- `agency_name`

Forbidden inputs:

- `status`
- `response_text`
- `response_text_raw`
- `primary_exemption`
- `all_cited_exemptions`
- `muckrock_url`

### 7.3 Extractor Output

Output strict JSON:

```json
{
  "features": {
    "request_for_law_enforcement_investigation_records": true,
    "request_targets_specific_named_individual": true,
    "request_for_internal_deliberative_email_chain": false
  },
  "evidence": {
    "request_for_law_enforcement_investigation_records": "records from FBI investigative file",
    "request_targets_specific_named_individual": "request names John Doe"
  },
  "uncertain_features": ["request_contains_confidential_source_material"]
}
```

Every feature must be boolean. Uncertainty is recorded separately and
does not produce a third truth value.

### 7.4 Feature Dictionary

The feature dictionary should be readable and request-shaped.

Include features for:

- law enforcement records;
- named private individuals;
- personnel files;
- medical/privacy records;
- confidential sources;
- internal deliberative communications;
- attorney-client or attorney work product records;
- trade secrets or confidential commercial records;
- classified or national security records;
- financial institution supervision records;
- geological/geophysical records;
- agency operational methods or investigative techniques.

Keep the feature set small enough for a reader to inspect. Prefer 30-45
well-named features over a large opaque taxonomy.

### 7.5 Extractor Metrics

Report extractor stability and quality separately:

- feature-vector byte-identical rate across 3 reruns;
- per-feature agreement across 3 reruns;
- manual spot-check accuracy on 20 scenarios;
- number of uncertain features emitted.

## 8. Pipelines

### 8.1 RAG

Track A:

- retrieves chunks from the legal corpus;
- LLM receives request text, agency name, and retrieved context;
- LLM emits verdict, rationale, and freeform cited excerpts.

Track B:

- same as Track A, but prompt also receives shared extracted features;
- prompt instructs the model to treat shared features as authoritative
  facts about the request.

Known failure mode: freeform excerpt fabrication.

### 8.2 RAG-ChunkLookup

Track A:

- retrieves chunks from the legal corpus;
- chunks are labeled `[c1]`, `[c2]`, etc.;
- LLM emits verdict, rationale, and cited chunk IDs;
- backend resolves cited IDs to exact chunk text.

Track B:

- same as Track A, with shared extracted features included in prompt.

Excerpt fabrication is structurally prevented. Unsupported or irrelevant
citations are still possible.

### 8.3 LogicPearl LogicPearl

Track A:

- LLM extracts features from request text;
- feature vector is passed to `logicpearl run`;
- LogicPearl emits deterministic verdict, rule ID, and authority IDs;
- LLM may write a rationale, but code overwrites verdict and authority
  fields from the rule output.

Track B:

- uses the shared feature vector;
- no LogicPearl-specific extractor is used;
- feature vector is passed directly to `logicpearl run`.

In both tracks, the LLM cannot override the LogicPearl verdict.

### 8.4 LogicPearl Rule Artifact

The demo should expose a human-readable ruleset layer, not only generated
JSON.

Example public rule shape:

```text
rule b7c_law_enforcement_privacy:
  when request_for_law_enforcement_investigation_records
   and request_targets_specific_named_individual
  then exemption = b7
  because "Disclosure could reasonably be expected to constitute an unwarranted invasion of personal privacy."
```

The compiled artifact must include:

- rule version;
- source manifest hash;
- feature dictionary hash;
- authority quote/source IDs;
- build timestamp.

## 9. Decision Governance Demo

This section is the LogicPearl centerpiece.

### 9.1 Rule Diff Demo

Include at least two ruleset versions:

- `pearl/rulesets/v1`
- `pearl/rulesets/v2`

Show a real rule update, such as splitting a broad `b7` rule into more
specific privacy/confidential-source/investigative-technique rules.

The README should show:

```bash
logicpearl diff pearl/rulesets/v1 pearl/rulesets/v2
```

And a small table:

| Scenario | v1 verdict | v2 verdict | Why changed |
|---|---:|---:|---|
| FBI records about named person | b7 | b7 | privacy subrule added |
| DEA informant records | b7 | b7 | confidential-source rule added |

If the top-level exemption stays `b7`, the explanation/rule ID should
still change and be visible.

### 9.2 Regression Demo

Add a regression command:

```bash
make regression
```

It should verify:

- expected scenarios still produce expected verdicts;
- only intended scenarios changed between ruleset versions;
- every rule has at least one trace or an explicit `untested` marker;
- every emitted authority ID resolves to a source in the corpus manifest.

### 9.3 Version Pinning

Each LogicPearl run records:

- ruleset version;
- compiled artifact hash;
- feature dictionary hash;
- extractor prompt hash;
- model name;
- corpus manifest hash.

This lets the README say:

> The ruleset decision can be pinned to an artifact. A future run can tell
> whether a verdict changed because the facts changed, the rules changed,
> the corpus changed, or the LLM extractor changed.

## 10. Evaluation Metrics

### 10.1 Correctness

Report:

- strict correctness: `verdict == primary_exemption`;
- lenient correctness: `verdict in all_cited_exemptions`;
- optional releasable correctness if releasable stratum exists.

Headline table uses test-set numbers only.

### 10.2 Citation Faithfulness

For RAG:

- faithful excerpt: excerpt is a verbatim substring of a retrieved chunk;
- corpus-backed but not retrieved: excerpt exists in corpus but not in
  retrieved context;
- fabricated excerpt: excerpt is not found in the corpus;
- no citation emitted: counted separately.

For ChunkLookup:

- invalid chunk ID rate;
- resolved citation count;
- unsupported citation examples, if obvious.

For LogicPearl:

- N/A for freeform excerpt fabrication;
- authority IDs must resolve to known source quotes in the ruleset/corpus
  manifest.

### 10.3 Determinism and Stability

Run each scenario 3 times.

Report separately:

- full JSON byte-identical rate;
- verdict-stable rate;
- feature-vector byte-identical rate;
- LogicPearl verdict determinism given fixed features;
- rationale byte-identical rate, if rationale is LLM-written.

Expected result:

- LogicPearl verdict given fixed facts: 100%.
- End-to-end LogicPearl: may vary if extractor varies.
- RAG and ChunkLookup: may vary in verdict, rationale, or citation choice.

### 10.4 Governance Capabilities

Add a capability table:

| Capability | RAG | ChunkLookup | LogicPearl LogicPearl |
|---|---:|---:|---:|
| Freeform excerpt fabrication prevented | no | yes | yes |
| Same fixed facts produce same verdict | no | no | yes |
| Decision rule inspectable | no | no | yes |
| Ruleset version pinnable | prompt only | prompt only | compiled artifact |
| Ruleset changes diffable | weak | weak | yes |
| Regression-test ruleset changes | weak | weak | yes |
| Authority IDs machine-resolvable | partial | yes | yes |

This table should be as prominent as the accuracy table.

### 10.5 Runtime and Cost

Track:

- total input/output tokens;
- wall time;
- model name;
- pricing assumptions used at run time.

Do not say only "current pricing." Store pricing assumptions in the
transcript so future readers know what was used.

## 11. Train/Dev/Test Split

Use 100 scenarios unless a releasable stratum is added.

- Dev: 40 scenarios.
- Test: 60 scenarios.

Split method:

- stratified random by `primary_exemption`;
- fixed seed: `random.Random(42)`;
- checked into `scenarios/split.100.live.json`.

Use dev set for:

- extractor prompt tuning;
- feature dictionary tuning;
- LogicPearl decision artifact iteration.

Use test set for:

- final README headline numbers;
- final transcript.

If test set is inspected and the system is changed afterward, disclose it
in the README.

## 12. Repo Structure

```text
rag-vs-pag/
├── README.md
├── Makefile
├── pyproject.toml
├── .env.example
├── corpus/
│   ├── fetch.py
│   ├── sources.toml
│   └── raw/
├── scenarios/
│   ├── muckrock_snapshot.100.live.json
│   ├── split.100.live.json
│   ├── adjudication.100.live.json
│   ├── manual_review.100.live.clean.json
│   ├── archive/
│   └── README.md
├── scripts/
│   ├── adjudicate_benchmark.py
│   ├── apply_manual_clean_review.py
│   ├── make_trace_viewer.py
│   ├── write_final_benchmark_report.py
│   └── corpus_build/
├── extraction/
│   ├── shared_extractor.py
│   ├── feature_dictionary.json
│   ├── extractor_prompt.md
│   └── outputs/
├── pipelines/
│   ├── rag.py
│   ├── rag_chunklookup.py
│   └── logicpearl.py
├── rag/
│   ├── index.py
│   └── retrieve.py
├── pearl/
│   ├── rulesets/
│   │   ├── v1/
│   │   └── v2/
│   ├── build.py
│   ├── artifact/
│   └── traces/
├── compare.py
├── transcripts/
│   ├── final-run.jsonl
│   └── final-summary.md
├── docs/
│   └── plans/
│       └── 2026-04-16-rag-vs-pag-logicpearl-design.md
└── tests/
    ├── test_selection_rule.py
    ├── test_gold_extraction.py
    ├── test_shared_extractor_schema.py
    ├── test_ruleset_regression.py
    └── test_pipelines_smoke.py
```

## 13. Reproduce

Primary flow:

```bash
git clone git@github.com:LogicPearlHQ/rag-vs-pag.git
cd rag-vs-pag
uv sync --extra dev
cp .env.example .env

make fetch
make index
make build
make demo
```

Optional:

```bash
make scrape
make extract
make regression
make diff-ruleset
```

`make demo` should:

- run Track A;
- run shared extraction;
- run Track B;
- compute aggregate metrics;
- write transcripts;
- print the README-ready summary table.

## 14. README Structure

Target length: 250-350 lines.

1. TLDR: LLMs extract facts; LogicPearl governs decisions.
2. Headline capability table.
3. Accuracy and stability tables for Track A and Track B.
4. Methodology in 200 words.
5. Example 1: RAG fabricated an excerpt.
6. Example 2: ChunkLookup fixed excerpt provenance but not verdict
   governance.
7. Example 3: LogicPearl rule diff and regression test.
8. Reproduce commands.
9. Limitations.
10. Credits.

The README should explicitly say:

> The shared-facts track is not an end-to-end benchmark. It isolates the
> decision layer by giving every pipeline the same extracted facts.

## 15. Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---:|---:|---|
| End-to-end LogicPearl accuracy lags RAG | Medium | Medium | Make decision-governance table the headline; report Track A honestly. |
| Shared-facts track looks rigged | Medium | High | Give the same feature vector to all systems and label Track B as decision-layer only. |
| Extractor instability obscures story | Medium | Medium | Report extractor stability separately; pin extractor prompt/model/hash. |
| MuckRock snapshot redistribution is unsafe | Medium | High | Ship IDs + scripts, or redacted cleaned text only. |
| Gold labels contain agency errors | Known | Low | Frame task as agency-cited exemption prediction. |
| Rule diff demo is too abstract | Medium | Medium | Use real scenarios from dev set and show changed rule IDs/outcomes. |
| Dataset overrepresents b6/b7 | High | Medium | Report exemption distribution; stratify if feasible. |
| Runtime exceeds target | Low | Low | Cache retrieval, extraction, and LLM outputs; allow replay from transcripts. |

## 16. Implementation Plan

### Phase 1: Repo and Corpus

- Bootstrap repo with `uv`, Makefile, `.env.example`, and tests.
- Add deterministic corpus fetcher and manifest.
- Build retrieval index.

Acceptance criteria:

- `make fetch` verifies source hashes.
- `make index` builds a local retriever.

### Phase 2: Scenarios

- Implement MuckRock client and selection rule.
- Extract gold labels.
- Redact/clean snapshot.
- Generate `split.json`.

Acceptance criteria:

- 100 usable scenarios or documented fallback count.
- QA spot-check complete.
- Snapshot is safe to publish or replaced by IDs-only plan.

### Phase 3: Shared Extraction

- Write feature dictionary.
- Write shared extractor prompt.
- Implement schema validation.
- Run extractor on dev/test and store outputs.

Acceptance criteria:

- All extractor outputs validate.
- Feature-vector stability is measured.
- Manual spot-check complete.

### Phase 4: Pipelines

- Implement RAG Track A/B.
- Implement ChunkLookup Track A/B.
- Implement LogicPearl Track A/B.
- Ensure all pipelines obey input contracts.

Acceptance criteria:

- Smoke tests pass for one scenario per pipeline per track.
- Forbidden fields are not passed to prompts.

### Phase 5: LogicPearl Governance

- Build human-readable ruleset v1.
- Build ruleset v2 for diff demo.
- Compile artifacts.
- Add regression tests.
- Add ruleset diff command.

Acceptance criteria:

- Fixed feature vectors produce 100% stable LogicPearl verdicts.
- Ruleset diff produces readable output.
- Regression command catches unintended changes.

### Phase 6: Final Eval and README

- Run final test-set sweep.
- Generate transcripts and summary tables.
- Write README.
- Include limitations and exact replay artifacts.

Acceptance criteria:

- README can be understood in 90 seconds.
- Transcript supports every headline number.
- Reproduction path works from a clean clone.

## 17. Open Questions

- Should v1 include the optional releasable stratum?
- How human-reviewed should shared feature vectors be for Track B:
  LLM-only, spot-checked, or fully reviewed?
- Should Track B RAG be forced to treat extracted features as
  authoritative, or allowed to override them from request text?
- How much of the ruleset language should be custom DSL versus generated
  JSON?
- Should published artifacts include full LLM request/response logs or
  only normalized JSON outputs?

## 18. Default Decisions

Unless implementation discovers a blocker:

- Keep v1 to 100 exemption-cited scenarios.
- Add releasable scenarios only if cheap.
- Use the same shared feature vector for all Track B systems.
- Make LogicPearl governance capabilities as prominent as accuracy.
- Treat Track A as deployment realism and Track B as decision-layer
  isolation.
- Publish cleaned/redacted scenario text only after ToS and privacy review.
