"""Regenerate transcript .md from an existing manifest .json (no new LLM calls).

Used when we update the transcript rendering logic without wanting to rerun
the full demo.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from compare import render_transcript_md


def main():
    p = argparse.ArgumentParser()
    p.add_argument("manifest_json", type=Path)
    args = p.parse_args()
    data = json.loads(args.manifest_json.read_text())
    summaries = data["summaries"]
    # Backfill full_determinism for pre-fix runs that only stored decision-level.
    for s in summaries:
        for side in ("rag", "pearl"):
            if "full_determinism" not in s[side]:
                # Old runs stored the full-output determinism as `determinism`.
                # We don't have the raw per-run outputs here, so copy it into
                # `full_determinism` and recompute decision-level from answers.
                from collections import Counter

                answers = s[side].get("answers", [])
                if answers:
                    most_common = Counter(answers).most_common(1)[0][1]
                    s[side]["full_determinism"] = s[side]["determinism"]
                    s[side]["determinism"] = [most_common, len(answers)]
                else:
                    s[side]["full_determinism"] = s[side]["determinism"]
    md_path = args.manifest_json.with_suffix("").with_suffix(".md")
    md_path.write_text(render_transcript_md(summaries, data["manifest"]))
    print(f"rewrote {md_path}")


if __name__ == "__main__":
    main()
