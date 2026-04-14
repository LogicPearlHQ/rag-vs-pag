"""Load + structure-aware chunking of the FOIA corpus.

The same chunks drive RAG retrieval (dense + BM25) and serve as the review
surface for pearl traces. Every chunk carries citation metadata so answers
can cite back into real files.
"""
from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Chunk:
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


def _html_to_text(raw: str | bytes) -> str:
    """Best-effort HTML/byte-stream to readable plain text."""
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8", errors="ignore")
    # Drop script/style/noscript blocks entirely.
    raw = re.sub(r"<(script|style|noscript)[^>]*>.*?</\1>", " ", raw, flags=re.S | re.I)
    # Collapse tags to spaces.
    raw = re.sub(r"<[^>]+>", " ", raw)
    raw = html.unescape(raw)
    # Normalize whitespace.
    raw = re.sub(r"[ \t]+", " ", raw)
    raw = re.sub(r" *\n *", "\n", raw)
    raw = re.sub(r"\n{3,}", "\n\n", raw)
    return raw.strip()


def chunk_statute(text: str | bytes, doc_id: str = "5_usc_552") -> list[Chunk]:
    """Split 5 U.S.C. § 552 into one chunk per subsection under (b), plus (a)."""
    if isinstance(text, bytes) or "<html" in text[:200].lower() or "<!doctype" in text[:200].lower():
        text = _html_to_text(text)

    chunks: list[Chunk] = []

    # Isolate the (b) subsection. Cornell LII renders "(b) This section does not apply..."
    b_start = text.find("(b) This section does not apply")
    if b_start < 0:
        # Fallback: find any "(b)" line followed by exemption numbering.
        m = re.search(r"\(b\)\s+This section", text)
        b_start = m.start() if m else -1

    # Terminate (b) at (c) if present.
    b_end = text.find("(c)", b_start + 5) if b_start >= 0 else -1
    b_block = text[b_start:b_end] if b_start >= 0 and b_end > b_start else (text[b_start:] if b_start >= 0 else "")

    # Within (b), each exemption is a numbered paragraph. Cornell's rendering
    # places the numeral on its own line. We split on lines that start with
    # "(N)" where N is 1-9 and collect everything until the next "(M)" marker
    # or the end.
    if b_block:
        # Build a list of (index, N) positions.
        matches = list(re.finditer(r"(?m)^\((\d)\)\s*$|\((\d)\)(?=\s)", b_block))
        # Use a cleaner regex: find each "(N)" where N is 1..9 that sits on
        # its own line OR is followed by space and content at the top level.
        markers = []
        for m in re.finditer(r"(?m)^\((\d)\)\s", b_block):
            n = int(m.group(1))
            if 1 <= n <= 9:
                markers.append((m.start(), n))
        if not markers:
            # Fallback: any "(N)" followed by text at start of line.
            for m in re.finditer(r"(?m)^\s*\((\d)\)\s", b_block):
                n = int(m.group(1))
                if 1 <= n <= 9:
                    markers.append((m.start(), n))

        # Slice each exemption.
        for i, (pos, n) in enumerate(markers):
            end = markers[i + 1][0] if i + 1 < len(markers) else len(b_block)
            body = b_block[pos:end].strip()
            if not body:
                continue
            chunks.append(
                Chunk(
                    text=body,
                    metadata={
                        "source": doc_id,
                        "kind": "statute",
                        "cite": f"5 U.S.C. § 552(b)({n})",
                        "exemption": n,
                    },
                )
            )

    # Also keep a chunk for subsection (a) as context.
    a_start = text.find("(a)")
    if a_start >= 0 and b_start > a_start:
        chunks.insert(
            0,
            Chunk(
                text=text[a_start:b_start].strip(),
                metadata={
                    "source": doc_id,
                    "kind": "statute",
                    "cite": "5 U.S.C. § 552(a)",
                },
            ),
        )

    return chunks


