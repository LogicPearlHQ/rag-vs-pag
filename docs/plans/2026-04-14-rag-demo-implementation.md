# RAG Demo Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers-extended-cc:executing-plans to implement this plan task-by-task.

**Goal:** Build an end-to-end demo at `~/Documents/LogicPearl/rag-demo` that runs the same FOIA scenarios through both a strong RAG baseline and a LogicPearl deterministic artifact, then prints a side-by-side transcript showing correctness, determinism, and citation faithfulness.

**Architecture:** Two runners (`rag/`, `pearl/`) plus shared libs (`ragdemo/`) over a shared federal-law corpus. RAG side: hybrid BM25+dense retrieval → cross-encoder rerank → LLM answer with citation-faithfulness check. LogicPearl side: LLM feature extraction → `logicpearl run` subprocess → LLM explanation that cannot override the artifact. Pluggable LLM provider (Anthropic default; OpenAI and Ollama supported).

**Tech Stack:** Python 3.11+, `uv` for deps, `anthropic`/`openai`/`ollama` SDKs, `chromadb`, `rank_bm25`, `sentence-transformers`, `pypdf`, `httpx`, `rich`, `pytest`. The `logicpearl` CLI 0.1.5 is already on PATH (`/opt/homebrew/bin/logicpearl`).

**Design source:** `docs/plans/2026-04-14-rag-demo-design.md` (approved).

**Scope:** Ship a working demo plus a checked-in sample transcript. Every task ends with a commit.

---

## Global conventions

- Python package name: `ragdemo`. Tests under `tests/`. Runners at `rag/rag.py`, `pearl/pearl.py`, `compare.py`.
- Temperature = 0 for all LLM calls that produce answers.
- JSON schema-enforced LLM output whenever possible (Anthropic tool-use, OpenAI structured output).
- Apply TDD for pure logic (chunking, citation check, scenario loader, trace-review generator, metrics aggregation). For external/LLM-dependent code, write integration tests that use recorded fixtures or lightweight mocks; live LLM smoke tests are `@pytest.mark.live` and skipped in CI by default.
- Commit after every task. Never skip hooks.
- Virtualenv: `uv sync` creates `.venv/`. All commands below assume it is active (`source .venv/bin/activate`) or prefixed with `uv run`.

---

## Task 0: Scaffold the project

**Files:**
- Create: `~/Documents/LogicPearl/rag-demo/pyproject.toml`
- Create: `~/Documents/LogicPearl/rag-demo/.gitignore`
- Create: `~/Documents/LogicPearl/rag-demo/.env.example`
- Create: `~/Documents/LogicPearl/rag-demo/Makefile`
- Create: `~/Documents/LogicPearl/rag-demo/README.md` (stub)
- Create: `~/Documents/LogicPearl/rag-demo/ragdemo/__init__.py`
- Create: `~/Documents/LogicPearl/rag-demo/tests/__init__.py`
- Create: `~/Documents/LogicPearl/rag-demo/tests/test_smoke.py`

**Step 1: Write `pyproject.toml`.**

```toml
[project]
name = "rag-demo"
version = "0.1.0"
description = "Replacing RAG with LogicPearl as the decision layer for an LLM, on real FOIA primary sources."
requires-python = ">=3.11"
dependencies = [
  "anthropic>=0.40",
  "openai>=1.50",
  "ollama>=0.3",
  "chromadb>=0.5",
  "rank-bm25>=0.2",
  "sentence-transformers>=3.0",
  "pypdf>=5.0",
  "httpx>=0.27",
  "rich>=13.7",
  "python-dotenv>=1.0",
  "tomli>=2.0; python_version < '3.11'",
]

[project.optional-dependencies]
dev = [
  "pytest>=8.0",
  "pytest-cov>=5.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["ragdemo"]

[tool.pytest.ini_options]
markers = [
  "live: runs a real LLM or network call; skipped unless --run-live is passed",
]
testpaths = ["tests"]
```

**Step 2: Write `.gitignore`.**

```gitignore
.venv/
__pycache__/
*.pyc
.pytest_cache/
.env
corpus/raw/
pearl/artifact/
rag/index/
transcripts/*.json
!transcripts/.gitkeep
uv.lock
```

**Step 3: Write `.env.example`.**

```dotenv
ANTHROPIC_API_KEY=
OPENAI_API_KEY=
LP_LLM_PROVIDER=anthropic
LP_LLM_MODEL=claude-opus-4-6
LP_EMBEDDING_PROVIDER=openai
LP_EMBEDDING_MODEL=text-embedding-3-small
```

**Step 4: Write `Makefile` skeleton.**

```makefile
.PHONY: install fetch index build demo test clean

install:
	uv sync

fetch:
	uv run python -m corpus.fetch

index:
	uv run python -m rag.index

build:
	bash pearl/build.sh

demo:
	uv run python compare.py --repeat 5

test:
	uv run pytest -q

clean:
	rm -rf corpus/raw pearl/artifact rag/index
```

**Step 5: Write `README.md` stub.**

```markdown
# rag-demo

End-to-end demo showing how LogicPearl can replace a RAG pipeline as the
decision layer an LLM uses. Full design in
`docs/plans/2026-04-14-rag-demo-design.md`.

## Quick start

```bash
uv sync
cp .env.example .env  # fill in ANTHROPIC_API_KEY
make fetch
make index
make build
make demo
```

See `transcripts/` for pre-captured runs.
```

**Step 6: Write smoke test.**

```python
# tests/test_smoke.py
import ragdemo

def test_package_importable():
    assert ragdemo is not None
```

**Step 7: Verify.**

```bash
cd ~/Documents/LogicPearl/rag-demo && uv sync && uv run pytest -q
```
Expected: `1 passed`.

**Step 8: Commit.**

```bash
cd ~/Documents/LogicPearl/rag-demo
git add -A
git commit -m "scaffold: pyproject, Makefile, smoke test"
```

---

## Task 1: Declare the corpus sources

**Files:**
- Create: `corpus/__init__.py`
- Create: `corpus/sources.toml`
- Create: `corpus/ATTRIBUTIONS.md`

**Step 1: Write `corpus/sources.toml`.** Every doc has a `url`, `sha256` (fill after first fetch — start with placeholder `"TBD"`), `kind`, and a `cite_root`. Use pinned URLs; prefer plain text where available.

```toml
# Public domain federal works (statute, CFR) + CourtListener opinions
# redistributed under its terms. See ATTRIBUTIONS.md.

[[documents]]
id = "5_usc_552"
kind = "statute"
url = "https://www.law.cornell.edu/uscode/text/5/552"
sha256 = "TBD"
cite_root = "5 U.S.C. § 552"

[[documents]]
id = "doj_guide_exemption_1"
kind = "doj_guide"
url = "https://www.justice.gov/oip/page/file/1199081/download"  # placeholder; update in Task 3
sha256 = "TBD"
cite_root = "DOJ FOIA Guide, Exemption 1"

# ... repeat for exemptions 2-9 (9 entries)

[[documents]]
id = "28_cfr_16"
kind = "cfr"
url = "https://www.ecfr.gov/current/title-28/chapter-I/part-16"
sha256 = "TBD"
cite_root = "28 C.F.R. Part 16"

# Selected FOIA landmark cases (IDs from CourtListener API)
[[documents]]
id = "nlrb_v_sears_roebuck"
kind = "case"
url = "https://www.courtlistener.com/api/rest/v4/opinions/109241/"
sha256 = "TBD"
cite_root = "NLRB v. Sears, Roebuck & Co., 421 U.S. 132 (1975)"

# ... 9 more case entries
```

**Step 2: Write `corpus/ATTRIBUTIONS.md`** — short page naming sources, licensing (public domain for federal works, CourtListener terms for opinions), and links.

**Step 3: Commit.**

```bash
git add corpus/ && git commit -m "corpus: declare sources.toml + attributions"
```

---

## Task 2: Ship the offline snapshot (statute only)

**Files:**
- Create: `corpus/snapshot/5_usc_552.txt` — plain-text copy of 5 U.S.C. § 552 from Cornell LII, manually verified once.
- Create: `corpus/snapshot/README.md` — why it's here and when to use it.
- Create: `tests/test_corpus_snapshot.py`

**Step 1: Fetch snapshot manually, commit.**

```bash
curl -sSL "https://www.law.cornell.edu/uscode/text/5/552" \
  | python -c "import sys, re; from html.parser import HTMLParser; \
               html = sys.stdin.read(); \
               import html as h; \
               text = re.sub(r'<[^>]+>', '', html); \
               print(h.unescape(text))" \
  > corpus/snapshot/5_usc_552.txt
```
*(Note: the above is only to bootstrap — the real fetcher in Task 3 does this properly. For the snapshot, the human reviewer should sanity-check and possibly trim to just the § 552 section.)*

**Step 2: Write failing test.**

```python
# tests/test_corpus_snapshot.py
from pathlib import Path

SNAPSHOT = Path(__file__).parent.parent / "corpus" / "snapshot" / "5_usc_552.txt"

def test_snapshot_contains_all_nine_exemptions():
    text = SNAPSHOT.read_text()
    for i in range(1, 10):
        assert f"({i})" in text, f"Exemption {i} marker not found in snapshot"

def test_snapshot_contains_exemption_5_language():
    text = SNAPSHOT.read_text().lower()
    assert "inter-agency" in text or "intra-agency" in text
```

