from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from extraction.shared_extractor import extract_one
from rag_vs_pag.features import validate_feature_payload
from rag_vs_pag.jsonio import read_json, write_json
from rag_vs_pag.paths import root_path
from rag_vs_pag.ruleset import evaluate_ruleset
from rag_vs_pag.schema import Scenario


def run(
    scenario: Scenario,
    *,
    track: str,
    shared_features: dict[str, bool] | None = None,
    ruleset_path: str | Path = root_path("pearl", "rulesets", "v2", "rules.json"),
) -> dict[str, Any]:
    ruleset = read_json(ruleset_path)
    if track == "B" and shared_features is not None:
        features = shared_features
        extraction = {
            "source": "shared",
            "features": features,
            "evidence": {},
            "uncertain_features": [],
        }
    else:
        payload = validate_feature_payload(extract_one(scenario.request_text, scenario.agency_name))
        features = payload["features"]
        extraction = {"source": "logicpearl_extractor", **payload}
    decision = evaluate_ruleset(ruleset, features)
    return {
        "pipeline": "logicpearl",
        "track": track,
        "scenario_id": scenario.id,
        "input_mode": "request_text+ruleset" if track == "A" else "shared_features+ruleset",
        "verdict": decision["verdict"],
        "rationale": f"{decision['rule_label']} ({decision['rule_id']}).",
        "feature_extraction": extraction,
        "ruleset_decision": decision,
        "authority_ids": decision["authority_ids"],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("scenario_json")
    parser.add_argument("--track", choices=["A", "B"], default="A")
    parser.add_argument("--ruleset", default=str(root_path("pearl", "rulesets", "v2", "rules.json")))
    parser.add_argument("--output")
    args = parser.parse_args()
    scenario = Scenario.from_dict(read_json(args.scenario_json))
    result = run(scenario, track=args.track, ruleset_path=args.ruleset)
    if args.output:
        write_json(args.output, result)
    else:
        print(result)


if __name__ == "__main__":
    main()
