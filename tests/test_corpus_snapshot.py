from pathlib import Path

SNAPSHOT = Path(__file__).parent.parent / "corpus" / "snapshot" / "5_usc_552.txt"


def test_snapshot_exists_and_nonempty():
    assert SNAPSHOT.exists()
    assert SNAPSHOT.stat().st_size > 1000


def test_snapshot_has_subsection_b():
    text = SNAPSHOT.read_text()
    assert "(b) This section does not apply" in text


def test_snapshot_contains_all_nine_exemptions():
    # Each exemption appears in the (b) section as a numbered paragraph.
    # We look for the (b)(N) or lone (N) marker within the (b) subsection.
    text = SNAPSHOT.read_text()
    b_start = text.find("(b) This section does not apply")
    assert b_start >= 0
    # Read ~3500 chars of (b) subsection content.
    b_block = text[b_start : b_start + 5000]
    for n in range(1, 10):
        assert f"({n})" in b_block, f"Exemption ({n}) marker missing in (b) block"


def test_snapshot_contains_exemption_5_language():
    text = SNAPSHOT.read_text().lower()
    assert "inter- agency" in text or "inter-agency" in text or "intra-agency" in text


def test_snapshot_contains_exemption_6_language():
    text = SNAPSHOT.read_text().lower()
    assert "personnel and medical files" in text