**Step 3: Run — expect pass if snapshot is clean; fix snapshot content otherwise.**

```bash
uv run pytest tests/test_corpus_snapshot.py -v
```

**Step 4: Commit.**

```bash
git add corpus/snapshot/ tests/test_corpus_snapshot.py
git commit -m "corpus: add checked-in statute snapshot + verification test"
```

---

## Task 3: Implement `corpus/fetch.py` with sha256 verification

**Files:**
- Create: `corpus/fetch.py`
- Create: `tests/test_corpus_fetch.py`

**Step 1: Write failing test using a local temp server pattern.**

```python
# tests/test_corpus_fetch.py
import hashlib
import http.server
import threading
from pathlib import Path
import pytest
from corpus.fetch import fetch_one, FetchError

@pytest.fixture
def local_server(tmp_path):
    payload = b"hello world\n"
    (tmp_path / "file.txt").write_bytes(payload)
    handler = http.server.SimpleHTTPRequestHandler
    srv = http.server.HTTPServer(("127.0.0.1", 0), handler)
    srv_thread = threading.Thread(target=srv.serve_forever, daemon=True)
    srv_thread.start()
    import os; os.chdir(tmp_path)
    yield f"http://127.0.0.1:{srv.server_address[1]}/file.txt", hashlib.sha256(payload).hexdigest()
    srv.shutdown()

def test_fetch_one_success(tmp_path, local_server):
    url, sha = local_server
    out = tmp_path / "out.txt"
    fetch_one(url, sha, out)
    assert out.read_bytes() == b"hello world\n"

def test_fetch_one_sha_mismatch_raises(tmp_path, local_server):
    url, _ = local_server
    out = tmp_path / "out.txt"
    with pytest.raises(FetchError, match="sha256 mismatch"):
        fetch_one(url, "0" * 64, out)
```

**Step 2: Run — expect import failure.**

```bash
uv run pytest tests/test_corpus_fetch.py -v
```

**Step 3: Implement `corpus/fetch.py`.**

```python
"""Fetches docs listed in corpus/sources.toml into corpus/raw/, verifying sha256."""
from __future__ import annotations
import hashlib
import json
import sys
import tomllib
from pathlib import Path
import httpx

ROOT = Path(__file__).parent
SOURCES = ROOT / "sources.toml"
RAW = ROOT / "raw"
MANIFEST = RAW / "MANIFEST.json"

class FetchError(RuntimeError):
    pass

def fetch_one(url: str, expected_sha: str, out: Path) -> str:
    out.parent.mkdir(parents=True, exist_ok=True)
    with httpx.Client(follow_redirects=True, timeout=60) as c:
        r = c.get(url)
        r.raise_for_status()
        data = r.content
    actual = hashlib.sha256(data).hexdigest()
    if expected_sha != "TBD" and actual != expected_sha:
        raise FetchError(f"sha256 mismatch for {url}: expected {expected_sha}, got {actual}")
    out.write_bytes(data)
    return actual

def main() -> int:
    RAW.mkdir(exist_ok=True)
    with SOURCES.open("rb") as f:
        cfg = tomllib.load(f)
    manifest = {}
    for doc in cfg["documents"]:
        out = RAW / f"{doc['id']}.bin"
        print(f"fetching {doc['id']} <- {doc['url']}")
        try:
            sha = fetch_one(doc["url"], doc["sha256"], out)
        except (httpx.HTTPError, FetchError) as e:
            print(f"  ERROR: {e}", file=sys.stderr)
            if (ROOT / "snapshot" / f"{doc['id']}.txt").exists():
                print(f"  falling back to snapshot")
                out.write_bytes((ROOT / "snapshot" / f"{doc['id']}.txt").read_bytes())
                sha = hashlib.sha256(out.read_bytes()).hexdigest()
            else:
                return 1
        manifest[doc["id"]] = {"sha256": sha, "url": doc["url"], "kind": doc["kind"], "cite_root": doc["cite_root"]}
    MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True))
    print(f"manifest: {MANIFEST}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
```

**Step 4: Run tests; expect pass.**

```bash
uv run pytest tests/test_corpus_fetch.py -v
```

**Step 5: Run the real fetcher; it will record sha256 values.**

```bash
uv run python -m corpus.fetch
```
Expected: `manifest: .../corpus/raw/MANIFEST.json`, per-doc "fetching" lines. Update `corpus/sources.toml` with real sha256s from `MANIFEST.json`.

**Step 6: Commit.**

```bash
git add corpus/fetch.py tests/test_corpus_fetch.py corpus/sources.toml
git commit -m "corpus: fetcher with sha256 verification + snapshot fallback"
```

---

## Task 4: Structure-aware chunking for the statute

**Files:**
- Create: `ragdemo/corpus.py`
- Create: `tests/test_chunking_statute.py`

**Step 1: Write failing test.**

```python
# tests/test_chunking_statute.py
from pathlib import Path
from ragdemo.corpus import chunk_statute, Chunk

SNAPSHOT = Path(__file__).parent.parent / "corpus" / "snapshot" / "5_usc_552.txt"

def test_statute_chunks_one_per_subsection():
    chunks = chunk_statute(SNAPSHOT.read_text(), doc_id="5_usc_552")
    # Every exemption (b)(1) through (b)(9) gets a chunk with metadata
    exemptions = [c for c in chunks if c.metadata.get("exemption") in range(1, 10)]
    assert len({c.metadata["exemption"] for c in exemptions}) == 9

def test_statute_chunk_has_cite_metadata():
    chunks = chunk_statute(SNAPSHOT.read_text(), doc_id="5_usc_552")
    b5 = next(c for c in chunks if c.metadata.get("exemption") == 5)
    assert b5.metadata["cite"] == "5 U.S.C. § 552(b)(5)"
    assert "inter-agency" in b5.text.lower() or "intra-agency" in b5.text.lower()
```

**Step 2: Run — fail.**

**Step 3: Implement in `ragdemo/corpus.py`.**

```python
"""Load + structure-aware chunking of the corpus."""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import Any

@dataclass
class Chunk:
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)

def chunk_statute(text: str, doc_id: str) -> list[Chunk]:
    """Split § 552 into one chunk per numbered subsection under (b)."""
    chunks: list[Chunk] = []
    # Find (b)(N) markers, inclusive. Greedy until next (b)(N+1) or (c).
    # Statute text uses forms like "(b)(1)" "(b)(2)" etc.
    pattern = re.compile(r"\(b\)\((\d)\)(.*?)(?=\(b\)\(\d\)|\(c\)|\Z)", re.S)
    for m in pattern.finditer(text):
        num = int(m.group(1))
        body = m.group(0).strip()
        chunks.append(Chunk(
            text=body,
            metadata={
                "source": doc_id,
                "kind": "statute",
                "cite": f"5 U.S.C. § 552(b)({num})",
                "exemption": num,
            },
        ))
    # Also a single chunk for the whole section header + (a) for context.
    header_match = re.search(r"\(a\).*?(?=\(b\)\(1\))", text, re.S)
    if header_match:
        chunks.insert(0, Chunk(
            text=header_match.group(0).strip(),
            metadata={"source": doc_id, "kind": "statute", "cite": "5 U.S.C. § 552(a)"},
        ))
    return chunks
```

**Step 4: Run — pass.**

```bash
uv run pytest tests/test_chunking_statute.py -v
```

**Step 5: Commit.**

```bash
git add ragdemo/corpus.py tests/test_chunking_statute.py
git commit -m "corpus: structure-aware statute chunking"
```

---

## Task 5: Chunkers for DOJ Guide, CFR, cases + unified `load_corpus()`

**Files:**
- Modify: `ragdemo/corpus.py`
- Create: `tests/test_chunking_other.py`

**Step 1: Write failing tests using small fixture files.**

```python
# tests/test_chunking_other.py
from pathlib import Path
from ragdemo.corpus import chunk_doj_guide_pdf, chunk_cfr, chunk_case, load_corpus

FIX = Path(__file__).parent / "fixtures"

def test_chunk_cfr_splits_by_section():
    text = "§ 16.1 Scope.\nFoo.\n§ 16.2 Definitions.\nBar."
    chunks = chunk_cfr(text, doc_id="28_cfr_16")
    assert len(chunks) == 2
    assert chunks[0].metadata["cite"] == "28 C.F.R. § 16.1"
    assert "Foo" in chunks[0].text

def test_chunk_case_paragraphs():
    text = "Opinion. First paragraph.\n\nSecond paragraph, longer.\n\nThird."
    chunks = chunk_case(text, doc_id="nlrb_v_sears_roebuck", cite_root="NLRB v. Sears")
    assert len(chunks) >= 2
    assert chunks[0].metadata["cite"].startswith("NLRB v. Sears")
```

**Step 2: Implement.** Append to `ragdemo/corpus.py`:

