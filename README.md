# RAG vs PAG

**Disclosure:** I work on [LogicPearl](https://github.com/LogicPearlHQ/logicpearl).
This repo is a head-to-head between a RAG pipeline and four pearl-based
alternatives on 72 real FOIA classification scenarios. All code, prompts,
and captured transcripts are checked in; the eval is reproducible.

## What this is

Five pipelines, same task — *"classify this FOIA record under
5 U.S.C. § 552(b)"* — same 72 scenarios, same corpus, same LLM (gpt-4o,
temp=0):

- **RAG (baseline):** retrieve chunks, LLM writes answer + citations
- **RAG-ChunkLookup:** retrieve chunks, LLM writes answer + chunk IDs;
  backend resolves IDs to real text. The pattern behind Anthropic's
  Citations API, Cohere's grounded generation, and LangChain's
  source-linked chains.
- **PAG (Pearl-Augmented Generation):** LLM extracts features, a
  compiled pearl artifact applies rules, deterministic verdict
- **PAG-R:** RAG reasoning, pearl feature dictionary for cites only
- **PAG-keyword:** no LLM anywhere; substring matching for extraction,
  pearl for decision, template for rationale

The three questions I wanted the eval to settle:

1. How often does a plain RAG pipeline hallucinate citations?
2. Does LogicPearl fix that problem?
3. If a well-known RAG pattern (chunk-ID indirection) also fixes it,
   what does LogicPearl actually add?

Short answers: often; yes; the decision itself becomes deterministic,
inspectable, and versionable, which is a different property from having
faithful citations.

## The headline numbers

72 scenarios × 3 reruns = 216 runs per pipeline. Gold labels come from
the DOJ OIP *Guide to the FOIA*; every scenario quote is sha256-verified
against the fetched PDF (263 tests enforce it). All numbers below are
from the run *after* the Klamath fix described in Finding 4 was in
place. The Finding 4 section also reports what changed between pre-
and post-fix.

| | RAG | RAG-ChunkLookup | PAG | PAG-R | PAG-keyword |
|---|---|---|---|---|---|
| Correct overall | 89% | 89% | 46% | 85% | 32% |
| Correct on curated (15×3) | 100% | 100% | 82% | 93% | 93% |
| Correct on case-derived (57×3) | 87% | 87% | 36% | 83% | 16% |
| Citation faithfulness | 57% | 100% | 100% | 100% | 100% |
| Fabricated citations | 174 | 0 | 0 | 0 | 0 |
| Byte-identical reruns | 50% | 54% | 57% | 56% | 100% |
| Decision is deterministic? | no | no | yes | no | yes |
| LLM calls / scenario | 1 | 1 | 2 | 1 | 0 |
| Avg latency | 3.7s | 3.7s | 3.8s | 3.7s | <1ms |
| Marginal cost / call | ~$0.01 | ~$0.01 | ~$0.005 | ~$0.01 | $0 |

174 of RAG baseline's 407 citations (43%) are not substrings of the
retrieved text. The LLM wrote quotes that don't exist. The other four
pipelines can't produce that failure mode — none of them let the LLM
write excerpt strings freely.

PAG's 46% deserves a quick explanation now rather than later: that
number is lower than an earlier capture (55%) because the Klamath fix
*tightened* the b5 rule — it now requires a co-feature that the LLM
extractor doesn't always infer correctly from abstract case-derived
descriptions. Finding 4 spells out the tradeoff. PAG-R is unaffected
(it uses the pearl dictionary only for citation lookups, not for
decisions) and sits at 85%.

## Finding 1: RAG fabricates citations, and the rate worsens with scale

At N=15 the faithfulness was 74%. At N=72 it's 58%. More scenarios gave
the LLM more opportunities to paraphrase and stitch quotes together,
and it took them.

Three real examples from the run.

**Ellipsis compression.** RAG cited this as one continuous passage from
§ 552(b)(7):

