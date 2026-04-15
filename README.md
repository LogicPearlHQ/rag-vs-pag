# rag-demo — Replacing RAG With LogicPearl For An LLM

An end-to-end demo on 15 FOIA record-classification scenarios against real
federal primary sources (5 U.S.C. § 552, DOJ OIP FOIA Guide, 28 C.F.R.
Part 16). Same LLM, same corpus, three backends compared side by side.

## Results

| | **RAG** | **Pearl (LLM extract)** | **Pearl (keyword extract)** |
|---|---|---|---|
| Correct | 45 / 45 (100%) | 42 / 45 (93%) | 42 / 45 (93%) |
| **Byte-identical full output** | 25 / 45 (56%) | 20 / 45 (44%) | **45 / 45 (100%)** |
| **Citation faithfulness** | **70 / 94 (74%)** | **57 / 57 (100%)** | **72 / 72 (100%)** |
| LLM calls per scenario | 1 | 2 | **0** |
| Avg latency | 3.7 s | 3.8 s | **<1 ms** |
| Marginal cost per run | ~$0.01 | ~$0.005 | **$0** |

Correctness is comparable on this benchmark. The separators are
**citation faithfulness** (LogicPearl paths are 100% by construction;
RAG's 74% is LLM-bounded) and **full-output reproducibility** (only the
keyword-mode pearl achieves 100% byte-identical reruns, because there is
no LLM in its pipeline to drift).

**Full writeup with prompts, failure modes, captured output, and
fairness notes:** [`docs/findings.md`](docs/findings.md).

## How it works

Three pipelines over the same FOIA corpus:

```
RAG:          text ──► retrieve 8 chunks ──► LLM synthesizes answer + cites

Pearl (LLM):  text ──► LLM extracts {feature: bool} ──►
              ──► logicpearl run (Rust engine, no LLM) ──► decision ──►
              ──► LLM writes prose (cannot change the verdict)

Pearl (kw):   text ──► keyword substring match ──►
              ──► logicpearl run (Rust engine, no LLM) ──► decision ──►
              ──► Python template rationale
```

The LogicPearl engine makes **zero LLM calls** — it's a compiled rule
evaluator in Rust (~10 ms per scenario). The demo's wrapper around it
uses an LLM to normalize free text into a feature vector (LLM mode) or
a keyword extractor (keyword mode). In both cases, the pearl's verdict
is authoritative — the code architecturally prevents any LLM from
overriding it.

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
LP_PEARL_EXTRACTOR=llm          # or keyword (fully LLM-free pearl)
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