```python
def chunk_cfr(text: str, doc_id: str) -> list[Chunk]:
    chunks: list[Chunk] = []
    pattern = re.compile(r"§\s*16\.(\d+)\s+([^\n]+)(.*?)(?=§\s*16\.\d+|\Z)", re.S)
    for m in pattern.finditer(text):
        num = m.group(1)
        title = m.group(2).strip().rstrip(".")
        body = m.group(0).strip()
        chunks.append(Chunk(
            text=body,
            metadata={
                "source": doc_id,
                "kind": "cfr",
                "cite": f"28 C.F.R. § 16.{num}",
                "title": title,
            },
        ))
    return chunks

def chunk_case(text: str, doc_id: str, cite_root: str) -> list[Chunk]:
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: list[Chunk] = []
    for i, p in enumerate(paragraphs, start=1):
        if len(p) < 40:  # skip case captions and headers
            continue
        chunks.append(Chunk(
            text=p,
            metadata={
                "source": doc_id,
                "kind": "case",
                "cite": f"{cite_root}, para. {i}",
            },
        ))
    return chunks

def chunk_doj_guide_pdf(pdf_path: Path, doc_id: str, cite_root: str) -> list[Chunk]:
    """Chunk DOJ Guide PDF by page, labeled by exemption chapter."""
    from pypdf import PdfReader
    reader = PdfReader(str(pdf_path))
    chunks: list[Chunk] = []
    for i, page in enumerate(reader.pages, start=1):
        txt = (page.extract_text() or "").strip()
        if len(txt) < 100:
            continue
        chunks.append(Chunk(
            text=txt,
            metadata={
                "source": doc_id,
                "kind": "doj_guide",
                "cite": f"{cite_root}, p. {i}",
                "page": i,
            },
        ))
    return chunks

def load_corpus(raw_dir: Path) -> list[Chunk]:
    import json
    manifest = json.loads((raw_dir / "MANIFEST.json").read_text())
    chunks: list[Chunk] = []
    for doc_id, meta in manifest.items():
        path = raw_dir / f"{doc_id}.bin"
        kind = meta["kind"]
        if kind == "statute":
            chunks.extend(chunk_statute(path.read_text(errors="ignore"), doc_id))
        elif kind == "cfr":
            chunks.extend(chunk_cfr(path.read_text(errors="ignore"), doc_id))
        elif kind == "case":
            chunks.extend(chunk_case(path.read_text(errors="ignore"), doc_id, meta["cite_root"]))
        elif kind == "doj_guide":
            chunks.extend(chunk_doj_guide_pdf(path, doc_id, meta["cite_root"]))
    return chunks
```

**Step 3: Run — pass.**

```bash
uv run pytest tests/test_chunking_other.py -v
```

**Step 4: Commit.**

```bash
git add ragdemo/corpus.py tests/test_chunking_other.py
git commit -m "corpus: CFR/case/DOJ Guide chunkers + load_corpus"
```

---

## Task 6: Scenario loader (`ragdemo/scenarios.py`)

**Files:**
- Create: `ragdemo/scenarios.py`
- Create: `tests/test_scenarios.py`
- Create: `tests/fixtures/scenarios/ok.json`
- Create: `tests/fixtures/scenarios/bad.json`

**Step 1: Write failing test.**

```python
# tests/test_scenarios.py
from pathlib import Path
import pytest
from ragdemo.scenarios import load_scenario, Scenario

FIX = Path(__file__).parent / "fixtures" / "scenarios"

def test_load_valid_scenario():
    s = load_scenario(FIX / "ok.json")
    assert s.id == "test01"
    assert s.expected.exemption == "b5"
    assert s.category == "clear-cut"

def test_bad_scenario_raises():
    with pytest.raises(ValueError):
        load_scenario(FIX / "bad.json")
```

**Step 2: Fixtures.**

```json
// tests/fixtures/scenarios/ok.json
{
  "id": "test01",
  "description": "A pre-decisional draft memo.",
  "expected": {"exemption": "b5", "releasable": false,
               "rationale_keywords": ["pre-decisional"],
               "expected_authority": "5 U.S.C. § 552(b)(5)"},
  "category": "clear-cut"
}
```

```json
// tests/fixtures/scenarios/bad.json
{"id": "test02"}
```

**Step 3: Implement.**

```python
# ragdemo/scenarios.py
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import json
from typing import Literal

Category = Literal["clear-cut", "borderline", "out-of-distribution", "rag-favored"]

@dataclass
class Expected:
    exemption: str | None  # "b1"..."b9" or "releasable" or None (rag-favored)
    releasable: bool
    rationale_keywords: list[str]
    expected_authority: str | None

@dataclass
class Scenario:
    id: str
    description: str
    expected: Expected
    category: Category

def load_scenario(path: Path) -> Scenario:
    data = json.loads(Path(path).read_text())
    required = {"id", "description", "expected", "category"}
    if not required.issubset(data):
        raise ValueError(f"scenario missing keys: {required - set(data)}")
    e = data["expected"]
    return Scenario(
        id=data["id"],
        description=data["description"],
        expected=Expected(
            exemption=e.get("exemption"),
            releasable=e.get("releasable", True),
            rationale_keywords=e.get("rationale_keywords", []),
            expected_authority=e.get("expected_authority"),
        ),
        category=data["category"],
    )

def load_scenarios(dir_: Path) -> list[Scenario]:
    return sorted((load_scenario(p) for p in Path(dir_).glob("*.json")), key=lambda s: s.id)
```

**Step 4: Run — pass. Commit.**

```bash
uv run pytest tests/test_scenarios.py -v
git add ragdemo/scenarios.py tests/test_scenarios.py tests/fixtures/
git commit -m "scenarios: loader + schema"
```

---

## Task 7: LLM interface + Anthropic implementation (with prompt caching)

**Files:**
- Create: `ragdemo/llm.py`
- Create: `ragdemo/llm_anthropic.py`
- Create: `tests/test_llm_interface.py`

**Step 1: Write the interface + a fake implementation test.**

```python
# tests/test_llm_interface.py
from ragdemo.llm import LLM, LLMConfig, make_llm

def test_factory_returns_fake_for_env():
    llm = make_llm(LLMConfig(provider="fake", model="none"))
    out = llm.chat_json(system="sys", user="hi", schema={"type": "object"}, temperature=0)
    assert isinstance(out, dict)
```

**Step 2: Implement `ragdemo/llm.py`.**

```python
# ragdemo/llm.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

@dataclass
class LLMConfig:
    provider: str   # "anthropic" | "openai" | "ollama" | "fake"
    model: str
    cache_system: bool = True

@runtime_checkable
class LLM(Protocol):
    def chat_json(self, *, system: str, user: str, schema: dict, temperature: float = 0.0) -> dict: ...
    def chat_tool(self, *, system: str, user: str, tool: dict, temperature: float = 0.0) -> dict: ...

class FakeLLM:
    def __init__(self, cfg: LLMConfig): self.cfg = cfg
    def chat_json(self, *, system, user, schema, temperature=0.0) -> dict:
        return {"_fake": True, "system": system, "user": user}
    def chat_tool(self, *, system, user, tool, temperature=0.0) -> dict:
        return {"_fake": True, "tool": tool["name"]}

def make_llm(cfg: LLMConfig) -> LLM:
    if cfg.provider == "fake":
        return FakeLLM(cfg)
    if cfg.provider == "anthropic":
        from .llm_anthropic import AnthropicLLM
        return AnthropicLLM(cfg)
    if cfg.provider == "openai":
        from .llm_openai import OpenAILLM
        return OpenAILLM(cfg)
    if cfg.provider == "ollama":
        from .llm_ollama import OllamaLLM
        return OllamaLLM(cfg)
    raise ValueError(f"unknown provider: {cfg.provider}")
```

**Step 3: Implement `ragdemo/llm_anthropic.py`** — use Messages API, prompt caching on system prompt, tool-use for schema-enforced JSON.

```python
# ragdemo/llm_anthropic.py
from __future__ import annotations
import json, os
from anthropic import Anthropic
from .llm import LLMConfig

class AnthropicLLM:
    def __init__(self, cfg: LLMConfig):
        self.cfg = cfg
        self.client = Anthropic()  # reads ANTHROPIC_API_KEY

    def _system_block(self, system: str) -> list[dict]:
        block = {"type": "text", "text": system}
        if self.cfg.cache_system:
            block["cache_control"] = {"type": "ephemeral"}
        return [block]

    def chat_json(self, *, system: str, user: str, schema: dict, temperature: float = 0.0) -> dict:
        # Use tool-use to enforce JSON schema. Define a single tool and force its use.
        tool = {"name": "emit", "description": "Return the answer.", "input_schema": schema}
        resp = self.client.messages.create(
            model=self.cfg.model,
            max_tokens=4096,
            temperature=temperature,
            system=self._system_block(system),
            tools=[tool],
            tool_choice={"type": "tool", "name": "emit"},
            messages=[{"role": "user", "content": user}],
        )
        for block in resp.content:
            if block.type == "tool_use" and block.name == "emit":
                return block.input
        raise RuntimeError("no tool_use in response")

    def chat_tool(self, *, system: str, user: str, tool: dict, temperature: float = 0.0) -> dict:
        resp = self.client.messages.create(
            model=self.cfg.model,
            max_tokens=4096,
            temperature=temperature,
            system=self._system_block(system),
            tools=[tool],
            tool_choice={"type": "tool", "name": tool["name"]},
            messages=[{"role": "user", "content": user}],
        )
        for block in resp.content:
            if block.type == "tool_use" and block.name == tool["name"]:
                return block.input
        raise RuntimeError("no tool_use in response")
```