> *"records or information compiled for law enforcement purposes, but
> only to the extent that the production of such law enforcement
> records or information**...** (D) could reasonably be expected to
> disclose..."*

The `...` elides subclauses (A), (B), and (C) — hundreds of words. The
stitched quote isn't in the statute.

**Plausible fabrication.** Cited as `DOJ FOIA Guide, Exemption 6, p. 14`:

> *"Similarly, civilian federal employees who are not involved in law
> enforcement generally have no expectation of privacy regarding their
> names, titles, grades, salaries, and duty stations..."*

Grammatical, on-topic, real page number. Not what's on page 14 of what
retrieval actually fetched. The LLM drew from its training data (the
DOJ Guide is public) instead of the retrieval.

**Memory-mixed quote.** Retrieval fetched page 40 of Exemption 3. The
LLM ignored the retrieved text and wrote its own phrasing blended with
what it remembers. The citation points at a real page; the quoted
excerpt isn't in that page's text.

A human reviewer would probably accept all three at a glance. The
automated substring check is what flagged them.

## Finding 2: Chunk-ID indirection fixes the fabrication, without a pearl

RAG-ChunkLookup restructures the LLM's output. Retrieved chunks are
labeled in the prompt (`[c1] [c2] ...`), and the schema asks for
`cited_chunk_ids: ["c1", "c5"]` rather than excerpt strings. Excerpts
are looked up server-side from the real retrieval. If the LLM
references an ID that wasn't in the retrieval, the citation is dropped.

The pattern is old news in production RAG — Anthropic Citations,
Cohere grounded generation, and LangChain all ship versions of it. This
repo just has a minimal in-tree implementation so we can measure it.

Result: **RAG-ChunkLookup gets 88% correctness and 100% citation
faithfulness.** That's essentially RAG's correctness with zero
fabricated cites, and it uses no pearl. If the only thing wrong with
your RAG system is made-up citations, switching to chunk-ID indirection
is the right fix.

## Finding 3: Chunk-ID indirection doesn't fix wrong verdicts

The chunk-ID fix guarantees one thing: the quoted excerpt is real bytes
from a real retrieved chunk. It doesn't check that the cited chunk
supports the verdict the LLM wrote, or that the rationale text
corresponds to what the chunk actually says.

The clearest example is the Klamath scenario. *Department of Interior
v. Klamath Water Users Protective Ass'n*, 532 U.S. 1 (2001). Scenario
description, verbatim from DOJ Guide Exemption 5, p. 5:

> *"A FOIA request seeks the following records: communications between
> the Department of the Interior and several Indian tribes which, in
> expressing their views to the Department on certain matters of
> administrative decisionmaking."*

Gold label: `releasable`. The Supreme Court held unanimously that the
threshold of Exemption 5 doesn't encompass communications with tribes,
because tribes have "their own, albeit entirely legitimate, interests"
and were "seeking a Government benefit." Tribes aren't agencies for
(b)(5) purposes.

On all LLM pipelines, retrieval returned the same 8 chunks — and *none*
of them were about Exemption 5. The ranker surfaced 28 CFR admin rules
and DOJ Guide Exemption 6 pages (privacy interests, unrelated). Four
pipelines produced four different verdicts.

- **RAG (baseline):** `insufficient_context`, confidence `low`.
  Rationale: *"The retrieved excerpts do not provide specific
  information... a determination cannot be made."* The only pipeline
  that admitted retrieval had failed.
- **RAG-ChunkLookup:** `b5`, confidence `high`. Wrote a full
  Exemption 5 rationale from its training memory. Cited two real
  chunks — both about Exemption **6** (privacy interests), not
  Exemption 5. The citations passed the "is this a real substring"
  check; the rationale it was paired with was about something else.
