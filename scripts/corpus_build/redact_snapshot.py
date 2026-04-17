from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from rag_vs_pag.jsonio import read_json, write_json
from rag_vs_pag.text import redact_pii


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    rows = []
    for row in read_json(args.input):
        copied = dict(row)
        for key in ("request_text", "response_text"):
            if key in copied:
                copied[key] = redact_pii(copied[key])
        rows.append(copied)
    write_json(args.output, rows)


if __name__ == "__main__":
    main()