**Step 4: Live smoke test (optional).**

```python
# tests/test_llm_anthropic_live.py
import os, pytest
pytestmark = pytest.mark.live
from ragdemo.llm import make_llm, LLMConfig

@pytest.mark.skipif(not os.getenv("ANTHROPIC_API_KEY"), reason="no key")
def test_anthropic_json_roundtrip():
    llm = make_llm(LLMConfig(provider="anthropic", model="claude-opus-4-6"))
    out = llm.chat_json(
        system="You return JSON.",
        user="Return {\"ok\": true}",
        schema={"type": "object", "properties": {"ok": {"type": "boolean"}}, "required": ["ok"]},
    )
    assert out["ok"] is True
```

**Step 5: Run unit tests — pass. Commit.**

```bash
uv run pytest tests/test_llm_interface.py -v
git add ragdemo/llm.py ragdemo/llm_anthropic.py tests/test_llm_interface.py tests/test_llm_anthropic_live.py
git commit -m "llm: interface + Anthropic impl with prompt caching"
```

**Skill reference:** for prompt caching and tool schema details see `claude-api` skill.

---

## Task 8: OpenAI LLM implementation

**Files:**
- Create: `ragdemo/llm_openai.py`
- Create: `tests/test_llm_openai_live.py`

**Step 1: Implement using Responses API with structured output.**

```python
# ragdemo/llm_openai.py
from __future__ import annotations
import json
from openai import OpenAI
from .llm import LLMConfig

class OpenAILLM:
    def __init__(self, cfg: LLMConfig):
        self.cfg = cfg
        self.client = OpenAI()

    def chat_json(self, *, system, user, schema, temperature=0.0) -> dict:
        resp = self.client.chat.completions.create(
            model=self.cfg.model,
            temperature=temperature,
            response_format={
                "type": "json_schema",
                "json_schema": {"name": "answer", "schema": schema, "strict": True},
            },
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return json.loads(resp.choices[0].message.content)

    def chat_tool(self, *, system, user, tool, temperature=0.0) -> dict:
        resp = self.client.chat.completions.create(
            model=self.cfg.model,
            temperature=temperature,
            tools=[{"type": "function", "function": {
                "name": tool["name"], "description": tool.get("description", ""),
                "parameters": tool["input_schema"], "strict": True,
            }}],
            tool_choice={"type": "function", "function": {"name": tool["name"]}},
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        call = resp.choices[0].message.tool_calls[0]
        return json.loads(call.function.arguments)
```

**Step 2: Live smoke test, parallel to the Anthropic one.**

**Step 3: Commit.**

```bash
git add ragdemo/llm_openai.py tests/test_llm_openai_live.py
git commit -m "llm: OpenAI impl (Responses API, structured output)"
```

---

## Task 9: Ollama LLM implementation

**Files:**
- Create: `ragdemo/llm_ollama.py`
- Create: `tests/test_llm_ollama_live.py`

**Step 1: Implement using `ollama` Python client.** Ollama supports tool-use since 0.3; use JSON-mode fallback if tool-use unavailable on the target model.

```python
# ragdemo/llm_ollama.py
from __future__ import annotations
import json
import ollama
from .llm import LLMConfig

class OllamaLLM:
    def __init__(self, cfg: LLMConfig): self.cfg = cfg

    def chat_json(self, *, system, user, schema, temperature=0.0) -> dict:
        resp = ollama.chat(
            model=self.cfg.model,
            format="json",
            options={"temperature": temperature},
            messages=[
                {"role": "system", "content": f"{system}\n\nRespond ONLY with JSON matching this schema: {json.dumps(schema)}"},
                {"role": "user", "content": user},
            ],
        )
        return json.loads(resp["message"]["content"])

    def chat_tool(self, *, system, user, tool, temperature=0.0) -> dict:
        # Use format=json + instruction; treat tool input_schema as the target JSON.
        schema = tool["input_schema"]
        return self.chat_json(system=f"{system}\n\nReturn arguments for tool {tool['name']}.", user=user, schema=schema, temperature=temperature)
```

**Step 2: Live smoke test.**

**Step 3: Commit.**

```bash
git add ragdemo/llm_ollama.py tests/test_llm_ollama_live.py
git commit -m "llm: Ollama impl (fully offline path)"
```

---

## Task 10: RAG indexing (Chroma + BM25)

**Files:**
- Create: `rag/__init__.py`
- Create: `rag/index.py`
- Create: `tests/test_rag_index.py`

**Step 1: Test in-memory indexing on a tiny chunk list.**

```python
# tests/test_rag_index.py
from ragdemo.corpus import Chunk
from rag.index import build_bm25

def test_bm25_ranks_keyword_match_first():
    chunks = [
        Chunk("pre-decisional deliberative process privilege", {"cite": "b5"}),
        Chunk("classified national security information", {"cite": "b1"}),
    ]
    bm25, ids = build_bm25(chunks)
    scores = bm25.get_scores("deliberative process".split())
    assert scores[0] > scores[1]
```

**Step 2: Implement `rag/index.py`.**

```python
# rag/index.py
from __future__ import annotations
from pathlib import Path
import os, pickle
from rank_bm25 import BM25Okapi
from ragdemo.corpus import Chunk, load_corpus

ROOT = Path(__file__).parent
INDEX = ROOT / "index"
BM25_PATH = INDEX / "bm25.pkl"
CHROMA_DIR = INDEX / "chroma"

def tokenize(text: str) -> list[str]:
    return [t for t in text.lower().split() if len(t) > 1]

def build_bm25(chunks: list[Chunk]):
    tokens = [tokenize(c.text) for c in chunks]
    return BM25Okapi(tokens), [c.metadata.get("cite", f"chunk_{i}") for i, c in enumerate(chunks)]

def build_chroma(chunks: list[Chunk]):
    import chromadb
    from chromadb.utils import embedding_functions
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    ef_name = os.environ.get("LP_EMBEDDING_PROVIDER", "openai")
    if ef_name == "openai":
        ef = embedding_functions.OpenAIEmbeddingFunction(
            api_key=os.environ["OPENAI_API_KEY"],
            model_name=os.environ.get("LP_EMBEDDING_MODEL", "text-embedding-3-small"),
        )
    else:
        ef = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=os.environ.get("LP_EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")
        )
    col = client.get_or_create_collection("foia", embedding_function=ef)
    col.add(
        ids=[f"c{i}" for i in range(len(chunks))],
        documents=[c.text for c in chunks],
        metadatas=[c.metadata for c in chunks],
    )
    return col

def main() -> int:
    raw = Path(__file__).parent.parent / "corpus" / "raw"
    chunks = load_corpus(raw)
    INDEX.mkdir(exist_ok=True)
    print(f"chunks: {len(chunks)}")
    bm25, ids = build_bm25(chunks)
    with BM25_PATH.open("wb") as f:
        pickle.dump({"bm25": bm25, "chunks": chunks}, f)
    print(f"bm25 written: {BM25_PATH}")
    build_chroma(chunks)
    print(f"chroma written: {CHROMA_DIR}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
```

**Step 3: Run tests; commit.**

```bash
uv run pytest tests/test_rag_index.py -v
git add rag/__init__.py rag/index.py tests/test_rag_index.py
git commit -m "rag: chroma + bm25 index builder"
```

---

## Task 11: RAG hybrid retrieval + rerank

**Files:**
- Create: `rag/retrieve.py`
- Create: `tests/test_rag_retrieve.py`

**Step 1: Test hybrid union + dedup on fake scores.**

```python
# tests/test_rag_retrieve.py
from rag.retrieve import merge_hybrid

def test_merge_dedup_and_preserves_best_score():
    bm25 = [("a", 5.0), ("b", 3.0), ("c", 1.0)]
    dense = [("b", 0.9), ("d", 0.8)]
    merged = merge_hybrid(bm25, dense)
    ids = [x[0] for x in merged]
    assert "a" in ids and "b" in ids and "d" in ids
    assert len(ids) == len(set(ids))
```

**Step 2: Implement.**