- **PAG (LLM extracts features):** `b5`. The LLM read "communications
  between DOI and tribes" and set `inter_or_intra_agency_memo` and
  `pre_decisional_deliberative` to TRUE. The pearl's statute-literal
  rule fired. Same wrong answer as RAG-ChunkLookup, same root cause:
  the LLM paraphrased *tribes* as *agency*.
- **PAG-keyword:** `releasable`. The keyword dictionary for
  `inter_or_intra_agency_memo` contains literal triggers like
  `"inter-agency memo"` — none of them match "communications
  between... and Indian tribes." No feature fires. The pearl defaults
  to releasable, which happens to be Klamath's answer.

Three things to take from this.

First, "100% citation faithfulness" is a real metric but a narrow one.
It tells you the bytes you're quoting exist somewhere; it doesn't tell
you the cited chunk supports the claim you're making. RAG-ChunkLookup
cited Exemption 6 pages under an Exemption 5 answer with high
confidence. The cites are real, the pairing is wrong.

Second, only the pearl makes the verdict deterministic. Four pipelines
ran the same input and produced four different verdicts; PAG and
PAG-keyword are the only two that will give the same answer on every
rerun by construction.

Third, keyword-mode PAG happened to get this one right — but read
that carefully. The keyword dictionary didn't contain *"tribes"* or
*"Indian tribe"* at the time, so those phrases failed to match any
feature and the pearl defaulted to releasable. That's a coincidence of
this scenario's wording, not a principled safeguard. A scenario
describing the same records as *"Native American sovereign nations"*
or *"external parties"* would have blown through keyword mode the
same way. The Klamath fix described in Finding 4 replaces this
coincidence with explicit negative keywords; the fix is the
principled version.

## Finding 4: The pearl has to encode the doctrine

PAG got Klamath wrong because the pearl's feature dictionary didn't
contain the thing Klamath turned on — *who the other party actually
is*. The statute says "inter-agency or intra-agency memorandums"; case
law says not-so-fast if the counterparty has adverse interests. The
pearl faithfully applied the statute's face, which is wrong after
Klamath.

The fix on the pearl side is a code change with a clear diff.

```json
// pearl/feature_dictionary.json — add feature
"other_party_is_federal_agency_or_consultant": {
  "label": "Communication counterparty is another federal agency or a bona fide agency-solicited consultant",
  "cite": "Dep't of Interior v. Klamath, 532 U.S. 1 (2001)",
  "keywords": ["intra-agency", "between agencies", "another federal agency", ...],
  "negative_keywords": ["indian tribe", "tribes", "tribal", "private party", "their own interests", ...]
}

// pearl/statute_structure.json — b5 now requires the new feature
"b5": { "groups": [{
  "features": ["inter_or_intra_agency_memo", "pre_decisional_deliberative",
               "other_party_is_federal_agency_or_consultant"], ...
}]}

// pearl/statute_structure.json — new Klamath-specific release pattern
{
  "features": ["inter_or_intra_agency_memo", "pre_decisional_deliberative"],
  "quote": "the threshold of Exemption 5 did not encompass communications between the Department of the Interior and several Indian tribes",
  "source_doc": "doj_guide_exemption_5",
  "source_page": 5
}
```

Quote verification was extended to accept `source_doc`/`source_page`
refs into the fetched DOJ Guide PDFs, so the case-law quote is
auto-verified the same way the statute quotes are. Trace generator
regenerates, pearl rebuilds at 100% training parity, 263 tests pass.

After the fix, on Klamath specifically:

- **PAG:** `releasable`. The LLM sets
  `other_party_is_federal_agency_or_consultant = FALSE` for the tribes
  case; the new inverse rule fires.
- **PAG-keyword:** `releasable`. "Indian tribes" is a negative trigger
  on the new feature; nothing fires; the pearl defaults.
- **RAG and RAG-ChunkLookup:** unchanged. They don't consult the pearl.
  Their Klamath failure was in the retrieval + LLM-inference layer,
  which a pearl-side fix doesn't touch.

