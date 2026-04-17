from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from rag_vs_pag.jsonio import read_json, write_json
from rag_vs_pag.paths import root_path
from rag_vs_pag.retrieval_core import Chunk, retrieve


def load_index(path: str | Path = root_path("rag", "index.json")) -> list[Chunk]:
    return [Chunk.from_dict(row) for row in read_json(path)]


def retrieve_for_text(text: str, k: int = 4, index_path: str | Path = root_path("rag", "index.json")) -> list[dict]:
    return retrieve(text, load_index(index_path), k=k)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("query")
    parser.add_argument("--k", type=int, default=4)
    parser.add_argument("--output")
    args = parser.parse_args()
    rows = retrieve_for_text(args.query, k=args.k)
    if args.output:
        write_json(args.output, rows)
    else:
        for row in rows:
            print(f"{row['chunk_id']} {row['source_id']} {row['score']}: {row['text']}")


if __name__ == "__main__":
    main()