```python
# rag/retrieve.py
from __future__ import annotations
from pathlib import Path
import os, pickle
from ragdemo.corpus import Chunk
from .index import BM25_PATH, CHROMA_DIR, tokenize

def merge_hybrid(bm25_hits: list[tuple[str, float]], dense_hits: list[tuple[str, float]]) -> list[tuple[str, float]]:
    # Normalize each list to [0,1] and take union; sum scores for items in both.
    def norm(hits):
        if not hits: return {}
        m = max(h[1] for h in hits) or 1.0
        return {h[0]: h[1]/m for h in hits}
    a, b = norm(bm25_hits), norm(dense_hits)
    combined = {k: a.get(k, 0) + b.get(k, 0) for k in set(a) | set(b)}
    return sorted(combined.items(), key=lambda x: -x[1])

def retrieve(query: str, top_k: int = 8) -> list[Chunk]:
    with BM25_PATH.open("rb") as f:
        d = pickle.load(f)
    bm25, chunks = d["bm25"], d["chunks"]
    scores = bm25.get_scores(tokenize(query))
    bm25_top = sorted(((f"c{i}", s) for i, s in enumerate(scores)), key=lambda x: -x[1])[:20]

    import chromadb
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    col = client.get_collection("foia")
    res = col.query(query_texts=[query], n_results=20)
    # Chroma returns distances (cosine); convert to score 1 - dist
    dense_top = [(id_, 1.0 - dist) for id_, dist in zip(res["ids"][0], res["distances"][0])]

    merged = merge_hybrid(bm25_top, dense_top)[:30]

    # Rerank with a cross-encoder
    from sentence_transformers import CrossEncoder
    ce = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
    id_to_chunk = {f"c{i}": c for i, c in enumerate(chunks)}
    candidates = [id_to_chunk[id_] for id_, _ in merged if id_ in id_to_chunk]
    if not candidates:
        return []
    pairs = [[query, c.text] for c in candidates]
    ce_scores = ce.predict(pairs)
    ranked = sorted(zip(candidates, ce_scores), key=lambda x: -x[1])[:top_k]
    return [c for c, _ in ranked]
```

**Step 3: Run + commit.**

```bash
uv run pytest tests/test_rag_retrieve.py -v
git add rag/retrieve.py tests/test_rag_retrieve.py
git commit -m "rag: hybrid retrieval + cross-encoder rerank"
```

---

## Task 12: RAG runner + citation-faithfulness check

**Files:**
- Create: `rag/rag.py`
- Create: `rag/README.md`
- Create: `tests/test_rag_citation_check.py`

**Step 1: Test citation check in isolation.**

```python
# tests/test_rag_citation_check.py
from ragdemo.corpus import Chunk
from rag.rag import check_citation

def test_check_citation_substring_match():
    chunk = Chunk("The deliberative process privilege protects predecisional opinions.",
                  {"cite": "5 U.S.C. § 552(b)(5)"})
    assert check_citation("5 U.S.C. § 552(b)(5)", "deliberative process privilege", [chunk])

def test_check_citation_mismatch():
    chunk = Chunk("Classified under Executive Order.", {"cite": "5 U.S.C. § 552(b)(1)"})
    assert not check_citation("5 U.S.C. § 552(b)(5)", "deliberative process", [chunk])
```

**Step 2: Implement `rag/rag.py`.**

```python
# rag/rag.py
from __future__ import annotations
import argparse, json, os, sys, time
from pathlib import Path
from ragdemo.corpus import Chunk, load_corpus
from ragdemo.llm import LLMConfig, make_llm
from ragdemo.scenarios import load_scenario
from .retrieve import retrieve

ANSWER_SCHEMA = {
    "type": "object",
    "properties": {
        "exemption": {"type": ["string", "null"], "enum": ["b1","b2","b3","b4","b5","b6","b7","b8","b9","releasable","insufficient_context", None]},
        "releasable": {"type": "boolean"},
        "rationale": {"type": "string"},
        "cited_authorities": {"type": "array", "items": {
            "type": "object",
            "properties": {"cite": {"type": "string"}, "excerpt": {"type": "string"}},
            "required": ["cite", "excerpt"],
        }},
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
    },
    "required": ["exemption", "releasable", "rationale", "cited_authorities", "confidence"],
}

SYSTEM_PROMPT = """You are a FOIA analyst. Given the retrieved statutory, regulatory, and case excerpts below, determine whether the described record is exempt under 5 U.S.C. § 552(b), and under which subsection (b1 through b9), or whether it is releasable.

You MUST cite the specific subsection or page number present in the retrieved excerpts. Every entry in cited_authorities MUST include a verbatim excerpt from the retrieved text.

If the retrieved context does not clearly support a confident answer, return exemption="insufficient_context" with confidence="low". Do not guess.
"""

def check_citation(cite: str, excerpt: str, chunks: list[Chunk]) -> bool:
    norm = lambda s: " ".join(s.split()).lower()
    target = norm(excerpt)
    for c in chunks:
        if cite.lower() in c.metadata.get("cite", "").lower() and target in norm(c.text):
            return True
    return False

def answer(scenario_path: Path, llm_cfg: LLMConfig) -> dict:
    s = load_scenario(scenario_path)
    chunks = retrieve(s.description, top_k=8)
    blob = "\n\n".join(f"[{c.metadata['cite']}]\n{c.text}" for c in chunks)
    llm = make_llm(llm_cfg)
    user = f"RECORD DESCRIPTION:\n{s.description}\n\nRETRIEVED EXCERPTS:\n{blob}"
    t0 = time.time()
    result = llm.chat_json(system=SYSTEM_PROMPT, user=user, schema=ANSWER_SCHEMA, temperature=0.0)
    result["_latency_s"] = round(time.time() - t0, 3)
    result["_retrieved"] = [c.metadata.get("cite") for c in chunks]
    result["_citation_faithfulness"] = [
        {"cite": a["cite"], "ok": check_citation(a["cite"], a["excerpt"], chunks)}
        for a in result.get("cited_authorities", [])
    ]
    return result

def main():
    p = argparse.ArgumentParser()
    p.add_argument("scenario", type=Path)
    p.add_argument("--provider", default=os.environ.get("LP_LLM_PROVIDER", "anthropic"))
    p.add_argument("--model", default=os.environ.get("LP_LLM_MODEL", "claude-opus-4-6"))
    args = p.parse_args()
    cfg = LLMConfig(provider=args.provider, model=args.model)
    print(json.dumps(answer(args.scenario, cfg), indent=2))

if __name__ == "__main__":
    main()
```

**Step 3: Run tests, commit.**

```bash
uv run pytest tests/test_rag_citation_check.py -v
git add rag/rag.py rag/README.md tests/test_rag_citation_check.py
git commit -m "rag: runner + citation-faithfulness check"
```

---

## Task 13: Pearl feature dictionary

**Files:**
- Create: `pearl/__init__.py`
- Create: `pearl/feature_dictionary.json`
- Create: `tests/test_feature_dictionary.py`

**Step 1: Write feature dictionary.**

```json
{
  "classified_under_executive_order": {"label": "Classified under Executive Order", "cite": "5 U.S.C. § 552(b)(1)"},
  "classification_still_in_force": {"label": "Classification still in force", "cite": "5 U.S.C. § 552(b)(1)"},
  "purely_internal_personnel_rule": {"label": "Purely internal personnel rule or practice", "cite": "5 U.S.C. § 552(b)(2)"},
  "exempt_by_other_statute": {"label": "Specifically exempted by another statute", "cite": "5 U.S.C. § 552(b)(3)"},
  "trade_secret_or_commercial_confidential": {"label": "Trade secret or confidential commercial info", "cite": "5 U.S.C. § 552(b)(4)"},
  "commercial_info_voluntarily_submitted": {"label": "Commercial info voluntarily submitted", "cite": "5 U.S.C. § 552(b)(4)"},
  "inter_or_intra_agency_memo": {"label": "Inter-agency or intra-agency memo", "cite": "5 U.S.C. § 552(b)(5)"},
  "pre_decisional_deliberative": {"label": "Pre-decisional and deliberative", "cite": "5 U.S.C. § 552(b)(5)"},
  "attorney_work_product_or_privileged": {"label": "Attorney work product or privileged communication", "cite": "5 U.S.C. § 552(b)(5)"},
  "personnel_medical_or_similar_file": {"label": "Personnel, medical, or similar file", "cite": "5 U.S.C. § 552(b)(6)"},
  "unwarranted_privacy_invasion": {"label": "Unwarranted invasion of personal privacy", "cite": "5 U.S.C. § 552(b)(6)"},
  "law_enforcement_record": {"label": "Compiled for law enforcement purposes", "cite": "5 U.S.C. § 552(b)(7)"},
  "law_enforcement_harm_proceedings": {"label": "Could reasonably be expected to interfere with proceedings", "cite": "5 U.S.C. § 552(b)(7)(A)"},
  "law_enforcement_harm_privacy": {"label": "Could reasonably be expected to invade privacy", "cite": "5 U.S.C. § 552(b)(7)(C)"},
  "law_enforcement_harm_source": {"label": "Could reasonably be expected to disclose a confidential source", "cite": "5 U.S.C. § 552(b)(7)(D)"},
  "law_enforcement_harm_techniques": {"label": "Would disclose techniques and procedures", "cite": "5 U.S.C. § 552(b)(7)(E)"},
  "law_enforcement_harm_life_safety": {"label": "Could reasonably be expected to endanger life or safety", "cite": "5 U.S.C. § 552(b)(7)(F)"},
  "financial_institution_examination_report": {"label": "Financial institution examination report", "cite": "5 U.S.C. § 552(b)(8)"},
  "geological_well_data": {"label": "Geological and geophysical information re: wells", "cite": "5 U.S.C. § 552(b)(9)"},
  "record_is_otherwise_public": {"label": "Record is already in the public domain", "cite": "DOJ FOIA Guide, Procedural Requirements"}
}
```