**The fix is not free, and the rerun proved it.** Re-running all five
pipelines on all 72 scenarios *after* the fix shows PAG's overall
correctness dropped from 55% to 46% and PAG-keyword from 35% to 32%.
The reason: the new b5 co-requirement tightened the rule, which is
correct by doctrine — but the LLM extractor doesn't always set
`other_party_is_federal_agency_or_consultant = TRUE` on the case-
derived b5 scenarios described in abstract DOJ Guide parenthetical
prose like *"documents prepared by attorney hired by private company
in contractual relationship with agency."* Per Klamath, this type of
agency-retained-consultant should qualify, but the LLM extractor
leans toward FALSE when it sees "private company." About ten
previously-correct b5 case-derived scenarios flipped to `releasable`
because the new required feature wasn't set.

PAG-R, which uses the pearl dictionary only as a cite vocabulary and
not for decisions, stayed put at 85%. RAG and RAG-ChunkLookup are
unaffected by pearl-side changes (they're at 89%).

That's the honest maintenance cost: **each doctrinal feature added to
the pearl requires matching investment in the extractor layer**
(better prompting, richer keyword lists, or more trace examples
showing the feature TRUE in realistic scenarios). In a production
deployment the two would evolve together under ongoing review by a
domain expert. This demo captures one fix cycle — doctrine in,
extractor lags, rule tightens, some scenarios regress, more work to
do. Not every fix is a net win on the day it ships; the win is the
ongoing ability to *add doctrine as a reviewable diff*, with the
understanding that each diff has a cost.

The broader point holds: the pearl fix is reviewable as a code diff,
pins to a new artifact hash, and can be versioned against a specific
date. Fixing the same class of failure on the RAG side means
retrieval tuning, query expansion, or case-law-aware prompting — real
engineering, but without a single reviewable artifact you can point
at and say *"this is the ruleset in force as of March 3."*

I only added a feature for Klamath because Klamath surfaced in the
eval. There are ~15 other case-derived scenarios where PAG misses
for similar case-law reasons (other consultant-corollary cases,
privacy-waiver doctrines, etc.). Those would need analogous features
+ quotes + inverse patterns + extractor updates. I didn't build those.
This one fix is a demonstration of the maintenance cycle, not a
complete encoding of FOIA doctrine.

## Finding 5: Where each pipeline actually fits

| Requirement | Pick |
|---|---|
| Open-ended synthesis, research, summarization | RAG or RAG-ChunkLookup; PAG is a classifier |
| Citations must be real, correctness can be LLM-driven | RAG-ChunkLookup |
| Verdict must be provably deterministic (same input → same output, byte-identical) | PAG |
| Decision logic must be inspectable, diffable, versionable for audit | PAG |
| Zero-cost classification at scale; offline or air-gap deployment | PAG-keyword |
| Tightly-reviewed cite vocabulary (20-entry dictionary) | PAG-R |

Short version: PAG is better when the *decision* needs audit
properties, not just the citations. If all you need is non-fabricated
cites, use RAG-ChunkLookup.

## What this demo isn't

- A statistical benchmark. N=72 on one corpus. The percentages are
  directionally useful, not a leaderboard entry.
- Legal advice. Every piece of the repo — traces, scenarios, LLM
  outputs — is illustrative.
- A claim that PAG wins every category. It doesn't. See Finding 5.

## Audit surface

The entire trust surface of the pearl is three JSON files and one
generator, all human-readable, all quote-verified against federal text:

- [`pearl/feature_dictionary.json`](pearl/feature_dictionary.json) — 21
  features. Each feature's `cite` and `label` are grounded (the cite is
  a real statute clause or case, the label is short human prose). The
  `keywords` and `negative_keywords` lists are engineering choices I
  wrote; they are not auto-verified against the corpus and are the
  weakest link in the trust chain. A production deployment would have
  these reviewed by a domain expert (a FOIA officer, in this case).
