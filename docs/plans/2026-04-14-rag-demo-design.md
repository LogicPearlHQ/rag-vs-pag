# RAG Demo — Replacing RAG With LogicPearl For An LLM

**Date:** 2026-04-14
**Status:** Design approved, ready for implementation planning.
**Repo:** `~/Documents/LogicPearl/rag-demo`

## Goal

Build an end-to-end demo that shows, on real legal primary sources, how
LogicPearl can replace a retrieval-augmented generation (RAG) pipeline as the
*decision* layer an LLM uses. Both paths consume the same FOIA corpus; only the
way the final decision is produced differs.

- **RAG path**: corpus → chunk + hybrid index → retrieve → LLM synthesizes an
  answer with citations.
- **LogicPearl path**: corpus → reviewed, citation-bearing traces → deterministic
  pearl artifact. At runtime the LLM normalizes a free-text record description
  into structured features, the pearl decides, the LLM explains the
  artifact's decision without being allowed to change it.

The demo is a *fair contest*: same model, same temperature, same scenarios,
same corpus, a strong RAG baseline (hybrid retrieval + rerank + structured JSON
output + citation-faithfulness check), and at least one scenario RAG is
supposed to win. The three honest headlines the comparison is designed to
surface are **determinism**, **citation faithfulness**, and **refusal quality**.

## Domain

FOIA exemptions — 5 U.S.C. § 552(b). Nine numbered exemptions, each a
plain-text, crisp-enough-to-encode definition in federal statute. Classic real
RAG use case; classic domain where determinism and "which exemption fired"
matter.

## Corpus (shared across both paths)

Canonical list in `corpus/sources.toml`, pinned URLs, sha256-verified by
`corpus/fetch.py`, written to `corpus/raw/`. A small snapshot of the statute
text lives at `corpus/snapshot/` checked into git so the demo reproduces
offline if URLs break.

| Source | Format | Role |
| --- | --- | --- |
| 5 U.S.C. § 552 | plain text (Cornell LII) + PDF (govinfo.gov) | the statute |
| DOJ OIP *Guide to the FOIA* | per-exemption PDFs from justice.gov/oip/foia-guide | canonical interpretive manual |
| 28 C.F.R. Part 16 | text from eCFR | DOJ's FOIA regulations |
| Selected FOIA case opinions | ~10 landmark cases from CourtListener free API | case law context |

All federal works (public domain) except CourtListener opinions, which are
public-domain court text redistributed under CourtListener's terms.
`corpus/ATTRIBUTIONS.md` records this.

Chunking is structure-aware (statute subsection, DOJ Guide heading, CFR
section, case paragraph), and every chunk carries
`{source, cite, exemption_hint?, page?}` metadata so answers can cite back into
real files.

## Architecture

Two runners + shared libs.

```text
rag-demo/
├── README.md
├── pyproject.toml                # deps: anthropic, openai, httpx, pypdf,
│                                 # chromadb, rank_bm25, sentence-transformers,
│                                 # rich, ollama
├── .env.example                  # ANTHROPIC_API_KEY, OPENAI_API_KEY,
│                                 # LP_LLM_PROVIDER, LP_EMBEDDING_PROVIDER
├── Makefile                      # fetch, index, build, demo
├── corpus/
│   ├── sources.toml
│   ├── fetch.py
│   ├── ATTRIBUTIONS.md
│   ├── raw/                      # gitignored; populated by fetch.py
│   └── snapshot/                 # checked-in fallback (statute text only)
├── ragdemo/                      # shared Python package
│   ├── __init__.py
│   ├── llm.py                    # provider-agnostic LLM interface
│   ├── corpus.py                 # load + structure-aware chunking
│   └── scenarios.py              # scenario loader, shared shape
├── scenarios/                    # ~15 .json scenarios
├── rag/
│   ├── index.py                  # one-time: chunk -> Chroma + BM25
│   ├── rag.py                    # runner
│   └── README.md
├── pearl/
│   ├── traces.csv                # reviewed, citation-bearing
│   ├── traces_review.md          # generated audit artifact
│   ├── feature_dictionary.json
│   ├── build.sh                  # wraps `logicpearl build ...`
│   ├── artifact/                 # gitignored; built by build.sh
│   └── pearl.py                  # runner
├── compare.py                    # drives both, writes transcripts/
└── transcripts/
```

