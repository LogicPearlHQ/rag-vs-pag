from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from rag_vs_pag.jsonio import write_json
from rag_vs_pag.paths import root_path
from rag_vs_pag.retrieval_core import parse_authority_text


def main() -> None:
    authority_path = root_path("corpus", "raw", "foia_authorities.txt")
    if not authority_path.exists():
        raise SystemExit("run make fetch first")
    chunks = parse_authority_text(authority_path.read_text(encoding="utf-8"))
    write_json(root_path("rag", "index.json"), [chunk.to_dict() for chunk in chunks])
    print(f"indexed {len(chunks)} chunks")


if __name__ == "__main__":
    main()