- [`pearl/statute_structure.json`](pearl/statute_structure.json) —
  element groups per exemption plus case-law release patterns. Every
  quote is a verbatim substring of either 5 U.S.C. § 552 or a named
  page of a fetched DOJ Guide PDF, checked on every build.
- [`scenarios/cases.json`](scenarios/cases.json) — 57 case-derived
  scenarios with verbatim record-description and outcome quotes; 174
  tests verify the substrings against the fetched DOJ Guide PDFs.
- [`scenarios/*.json`](scenarios/) (top-level) — 15 curated diagnostic
  scenarios. I wrote these; they're designed to probe specific
  statute-literal patterns. They are not extracted from anything, and
  a reviewer who thinks they look contrived should say so.
- [`pearl/generate_traces.py`](pearl/generate_traces.py) — deterministic
  trace generator, idempotence tested.
- [`scripts/find_case_candidates.py`](scripts/find_case_candidates.py) —
  the tool that extracted the 57 case-derived scenarios via regex over
  the DOJ Guide PDF parenthetical case summaries. Its heuristics
  (positive/negative outcome cue words) influence which cases were
  included; worth reading before trusting the scenario mix.

If the comparison looks rigged, flip a row, swap a scenario, rewrite a
quote. The eval rebuilds in about 30 seconds for PAG, a few minutes
for the 5-way sweep.

## Reproduce

```bash
git clone git@github.com:LogicPearlHQ/rag-vs-pag.git
cd rag-vs-pag
uv sync --extra dev
cp .env.example .env   # OPENAI_API_KEY

# ~10 min total, ~$15-20 of gpt-4o tokens for the full 5-way run
make fetch       # download statute + 9 DOJ Guide chapters + 28 CFR Part 16
make index       # chunk + embed for RAG baseline
make build       # build the LogicPearl artifact from traces.csv
make demo        # RAG + PAG (LLM mode) on 72 scenarios × 3 reruns

# Other configurations
uv run python compare.py --rag-impl chunklookup --pearl-impl r --repeat 3
uv run python compare.py --pearl-extractor keyword --skip-rag --repeat 3
```

Captured runs are in [`transcripts/`](transcripts/).

## How the pipelines actually work

**RAG (baseline).** Retrieve 8 chunks via hybrid BM25 + dense
(text-embedding-3-small) with cross-encoder rerank
(ms-marco-MiniLM-L-6-v2). Give the LLM the chunks and the question,
ask it to emit `{exemption, rationale, cited_authorities: [{cite,
excerpt}]}`. The excerpt is a string the LLM writes.

**RAG-ChunkLookup.** Same retrieval. Chunks are labeled `[c1] [c2] ...`
in the prompt; the LLM emits `cited_chunk_ids: ["c1", "c5"]`; the
backend resolves each ID and fills in the real chunk bytes. The LLM
never writes excerpt text.

**PAG.** No retrieval. One LLM tool-call extracts a boolean feature
vector from the description. The vector goes to `logicpearl run`, a
compiled Rust rule evaluator (~10 ms). The pearl emits a verdict and
which rule fired. A second LLM call writes a plain-English rationale
citing the authorities the pearl provided; code overwrites the verdict
and releasable fields from the pearl, so the LLM can't change them.

**PAG-R.** Same retrieval as RAG. LLM reads the chunks and decides
(like RAG). LLM also names which features from the pearl's dictionary
apply; cites are looked up from those feature names. The pearl's rule
engine is not invoked — the dictionary is used purely as a constrained
cite vocabulary.

**PAG-keyword.** No LLM at runtime. A keyword extractor (substring
matching over a positive/negative keyword list per feature) produces
the feature vector. The pearl decides. A Python template generates the
rationale from the rule output.

## What chunk-ID indirection doesn't fix