## LLM abstraction

`ragdemo/llm.py` exposes a single provider-agnostic interface with three
implementations selected by `LP_LLM_PROVIDER` (default `anthropic`):

- **Anthropic** — `claude-opus-4-6`, Messages API, tool-use, strict JSON via
  tool schema, prompt caching on the RAG system prompt + retrieved-chunks
  block.
- **OpenAI** — `gpt-4o` / `gpt-4o-mini`, Responses API, tool-use, structured
  output.
- **Ollama** — `llama3.1:8b` chat + `bge-m3` embeddings, fully offline.

Embeddings are abstracted separately via `LP_EMBEDDING_PROVIDER`: default
OpenAI `text-embedding-3-small`, local fallback `BAAI/bge-small-en-v1.5` via
`sentence-transformers`.

## RAG runner

One-time setup (`rag/index.py`):

1. Load all chunks from `ragdemo/corpus.py`.
2. Embed and persist to `rag/index/chroma/`.
3. Build parallel `rag/index/bm25.pkl` over the same chunks.

Per-query flow (`rag/rag.py answer <scenario.json>`):

1. Hybrid retrieval: BM25 top-20 ∪ dense top-20 → dedupe → cross-encoder
   rerank (`ms-marco-MiniLM-L-6-v2`) → top-8.
2. Build prompt: system prompt (tuned for fair-but-strong — citation required,
   refusal on insufficient context) + retrieved chunks + scenario description.
3. Call Claude at temp=0 with tool-use *disabled*; output schema is strict
   JSON: `{exemption, releasable, rationale, cited_authorities[], confidence}`.
4. **Citation-faithfulness check**: every `cited_authorities[i].cite` is
   looked up in the corpus; `excerpt` must be a substring (after whitespace
   normalization). Mismatches flag as *fabricated citation*.

Deliberately out of scope to keep the comparison honest: no ensembling, no
self-critique, no query rewriting, no agentic retry loop.

## LogicPearl runner

Feature schema (17 fields) derived directly from the elements of 5 U.S.C.
§ 552(b); `pearl/feature_dictionary.json` maps each to a human label + `cite`.

`pearl/traces.csv` — ~40–60 reviewed rows. Action column `exemption` with
values `b1`…`b9` and `releasable` (default). Every row carries:

- `source` — citation into the corpus (e.g., `5 U.S.C. § 552(b)(5)` or
  `DOJ FOIA Guide, Exemption 6, p. 312`).
- `note` — one-line human rationale.

Distribution: roughly balanced across the 9 exemptions + clear-releasable +
a few "looks-exempt-but-isn't" cases to exercise edge behavior.

`pearl/traces_review.md` is generated from `traces.csv`: per-row feature
values, label, citation, and the **quoted excerpt** of the cited authority
from `corpus/raw/`. A reviewer can sign off the whole file in one pass. If
anyone edits `traces.csv`, regenerating this file makes the change visible
in git diff.

`pearl/build.sh` wraps `logicpearl build` with the action-column,
default-action, feature-dictionary, gate-id, and output-dir flags. Build
must report **100% training parity**; if not, traces are inconsistent and
must be fixed before shipping.

Runtime (`pearl/pearl.py answer <scenario.json>`):

1. LLM tool-call `extract_features(description)` returns JSON matching the
   feature schema (types and enums enforced by tool schema).
2. Write `features.json`; subprocess
   `logicpearl run pearl/artifact features.json --explain --json`.
3. Parse `{action, reason}`. Call LLM again at temp=0 with system prompt:
   *"explain this deterministic decision in plain English, citing the
   authority from the artifact's reason. Do not add claims the artifact did
   not make."*