**Step 2: Write a validation test.**

```python
# tests/test_feature_dictionary.py
import json
from pathlib import Path

FD = Path("pearl/feature_dictionary.json")

def test_every_feature_has_label_and_cite():
    data = json.loads(FD.read_text())
    for k, v in data.items():
        assert "label" in v and "cite" in v, k

def test_covers_all_nine_exemptions():
    data = json.loads(FD.read_text())
    cites = " ".join(v["cite"] for v in data.values())
    for n in range(1, 10):
        assert f"(b)({n})" in cites
```

**Step 3: Run + commit.**

```bash
uv run pytest tests/test_feature_dictionary.py -v
git add pearl/__init__.py pearl/feature_dictionary.json tests/test_feature_dictionary.py
git commit -m "pearl: feature dictionary anchored to § 552(b)(1-9)"
```

---

## Task 14: First trace set (~25 rows) + `traces_review.md` generator

**Files:**
- Create: `pearl/traces.csv`
- Create: `pearl/generate_review.py`
- Create: `pearl/traces_review.md` (generated output checked in)
- Create: `tests/test_traces_schema.py`

**Step 1: Write `pearl/traces.csv` with ~25 statute-literal rows.** Columns: every feature name + `exemption` (label) + `source` + `note`. One row per feature dictionary key = one exemplar per path. Example:

```csv
classified_under_executive_order,classification_still_in_force,purely_internal_personnel_rule,exempt_by_other_statute,trade_secret_or_commercial_confidential,commercial_info_voluntarily_submitted,inter_or_intra_agency_memo,pre_decisional_deliberative,attorney_work_product_or_privileged,personnel_medical_or_similar_file,unwarranted_privacy_invasion,law_enforcement_record,law_enforcement_harm_proceedings,law_enforcement_harm_privacy,law_enforcement_harm_source,law_enforcement_harm_techniques,law_enforcement_harm_life_safety,financial_institution_examination_report,geological_well_data,record_is_otherwise_public,exemption,source,note
true,true,false,false,false,false,false,false,false,false,false,false,false,false,false,false,false,false,false,false,b1,"5 U.S.C. § 552(b)(1)","Classified TOP SECRET under EO 13526, still in force"
false,false,false,false,false,false,true,true,false,false,false,false,false,false,false,false,false,false,false,false,b5,"5 U.S.C. § 552(b)(5)","Pre-decisional intra-agency draft"
false,false,false,false,false,false,false,false,false,true,true,false,false,false,false,false,false,false,false,false,b6,"5 U.S.C. § 552(b)(6)","Personnel file; invasion of privacy"
false,false,false,false,false,false,false,false,false,true,false,false,false,false,false,false,false,false,false,true,releasable,"DOJ FOIA Guide, Procedural Requirements","Personnel info already public; no privacy invasion"
```

Continue for all 9 exemptions + several `releasable` rows + 3–4 "looks exempt but isn't" rows (e.g., classified but declassified → releasable).

**Step 2: Write `pearl/generate_review.py` that reads traces.csv + feature_dictionary.json + corpus/raw/ and emits `traces_review.md` with per-row rendering.**

```python
# pearl/generate_review.py
from __future__ import annotations
import csv, json
from pathlib import Path

ROOT = Path(__file__).parent
PROJECT = ROOT.parent
FD = json.loads((ROOT / "feature_dictionary.json").read_text())
TRACES = ROOT / "traces.csv"
REVIEW = ROOT / "traces_review.md"

def main() -> int:
    rows = list(csv.DictReader(TRACES.open()))
    out = ["# Traces Review", "",
           f"Source: `pearl/traces.csv` ({len(rows)} rows). Regenerate with `python -m pearl.generate_review`.", ""]
    for i, r in enumerate(rows, start=1):
        out.append(f"## Row {i}: label = `{r['exemption']}`")
        out.append(f"- **Source**: {r['source']}")
        out.append(f"- **Note**: {r['note']}")
        out.append("- **Features TRUE:**")
        for k, v in r.items():
            if k in FD and v.strip().lower() == "true":
                out.append(f"  - `{k}` — {FD[k]['label']} ({FD[k]['cite']})")
        out.append("")
    REVIEW.write_text("\n".join(out))
    print(f"wrote {REVIEW}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
```

**Step 3: Run generator; commit.**

```bash
cd ~/Documents/LogicPearl/rag-demo && uv run python -m pearl.generate_review
git add pearl/traces.csv pearl/generate_review.py pearl/traces_review.md tests/test_traces_schema.py
git commit -m "pearl: first trace set (~25 rows) + review generator"
```

**Step 4: Write schema test.**

```python
# tests/test_traces_schema.py
import csv, json
from pathlib import Path

FD = json.loads(Path("pearl/feature_dictionary.json").read_text())

def test_every_column_is_known_or_meta():
    meta = {"exemption", "source", "note"}
    with open("pearl/traces.csv") as f:
        headers = next(csv.reader(f))
    for h in headers:
        assert h in meta or h in FD, f"unknown column: {h}"

def test_labels_in_expected_set():
    allowed = {f"b{i}" for i in range(1, 10)} | {"releasable"}
    with open("pearl/traces.csv") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        assert r["exemption"] in allowed, r
```

**Step 5: Run; commit.**

```bash
uv run pytest tests/test_traces_schema.py -v
git add tests/test_traces_schema.py
git commit -m "pearl: traces schema tests"
```

---

## Task 15: Expand trace set to ~40–60 rows and regenerate

**Files:**
- Modify: `pearl/traces.csv`
- Modify: `pearl/traces_review.md`

**Step 1: Add ~25 more rows covering:** 2–3 clean exemplars per exemption (varied features), 3–5 ambiguous cases (e.g., law enforcement techniques that are publicly known → releasable), cases involving 2 TRUE exemption features to force rule priority, and a handful where only `record_is_otherwise_public = true` → `releasable`.

**Step 2: Regenerate.**

```bash
uv run python -m pearl.generate_review
```

**Step 3: Run schema tests again.**

```bash
uv run pytest tests/test_traces_schema.py -v
```

**Step 4: Commit.**

```bash
git add pearl/traces.csv pearl/traces_review.md
git commit -m "pearl: expand trace set to ~50 rows, cover all exemptions + edge cases"
```

---

## Task 16: Build the pearl artifact + verify 100% training parity

**Files:**
- Create: `pearl/build.sh`
- Create: `tests/test_pearl_build.py`

**Step 1: Write build script.**

```bash
#!/usr/bin/env bash
# pearl/build.sh
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ARTIFACT="$HERE/artifact"
rm -rf "$ARTIFACT"
logicpearl build "$HERE/traces.csv" \
  --action-column exemption \
  --default-action releasable \
  --gate-id foia_exemptions \
  --feature-dictionary "$HERE/feature_dictionary.json" \
  --output-dir "$ARTIFACT"
logicpearl inspect "$ARTIFACT"
echo "---"
logicpearl artifact verify "$ARTIFACT"
```

Make executable: `chmod +x pearl/build.sh`.

**Step 2: Run it.**

```bash
bash pearl/build.sh
```
Expected: build succeeds, inspect prints "Training parity 100.0%" (or flag non-100% as a trace inconsistency to fix).

**Step 3: Write parity verification test.**

```python
# tests/test_pearl_build.py
import json
import subprocess
from pathlib import Path
import pytest

ART = Path("pearl/artifact")

@pytest.mark.skipif(not ART.exists(), reason="artifact not built")
def test_training_parity_is_100():
    out = subprocess.run(
        ["logicpearl", "inspect", str(ART), "--json"],
        capture_output=True, text=True, check=True,
    ).stdout
    data = json.loads(out)
    # Training parity field name may vary; check both top-level and nested.
    parity = data.get("training_parity") or data.get("build", {}).get("training_parity")
    assert parity == 1.0 or parity == "100.0%", f"parity={parity}; inspect output follows:\n{out}"

def test_artifact_verify_ok():
    subprocess.run(["logicpearl", "artifact", "verify", str(ART)], check=True)
```

**Step 4: Run test; commit.**

```bash
uv run pytest tests/test_pearl_build.py -v
git add pearl/build.sh tests/test_pearl_build.py
git commit -m "pearl: build script + training parity test"
```

---

## Task 17: Pearl feature-extraction tool call

**Files:**
- Create: `pearl/pearl.py` (first half — extraction)
- Create: `tests/test_pearl_extraction.py`

**Step 1: Derive the tool schema from `feature_dictionary.json`.**

