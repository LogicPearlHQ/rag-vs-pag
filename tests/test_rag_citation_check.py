from ragdemo.corpus import Chunk

from rag.rag import check_citation


def test_matches_substring_with_matching_cite():
    chunk = Chunk(
        "The deliberative process privilege protects pre-decisional opinions of agency staff.",
        {"cite": "5 U.S.C. § 552(b)(5)"},
    )
    assert check_citation("5 U.S.C. § 552(b)(5)", "deliberative process privilege", [chunk])


def test_fallback_when_cite_mismatches_but_excerpt_matches():
    chunk = Chunk(
        "Pre-decisional deliberative memos qualify.",
        {"cite": "DOJ FOIA Guide, Exemption 5, p. 412"},
    )
    # LLM cited just "Exemption 5" but excerpt is real.
    assert check_citation("Exemption 5", "pre-decisional deliberative memos", [chunk])


def test_rejects_fabricated_excerpt():
    chunk = Chunk("Classified under Executive Order.", {"cite": "5 U.S.C. § 552(b)(1)"})
    assert not check_citation(
        "5 U.S.C. § 552(b)(1)",
        "The statute categorically forbids disclosure of diplomatic cables.",
        [chunk],
    )


def test_whitespace_insensitive_match():
    chunk = Chunk(
        "inter- agency  or  intra- agency memorandums",
        {"cite": "5 U.S.C. § 552(b)(5)"},
    )
    assert check_citation(
        "5 U.S.C. § 552(b)(5)",
        "inter-agency or intra-agency memorandums",
        [chunk],
    )