The architecture guarantees the quoted excerpt is real bytes from a
real retrieved chunk. It doesn't guarantee any of these:

- The verdict is correct. Still LLM-generated.
- The rationale corresponds to the cited chunk. The LLM writes the
  rationale freely; nothing checks that the chunk actually says what
  the rationale claims.
- The cited chunk is on-point for the answer. The LLM can pick a
  topically-related chunk that doesn't actually support the specific
  claim it's making. Klamath above is a concrete example of this.
- The decision is deterministic. LLMs drift across reruns even at
  temp=0.

PAG and PAG-keyword are the only pipelines where the verdict is
deterministic. PAG-keyword is the only one where the entire output is
a deterministic function of the input.

## Limitations

- N=72 is small. Percentages are useful as directional evidence, not
  population estimates.
- The corpus is pedagogical: statute + 9 DOJ Guide chapters + 28 CFR
  Part 16. No court opinions (CourtListener's free API requires a
  token). Real FOIA work involves segregability, foreseeable-harm
  balancing, and case-law nuance that the pearl only partially covers.
- RAG didn't get a parallel refinement pass. PAG got two (trace-set
  expansion after the first run surfaced a greedy-rule issue; the
  Klamath feature after the case-law issue). A serious RAG team could
  probably close part of the correctness gap on case-derived scenarios
  with better retrieval, query expansion, or agentic reasoning. The
  claim isn't that RAG can't be improved; it's that PAG's fixes are
  artifact-level changes with clear diffs, and RAG's fixes are
  system-level behavior changes without a reviewable artifact.
- The case-derived scenarios are auto-extracted from DOJ Guide
  parenthetical prose, which is condensed doctrinal shorthand and not
  how real FOIA intake is worded. Both pipelines would likely do
  better on natural-language record descriptions.
- Only gpt-4o at temp=0. The provider is pluggable
  (`LP_LLM_PROVIDER=anthropic|openai|ollama`); Anthropic and Ollama
  backends are smoke-tested. Fabrication rates may shift with other
  models; the pipeline topology doesn't.
- Not legal advice.

## Layout

```
corpus/                 fetched federal docs, sha256-verified
ragdemo/                shared libs: LLM providers, chunking, scenarios
rag/
  rag.py                baseline RAG (LLM writes cites)
  rag_chunklookup.py    chunk-ID indirection variant
  retrieve.py           hybrid BM25 + dense + cross-encoder rerank
  index.py              one-time corpus indexing
pearl/
  feature_dictionary.json  21 features, statute cites, keyword triggers
  statute_structure.json   element groups + case-law release patterns
  generate_traces.py       deterministic trace generator
  pearl.py                 PAG runner (LLM or keyword extractor)
  pearl_r.py               PAG-R (RAG decides, pearl dict for cites)
  keyword_extractor.py     deterministic substring extractor
scenarios/
  *.json                15 curated diagnostic scenarios
  cases.json            57 case-derived scenarios (verbatim quotes + cites)
  cases/                generated scenario files
compare.py              side-by-side harness
transcripts/            captured runs (5 pipelines × N=72)
docs/
  findings.md           long-form writeup
  plans/                design and implementation plan
```

## Credits

- **[LogicPearl](https://github.com/LogicPearlHQ/logicpearl)** — the
  deterministic rule engine and `logicpearl` CLI.
- Corpus from [law.cornell.edu](https://www.law.cornell.edu/uscode/text/5/552),
  [justice.gov/oip/foia-guide](https://www.justice.gov/oip/foia-guide),
  [ecfr.gov](https://www.ecfr.gov/); federal works, public domain.
- `gpt-4o` at temp=0 for LLM calls.
- Chunk-ID indirection is the pattern behind
  [Anthropic Citations](https://docs.anthropic.com/en/docs/build-with-claude/citations),
  Cohere's grounded generation, and LangChain's source-linked chains;
  this repo has a minimal in-tree implementation for measurement.
