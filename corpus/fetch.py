from __future__ import annotations

from pathlib import Path

from rag_vs_pag.hashutil import sha256_file
from rag_vs_pag.jsonio import write_json
from rag_vs_pag.paths import root_path


AUTHORITY_TEXT = """\
SOURCE foia_b1
TITLE 5 U.S.C. 552(b)(1)
Exemption 1 covers matters that are specifically authorized under criteria established by an Executive order to be kept secret in the interest of national defense or foreign policy and are in fact properly classified.

SOURCE foia_b2
TITLE 5 U.S.C. 552(b)(2)
Exemption 2 covers records related solely to the internal personnel rules and practices of an agency.

SOURCE foia_b3
TITLE 5 U.S.C. 552(b)(3)
Exemption 3 covers matters specifically exempted from disclosure by statute, if that statute requires withholding or establishes particular criteria for withholding.

SOURCE foia_b4
TITLE 5 U.S.C. 552(b)(4)
Exemption 4 covers trade secrets and commercial or financial information obtained from a person that is privileged or confidential.

SOURCE foia_b5
TITLE 5 U.S.C. 552(b)(5)
Exemption 5 covers inter-agency or intra-agency memorandums or letters that would not be available by law to a party in litigation with the agency, including deliberative process, attorney-client, and attorney work product materials.

SOURCE foia_b6
TITLE 5 U.S.C. 552(b)(6)
Exemption 6 covers personnel and medical files and similar files when disclosure would constitute a clearly unwarranted invasion of personal privacy.

SOURCE foia_b7
TITLE 5 U.S.C. 552(b)(7)
Exemption 7 covers records or information compiled for law enforcement purposes when production could reasonably be expected to interfere with enforcement proceedings, invade personal privacy, disclose a confidential source, disclose investigative techniques, or endanger safety.

SOURCE foia_b8
TITLE 5 U.S.C. 552(b)(8)
Exemption 8 covers matters contained in or related to examination, operating, or condition reports prepared by or for an agency responsible for regulation or supervision of financial institutions.

SOURCE foia_b9
TITLE 5 U.S.C. 552(b)(9)
Exemption 9 covers geological and geophysical information and data, including maps, concerning wells.
"""


def main() -> None:
    raw_dir = root_path("corpus", "raw")
    raw_dir.mkdir(parents=True, exist_ok=True)
    authority_path = raw_dir / "foia_authorities.txt"
    authority_path.write_text(AUTHORITY_TEXT, encoding="utf-8")
    write_json(
        raw_dir / "manifest.json",
        {
            "files": [
                {
                    "path": "foia_authorities.txt",
                    "sha256": sha256_file(authority_path),
                }
            ]
        },
    )
    print(f"wrote {authority_path.relative_to(root_path())}")


if __name__ == "__main__":
    main()