4. Return `{exemption, releasable, rationale, cited_authorities (from
   artifact), confidence: "deterministic"}`.

**Architectural rule:** the LLM is a normalizer, not a decider. It cannot
override the artifact's action. It can only decline to speak when feature
extraction is low-confidence (`insufficient_context`). If tool-call JSON
fails schema validation twice, the scenario is marked
`error: feature_extraction_failed` — **we never fabricate a feature vector.**

## Comparison harness

`scenarios/*.json` — 15 scenarios across categories:

- `clear-cut` (~8): one per exemption + one clearly releasable.
- `borderline` (~4): edge cases where RAG may waffle.
- `out-of-distribution` (~2): pearl should refuse.
- `rag-favored` (1): open-ended synthesis ("summarize legislative history of
  Exemption 5"). Pearl must say "not applicable"; RAG should win.

`compare.py --provider anthropic --repeat 5` runs both sides 5× per scenario,
measures correctness vs. `expected`, byte-identical determinism across reruns,
citation faithfulness, latency, tokens. Renders a `rich` transcript to stdout
and writes `transcripts/YYYY-MM-DD-<provider>.md` plus a `run_manifest.json`
containing: git sha of rag-demo, logicpearl CLI version, provider + model,
embedding model, corpus MANIFEST hash, artifact hash, scenarios list. Any
published transcript is reproducible from the manifest.

The three honest headlines the summary table is designed to surface:

1. Correctness is comparable on clear-cut cases.
2. Determinism diverges sharply (pearl 5/5; RAG 1–4/5 on borderline).
3. Citation faithfulness diverges sharply (pearl 5/5 by construction;
   RAG occasionally fabricates plausible-looking cites).
4. On OOD scenarios, pearl refuses and RAG answers confidently but
   unverifiably — viewer decides.
5. On the rag-favored scenario, pearl says "not applicable" and RAG wins.

## Reproducibility

- `corpus/sources.toml` sha256 + `fetch.py` verifies.
- `corpus/snapshot/` makes `make demo` work offline.
- `logicpearl artifact verify pearl/artifact` runs in the demo's sanity check.
- `run_manifest.json` per transcript captures every version.
- Python pinned via `pyproject.toml` + `uv.lock`; bootstrap is `uv sync`.

Happy path:

```bash
make fetch      # corpus/fetch.py
make index      # rag/index.py
make build      # pearl/build.sh
make demo       # compare.py --repeat 5
```

## Error handling — only at real boundaries

- Corpus fetch: HTTP error / sha256 mismatch → point at `sources.toml` and
  snapshot fallback. No silent retry loops.
- LLM call: provider-specific errors surface as one-line hints + the actual
  provider error. No fake fallback answers.
- Feature extraction: schema-failed JSON retries once with the validation error
  echoed; second failure marks the scenario error, never guesses.
- `logicpearl run` subprocess: non-zero exit marks `error: pearl_run_failed`
  with stderr + artifact hash.
- Citation-faithfulness mismatches are reported in the transcript but do not
  block the run — surfacing them is the whole point.

## YAGNI — explicitly out of scope

- No web server, DB (beyond Chroma's on-disk store), auth, or CI config
  beyond a `make demo` smoke test.
- No multi-turn conversation state.
- No agentic scaffolding on the RAG side.
- No plugin authoring on the LogicPearl side; the built CLI is a subprocess
  like any user would use it.

## Fairness guardrails (baked in, not bolted on)

- Same LLM, same temperature (0) both sides.
- Same corpus both sides.
- Strong RAG baseline: hybrid retrieval, cross-encoder rerank, structure-aware
  chunking, citation-required system prompt, top-k=8.
- Include at least one scenario where RAG is supposed to win.
- Measure refusal quality, not just accuracy.
- Citation faithfulness auto-checked for both sides.

## Task references (from brainstorm)

Tasks #1–#6 in the session task list track: explore context (done), clarify
scope (done), propose approaches (done), present + validate design (done),
write design doc (this file), and hand off to writing-plans.