```python
# pearl/pearl.py (partial, Task 17 extent)
from __future__ import annotations
import json, os, subprocess, tempfile, time
from pathlib import Path
from ragdemo.llm import LLMConfig, make_llm
from ragdemo.scenarios import load_scenario

ROOT = Path(__file__).parent
FD = json.loads((ROOT / "feature_dictionary.json").read_text())
ARTIFACT = ROOT / "artifact"

def build_extract_tool() -> dict:
    props = {k: {"type": "boolean", "description": v["label"]} for k, v in FD.items()}
    return {
        "name": "extract_features",
        "description": "Extract FOIA exemption features from the record description. Set a feature TRUE only if the description clearly supports it.",
        "input_schema": {"type": "object", "properties": props, "required": list(FD.keys()), "additionalProperties": False},
    }

EXTRACT_SYSTEM = """You are a FOIA analyst. Given a record description, decide which of the listed features are TRUE based strictly on what the description states. Do not assume facts not present. If the description is ambiguous for a feature, set it to FALSE."""
```

**Step 2: Test via FakeLLM.**

```python
# tests/test_pearl_extraction.py
from pearl.pearl import build_extract_tool

def test_extract_tool_schema_covers_all_features():
    tool = build_extract_tool()
    assert tool["input_schema"]["type"] == "object"
    assert len(tool["input_schema"]["properties"]) >= 18
    for v in tool["input_schema"]["properties"].values():
        assert v["type"] == "boolean"
```

**Step 3: Run; commit.**

```bash
uv run pytest tests/test_pearl_extraction.py -v
git add pearl/pearl.py tests/test_pearl_extraction.py
git commit -m "pearl: feature-extraction tool schema"
```

---

## Task 18: Pearl runner — subprocess + explain + refusal

**Files:**
- Modify: `pearl/pearl.py`
- Create: `tests/test_pearl_subprocess.py`

**Step 1: Complete `pearl/pearl.py`.**

```python
# pearl/pearl.py (add below Task 17 code)
EXPLAIN_SYSTEM = """You are explaining a deterministic decision produced by a reviewed policy artifact. The artifact decided the exemption below. You MUST accept its decision and explain it in plain English, citing the authority from the provided 'reason' list. You MUST NOT add claims the artifact did not make. You MUST NOT override the artifact's action."""

EXPLAIN_SCHEMA = {
    "type": "object",
    "properties": {
        "exemption": {"type": "string"},
        "releasable": {"type": "boolean"},
        "rationale": {"type": "string"},
        "cited_authorities": {"type": "array", "items": {
            "type": "object", "properties": {"cite": {"type": "string"}, "excerpt": {"type": "string"}}, "required": ["cite", "excerpt"]
        }},
        "confidence": {"type": "string", "enum": ["deterministic"]},
    },
    "required": ["exemption", "releasable", "rationale", "cited_authorities", "confidence"],
}

def run_pearl(features: dict) -> dict:
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(features, f); tmp = f.name
    res = subprocess.run(
        ["logicpearl", "run", str(ARTIFACT), tmp, "--explain", "--json"],
        capture_output=True, text=True,
    )
    if res.returncode != 0:
        raise RuntimeError(f"logicpearl run failed: {res.stderr}")
    return json.loads(res.stdout)

def answer(scenario_path: Path, llm_cfg: LLMConfig) -> dict:
    s = load_scenario(scenario_path)
    llm = make_llm(llm_cfg)
    tool = build_extract_tool()
    t0 = time.time()
    features = llm.chat_tool(system=EXTRACT_SYSTEM, user=s.description, tool=tool, temperature=0.0)
    t_extract = time.time() - t0

    t1 = time.time()
    try:
        pearl_out = run_pearl(features)
    except RuntimeError as e:
        return {"error": "pearl_run_failed", "detail": str(e), "features": features}
    t_pearl = time.time() - t1

    action = pearl_out.get("action") or pearl_out.get("decision") or "releasable"
    reason = pearl_out.get("reason") or pearl_out.get("rules") or []
    cites_from_artifact = []
    for key in FD:
        if features.get(key) and any(key in r for r in (reason if isinstance(reason, list) else [reason])):
            cites_from_artifact.append({"cite": FD[key]["cite"], "excerpt": FD[key]["label"]})

    user_blob = (
        f"RECORD DESCRIPTION:\n{s.description}\n\n"
        f"ARTIFACT ACTION: {action}\n"
        f"ARTIFACT REASON: {json.dumps(reason)}\n"
        f"AUTHORITIES (from artifact): {json.dumps(cites_from_artifact)}\n"
    )
    t2 = time.time()
    explained = llm.chat_json(system=EXPLAIN_SYSTEM, user=user_blob, schema=EXPLAIN_SCHEMA, temperature=0.0)
    t_explain = time.time() - t2

    # Architectural rule: LLM cannot override the artifact's action.
    explained["exemption"] = action
    explained["releasable"] = (action == "releasable")
    explained["confidence"] = "deterministic"
    explained["_latency_s"] = {
        "extract": round(t_extract, 3),
        "pearl": round(t_pearl, 3),
        "explain": round(t_explain, 3),
    }
    explained["_features"] = features
    return explained

def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("scenario", type=Path)
    p.add_argument("--provider", default=os.environ.get("LP_LLM_PROVIDER", "anthropic"))
    p.add_argument("--model", default=os.environ.get("LP_LLM_MODEL", "claude-opus-4-6"))
    args = p.parse_args()
    cfg = LLMConfig(provider=args.provider, model=args.model)
    print(json.dumps(answer(args.scenario, cfg), indent=2))

if __name__ == "__main__":
    main()
```

**Step 2: Test the subprocess wiring (independent of LLM) by feeding a known feature vector.**

```python
# tests/test_pearl_subprocess.py
import json
from pathlib import Path
import pytest
from pearl.pearl import run_pearl, FD

@pytest.mark.skipif(not Path("pearl/artifact").exists(), reason="artifact not built")
def test_clearly_b1_routes_to_b1():
    features = {k: False for k in FD}
    features["classified_under_executive_order"] = True
    features["classification_still_in_force"] = True
    out = run_pearl(features)
    action = out.get("action") or out.get("decision")
    assert action == "b1", out
```

**Step 3: Run tests; commit.**

```bash
uv run pytest tests/test_pearl_subprocess.py -v
git add pearl/pearl.py tests/test_pearl_subprocess.py
git commit -m "pearl: runner w/ subprocess, explain, no-override rule"
```

---

## Task 19: Scenarios — 15 `.json` files

**Files:**
- Create: `scenarios/01_classified_memo.json` through `scenarios/15_rag_favored_synthesis.json`

**Distribution:** 8 clear-cut (one per exemption + one clearly releasable), 4 borderline, 2 out-of-distribution (pearl should refuse via `insufficient_context` in RAG answers — but the pearl path will produce its best guess or fall to `releasable`; in the transcript, borderline/OOD are marked for the viewer), 1 rag-favored synthesis.

**Step 1: Write each file** using the shape specified in `ragdemo/scenarios.py`. Example:

```json
{
  "id": "01_classified_memo",
  "description": "An inter-agency memo classified TOP SECRET under Executive Order 13526 discussing active foreign intelligence operations. Classification is currently in force.",
  "expected": {"exemption": "b1", "releasable": false, "rationale_keywords": ["classified"], "expected_authority": "5 U.S.C. § 552(b)(1)"},
  "category": "clear-cut"
}
```

```json
{
  "id": "15_rag_favored_synthesis",
  "description": "Provide a two-paragraph summary of the legislative history of FOIA Exemption 5 and its major case law developments.",
  "expected": {"exemption": null, "releasable": true, "rationale_keywords": ["legislative", "history"], "expected_authority": null},
  "category": "rag-favored"
}
```

**Step 2: Verify they all load.**

```python
# tests/test_scenarios_repo.py
from pathlib import Path
from ragdemo.scenarios import load_scenarios

def test_15_scenarios_load():
    scs = load_scenarios(Path("scenarios"))
    assert len(scs) == 15
    cats = {s.category for s in scs}
    assert cats == {"clear-cut", "borderline", "out-of-distribution", "rag-favored"}
```

**Step 3: Run; commit.**

```bash
uv run pytest tests/test_scenarios_repo.py -v
git add scenarios/ tests/test_scenarios_repo.py
git commit -m "scenarios: 15 FOIA scenarios across all categories"
```

---

## Task 20: Comparison harness `compare.py`

**Files:**
- Create: `compare.py`
- Create: `tests/test_compare_metrics.py`
- Create: `transcripts/.gitkeep`

**Step 1: Test the pure metrics aggregation.**

```python
# tests/test_compare_metrics.py
from compare import determinism_score, correctness, summarize

def test_determinism_5_of_5():
    results = [{"exemption": "b5"}] * 5
    assert determinism_score(results) == (5, 5)

def test_determinism_3_of_5():
    results = [{"exemption": "b5"}]*3 + [{"exemption": "b7"}, {"exemption": "b6"}]
    assert determinism_score(results) == (3, 5)

def test_correctness_matches_expected():
    assert correctness({"exemption": "b5"}, "b5") is True
    assert correctness({"exemption": "b5"}, "b6") is False
```

**Step 2: Implement.**