def chunk_cfr(text: str | bytes, doc_id: str = "28_cfr_16") -> list[Chunk]:
    """Split a CFR Part into one chunk per section.

    Accepts either eCFR versioner XML (where sections are `<DIV8 N="16.N"
    TYPE="SECTION">` blocks) or already-rendered plain text with
    `§ 16.N Title.` headers.
    """
    if isinstance(text, bytes):
        text = text.decode("utf-8", errors="ignore")

    chunks: list[Chunk] = []

    # XML path: eCFR versioner output.
    if "<DIV8" in text:
        pattern = re.compile(
            r'<DIV8\s+N="([^"]+)"\s+TYPE="SECTION"[^>]*>(.*?)</DIV8>',
            re.S,
        )
        for m in pattern.finditer(text):
            num = m.group(1)
            body_xml = m.group(2)
            # Pull the HEAD title if present.
            head = re.search(r"<HEAD>(.*?)</HEAD>", body_xml, re.S)
            title = _html_to_text(head.group(1)) if head else ""
            title = title.strip().rstrip(".")
            body = _html_to_text(body_xml)
            if len(body) < 40:
                continue
            chunks.append(
                Chunk(
                    text=body,
                    metadata={
                        "source": doc_id,
                        "kind": "cfr",
                        "cite": f"28 C.F.R. § {num}",
                        "title": title,
                    },
                )
            )
        return chunks

    # Plain text path.
    pattern = re.compile(
        r"§\s*16\.(\d+[a-z]?)\s*([^\n]{0,120})?(.*?)(?=§\s*16\.\d+[a-z]?|\Z)",
        re.S,
    )
    for m in pattern.finditer(text):
        num = m.group(1)
        title = (m.group(2) or "").strip().rstrip(".")
        body = m.group(0).strip()
        if len(body) < 40:
            continue
        chunks.append(
            Chunk(
                text=body,
                metadata={
                    "source": doc_id,
                    "kind": "cfr",
                    "cite": f"28 C.F.R. § 16.{num}",
                    "title": title,
                },
            )
        )
    return chunks


def chunk_case(text: str | bytes, doc_id: str, cite_root: str) -> list[Chunk]:
    """Split a court opinion into paragraph chunks."""
    if isinstance(text, bytes):
        text = text.decode("utf-8", errors="ignore")
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: list[Chunk] = []
    for i, p in enumerate(paragraphs, start=1):
        if len(p) < 60:
            continue
        chunks.append(
            Chunk(
                text=p,
                metadata={
                    "source": doc_id,
                    "kind": "case",
                    "cite": f"{cite_root}, para. {i}",
                },
            )
        )
    return chunks


def chunk_doj_guide_pdf(pdf_path: Path, doc_id: str, cite_root: str) -> list[Chunk]:
    """Chunk a DOJ Guide PDF by page with the chapter cite + page number."""
    from pypdf import PdfReader

    reader = PdfReader(str(pdf_path))
    chunks: list[Chunk] = []
    for i, page in enumerate(reader.pages, start=1):
        try:
            txt = (page.extract_text() or "").strip()
        except Exception:
            continue
        if len(txt) < 120:
            continue
        # Collapse egregious multi-space from PDF extraction.
        txt = re.sub(r"[ \t]+", " ", txt)
        chunks.append(
            Chunk(
                text=txt,
                metadata={
                    "source": doc_id,
                    "kind": "doj_guide",
                    "cite": f"{cite_root}, p. {i}",
                    "page": i,
                },
            )
        )
    return chunks


def load_corpus(raw_dir: Path) -> list[Chunk]:
    """Load all fetched corpus docs and return a flat list of chunks."""
    raw_dir = Path(raw_dir)
    manifest = json.loads((raw_dir / "MANIFEST.json").read_text())
    chunks: list[Chunk] = []
    for doc_id, meta in manifest.items():
        path = raw_dir / f"{doc_id}.bin"
        if not path.exists():
            continue
        kind = meta["kind"]
        if kind == "statute":
            chunks.extend(chunk_statute(path.read_bytes(), doc_id))
        elif kind == "cfr":
            chunks.extend(chunk_cfr(path.read_bytes(), doc_id))
        elif kind == "case":
            chunks.extend(chunk_case(path.read_bytes(), doc_id, meta["cite_root"]))
        elif kind == "doj_guide":
            chunks.extend(chunk_doj_guide_pdf(path, doc_id, meta["cite_root"]))
    return chunks
