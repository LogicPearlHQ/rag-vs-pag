from pathlib import Path

from ragdemo.corpus import Chunk, chunk_statute

SNAPSHOT = Path(__file__).parent.parent / "corpus" / "snapshot" / "5_usc_552.txt"
RAW = Path(__file__).parent.parent / "corpus" / "raw" / "5_usc_552.bin"


def test_chunks_snapshot_text_into_all_nine_exemptions():
    chunks = chunk_statute(SNAPSHOT.read_text())
    exemption_chunks = [c for c in chunks if isinstance(c.metadata.get("exemption"), int)]
    assert {c.metadata["exemption"] for c in exemption_chunks} == set(range(1, 10))


def test_exemption_5_chunk_mentions_deliberative_language():
    chunks = chunk_statute(SNAPSHOT.read_text())
    b5 = next(c for c in chunks if c.metadata.get("exemption") == 5)
    assert b5.metadata["cite"] == "5 U.S.C. § 552(b)(5)"
    txt = b5.text.lower()
    assert "inter- agency" in txt or "inter-agency" in txt or "intra-agency" in txt


def test_exemption_1_chunk_mentions_classification():
    chunks = chunk_statute(SNAPSHOT.read_text())
    b1 = next(c for c in chunks if c.metadata.get("exemption") == 1)
    assert "classified" in b1.text.lower() or "executive order" in b1.text.lower()


def test_raw_html_bytes_also_work():
    if not RAW.exists():
        # corpus/raw populated only after `make fetch`; skip if missing.
        import pytest

        pytest.skip("raw corpus not fetched yet")
    chunks = chunk_statute(RAW.read_bytes())
    exemption_chunks = [c for c in chunks if isinstance(c.metadata.get("exemption"), int)]
    assert {c.metadata["exemption"] for c in exemption_chunks} == set(range(1, 10))


def test_chunk_dataclass_shape():
    chunks = chunk_statute(SNAPSHOT.read_text())
    for c in chunks:
        assert isinstance(c, Chunk)
        assert isinstance(c.text, str) and c.text
        assert "source" in c.metadata and "cite" in c.metadata