```python
# compare.py
from __future__ import annotations
import argparse, json, os, subprocess, sys, time
from collections import Counter
from pathlib import Path
from rich.console import Console
from rich.table import Table
from ragdemo.llm import LLMConfig
from ragdemo.scenarios import load_scenarios, Scenario
from rag.rag import answer as rag_answer
from pearl.pearl import answer as pearl_answer

def determinism_score(results: list[dict]) -> tuple[int, int]:
    if not results: return (0, 0)
    keys = [json.dumps({k: v for k, v in r.items() if not k.startswith("_")}, sort_keys=True) for r in results]
    c = Counter(keys)
    return (c.most_common(1)[0][1], len(results))

def correctness(result: dict, expected: str | None) -> bool:
    if expected is None:
        return result.get("exemption") in (None, "releasable", "insufficient_context", "not_applicable")
    return result.get("exemption") == expected

def citation_faithfulness(result: dict) -> tuple[int, int]:
    checks = result.get("_citation_faithfulness", [])
    if not checks:
        # pearl side cites come from artifact; treat as 100%.
        cites = result.get("cited_authorities", [])
        return (len(cites), len(cites))
    ok = sum(1 for c in checks if c["ok"])
    return (ok, len(checks))

def summarize(scenario: Scenario, rag_runs: list[dict], pearl_runs: list[dict]) -> dict:
    return {
        "id": scenario.id,
        "category": scenario.category,
        "expected": scenario.expected.exemption,
        "rag": {
            "correct": sum(correctness(r, scenario.expected.exemption) for r in rag_runs),
            "determinism": determinism_score(rag_runs),
            "citation_ok": [citation_faithfulness(r) for r in rag_runs],
        },
        "pearl": {
            "correct": sum(correctness(r, scenario.expected.exemption) for r in pearl_runs),
            "determinism": determinism_score(pearl_runs),
            "citation_ok": [citation_faithfulness(r) for r in pearl_runs],
        },
    }

def build_manifest(provider: str, model: str) -> dict:
    git_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    lp_ver = subprocess.check_output(["logicpearl", "--version"], text=True).strip()
    raw = Path("corpus/raw/MANIFEST.json")
    art = Path("pearl/artifact/artifact.json")
    return {
        "git_sha": git_sha,
        "logicpearl_version": lp_ver,
        "provider": provider, "model": model,
        "corpus_manifest": json.loads(raw.read_text()) if raw.exists() else None,
        "artifact_manifest": json.loads(art.read_text()) if art.exists() else None,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

def render_transcript(summaries: list[dict], manifest: dict, out: Path):
    lines = [f"# Transcript ({manifest['timestamp']})", "",
             f"- provider: `{manifest['provider']}` model: `{manifest['model']}`",
             f"- git sha: `{manifest['git_sha']}`  logicpearl: `{manifest['logicpearl_version']}`",
             "", "## Summary", "", "| scenario | category | expected | RAG correct/det/cite | Pearl correct/det/cite |",
             "|---|---|---|---|---|"]
    for s in summaries:
        def fmt(side):
            c = side["correct"]; d = side["determinism"]
            cit = side["citation_ok"]; cit_ok = sum(x[0] for x in cit); cit_tot = sum(x[1] for x in cit)
            return f"{c}/{d[1]} / {d[0]}/{d[1]} / {cit_ok}/{cit_tot}"
        lines.append(f"| {s['id']} | {s['category']} | {s['expected']} | {fmt(s['rag'])} | {fmt(s['pearl'])} |")
    out.write_text("\n".join(lines))

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--provider", default=os.environ.get("LP_LLM_PROVIDER", "anthropic"))
    p.add_argument("--model", default=os.environ.get("LP_LLM_MODEL", "claude-opus-4-6"))
    p.add_argument("--repeat", type=int, default=5)
    p.add_argument("--only", default=None, help="only run scenarios whose id contains this string")
    args = p.parse_args()
    cfg = LLMConfig(provider=args.provider, model=args.model)
    scs = load_scenarios(Path("scenarios"))
    if args.only:
        scs = [s for s in scs if args.only in s.id]
    console = Console()
    summaries = []
    for s in scs:
        console.rule(f"{s.id}  [{s.category}]")
        rag_runs = []; pearl_runs = []
        for i in range(args.repeat):
            console.print(f"  rag run {i+1}/{args.repeat}")
            try:
                rag_runs.append(rag_answer(Path(f"scenarios/{s.id}.json"), cfg))
            except Exception as e:
                rag_runs.append({"error": str(e)})
            console.print(f"  pearl run {i+1}/{args.repeat}")
            try:
                pearl_runs.append(pearl_answer(Path(f"scenarios/{s.id}.json"), cfg))
            except Exception as e:
                pearl_runs.append({"error": str(e)})
        summaries.append(summarize(s, rag_runs, pearl_runs))

    # Output
    Path("transcripts").mkdir(exist_ok=True)
    ts = time.strftime("%Y-%m-%d")
    manifest = build_manifest(args.provider, args.model)
    out_md = Path(f"transcripts/{ts}-{args.provider}.md")
    out_json = Path(f"transcripts/{ts}-{args.provider}.manifest.json")
    render_transcript(summaries, manifest, out_md)
    out_json.write_text(json.dumps({"manifest": manifest, "summaries": summaries}, indent=2))
    console.print(f"\nwrote: {out_md}  and  {out_json}")
    # Print summary table
    t = Table(title="Summary")
    for col in ["scenario", "category", "expected", "RAG ✓/det/cite", "Pearl ✓/det/cite"]:
        t.add_column(col)
    for s in summaries:
        def fmt(side):
            return f"{side['correct']}/{side['determinism'][1]}  {side['determinism'][0]}/{side['determinism'][1]}  " \
                   f"{sum(x[0] for x in side['citation_ok'])}/{sum(x[1] for x in side['citation_ok'])}"
        t.add_row(s["id"], s["category"], str(s["expected"]), fmt(s["rag"]), fmt(s["pearl"]))
    console.print(t)

if __name__ == "__main__":
    main()
```

**Step 3: Run unit tests.**

```bash
uv run pytest tests/test_compare_metrics.py -v
```

**Step 4: Commit.**

```bash
git add compare.py tests/test_compare_metrics.py transcripts/.gitkeep
git commit -m "compare: harness w/ metrics, transcript, manifest"
```

---

## Task 21: Top-level README + Makefile finalization + smoke target

**Files:**
- Modify: `README.md` (full version)
- Modify: `Makefile` (add `smoke` target)

**Step 1: Expand `README.md`** — 2-paragraph story, 4-command reproduce block, link to a checked-in transcript, limitations section.

**Step 2: Add `smoke` Makefile target** that runs a single scenario end-to-end with `--repeat 1` to catch wiring errors quickly.

```makefile
smoke:
	uv run python compare.py --only 01_classified_memo --repeat 1
```

**Step 3: Commit.**

```bash
git add README.md Makefile
git commit -m "docs: expand README + make smoke target"
```

---

## Task 22: End-to-end demo run + captured transcript

**Files:**
- Create: `transcripts/YYYY-MM-DD-anthropic.md`, `.manifest.json`

**Step 1: Run the full pipeline live.**

```bash
cd ~/Documents/LogicPearl/rag-demo
cp .env.example .env  # edit with ANTHROPIC_API_KEY + OPENAI_API_KEY
make fetch
make index
make build
make demo
```

**Step 2: Inspect the transcript and spot-check**

- `make test` still passes.
- Determinism: Pearl 5/5 on every scenario; RAG <5/5 on at least one borderline.
- Citation faithfulness: Pearl 100%; RAG <100% on at least one run.
- RAG wins scenario 15.
- On OOD scenarios, the transcript shows the contrast cleanly.

**Step 3: Commit transcript.**

```bash
git add transcripts/*.md transcripts/*.manifest.json
git commit -m "transcripts: initial end-to-end capture (Anthropic)"
```

**Step 4: Push if remote exists.** (Skip if this stays local.)

---

## Done criteria

- `make fetch && make index && make build && make demo` runs cleanly from a fresh clone after `uv sync` and `.env` setup.
- All unit tests pass: `make test`.
- `pearl/artifact/` verifies with `logicpearl artifact verify`.
- A checked-in transcript under `transcripts/` demonstrates: pearl ≥ 90% correct on clear-cut, 5/5 determinism throughout, 100% citation faithfulness, refusal or "not applicable" on out-of-distribution + rag-favored. RAG shows realistic ranges on each metric, including at least one fabricated-cite flag and at least one determinism miss.

---

## Risk register

- **DOJ Guide PDFs may require different URLs or change format.** Mitigation: `sources.toml` is the single place to edit; snapshot covers statute. Acceptable to ship the demo with only the statute + CFR + cases if Guide PDFs are hostile; note in README.
- **Cross-encoder rerank model download adds ~100MB first run.** Mitigation: note in README; cache under `~/.cache/torch`.
- **Chroma + OpenAI embeddings cost a few cents per full index.** Mitigation: set `LP_EMBEDDING_PROVIDER=sentence_transformers` for a fully offline index.
- **Trace rows may not reach 100% parity on first build.** Mitigation: `logicpearl inspect` reveals the conflict; edit `traces.csv`, regenerate review, rebuild. Task 16 blocks on 100% parity.
- **Ollama tool-use quality is lower than Claude/OpenAI.** Mitigation: documented in README as a known weaker path; used for "no-cloud" story, not for the headline transcript.
