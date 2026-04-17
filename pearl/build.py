from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from rag_vs_pag.hashutil import canonical_hash, sha256_file
from rag_vs_pag.features import empty_features
from rag_vs_pag.jsonio import read_json, write_json, write_jsonl


def build_trace_rows(ruleset: dict) -> list[dict]:
    rows = []
    for rule in ruleset.get("rules", []):
        features = empty_features()
        for feature in rule.get("all", []):
            features[feature] = True
        for feature in rule.get("any", [])[:1]:
            features[feature] = True
        row = {**features, "verdict": rule["verdict"]}
        rows.append(row)
    return rows


def maybe_build_logicpearl(traces_path: Path, output: Path) -> str | None:
    if not shutil.which("logicpearl"):
        return None
    lp_dir = output / "logicpearl"
    lp_dir.mkdir(parents=True, exist_ok=True)
    command = [
        "logicpearl",
        "build",
        str(traces_path),
        "--action-column",
        "verdict",
        "--output-dir",
        str(lp_dir),
        "--json",
    ]
    completed = subprocess.run(command, text=True, capture_output=True, check=False)
    (output / "logicpearl-build.stdout.json").write_text(completed.stdout, encoding="utf-8")
    (output / "logicpearl-build.stderr.txt").write_text(completed.stderr, encoding="utf-8")
    if completed.returncode != 0:
        return f"logicpearl build failed with exit {completed.returncode}"
    return "logicpearl build succeeded"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ruleset", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    ruleset_path = Path(args.ruleset)
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    ruleset = read_json(ruleset_path)
    traces = build_trace_rows(ruleset)
    traces_path = output / "decision_traces.jsonl"
    write_jsonl(traces_path, traces)
    write_json(output / "ruleset.json", ruleset)
    status = maybe_build_logicpearl(traces_path, output)
    manifest = {
        "schema_version": "rag_vs_pag.decision_artifact.v1",
        "ruleset_path": str(ruleset_path),
        "ruleset_hash": canonical_hash(ruleset),
        "ruleset_file_hash": sha256_file(ruleset_path),
        "trace_file_hash": sha256_file(traces_path),
        "logicpearl_status": status,
    }
    write_json(output / "artifact.json", manifest)
    print(f"built {output}")


if __name__ == "__main__":
    main()
