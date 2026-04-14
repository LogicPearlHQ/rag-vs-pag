"""LogicPearl runner.

Flow, per scenario:

  1. LLM tool-call `extract_features(description)` returns a JSON dict
     matching the feature schema derived from feature_dictionary.json.
  2. That dict is fed to `logicpearl run <artifact> features.json --explain
     --json` as a subprocess. The artifact's decision is authoritative —
     the LLM cannot override it.
  3. A second LLM pass (chat_json) composes a plain-English explanation,
     citing authorities pulled from the artifact itself. The explanation
     MUST defer to the artifact's action; if it doesn't, we clobber it.

Architectural rule enforced in code: the `action` the pearl returned is
copied verbatim into the final answer, replacing whatever the LLM decided
to say. The LLM is a normalizer, not a decider.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import tempfile
import time
from pathlib import Path

from ragdemo.llm import LLMConfig, make_llm
from ragdemo.scenarios import load_scenario

ROOT = Path(__file__).parent
FD_PATH = ROOT / "feature_dictionary.json"
ARTIFACT = ROOT / "artifact"

FD = json.loads(FD_PATH.read_text())


def build_extract_tool() -> dict:
    props = {
        k: {"type": "boolean", "description": v["label"]}
        for k, v in FD.items()
    }
    return {
        "name": "extract_features",
        "description": (
            "Extract the FOIA exemption features from the record "
            "description. Set a feature TRUE only if the description clearly "
            "states or directly implies it. If the description is ambiguous "
            "for a feature, set it to FALSE."
        ),
        "input_schema": {
            "type": "object",
            "properties": props,
            "required": list(FD.keys()),
            "additionalProperties": False,
        },
    }


EXTRACT_SYSTEM = """You are a FOIA analyst performing structured feature extraction.

Given a free-text record description, set each feature TRUE only if the description clearly states or directly implies it. Err on the side of FALSE for ambiguous cases — the artifact will reach its conclusion on whatever features you mark, and false positives cause wrong answers. Do not speculate beyond the text."""


EXPLAIN_SYSTEM = """You are explaining a deterministic decision produced by a reviewed policy artifact.

The artifact has already decided the exemption. Your job is to explain its decision in plain English, citing authorities drawn from the artifact's own rule output. You MUST:
  - Accept the artifact's action verbatim.
  - Cite authorities the artifact provides; do not add new cites.
  - Not contradict the artifact, hedge, or suggest alternatives.

If the artifact's action is `releasable`, say the record is releasable."""


EXPLAIN_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "rationale": {"type": "string"},
        "cited_authorities": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "cite": {"type": "string"},
                    "excerpt": {"type": "string"},
                },
                "required": ["cite", "excerpt"],
            },
        },
    },
    "required": ["rationale", "cited_authorities"],
}


def run_pearl(features: dict) -> dict:
    """Run `logicpearl run` subprocess on features, return the parsed JSON."""
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(features, f)
        tmp = f.name
    res = subprocess.run(
        ["logicpearl", "run", str(ARTIFACT), tmp, "--explain", "--json"],
        capture_output=True,
        text=True,
    )
    if res.returncode != 0:
        raise RuntimeError(
            f"logicpearl run failed (rc={res.returncode}): {res.stderr.strip()}"
        )
    return json.loads(res.stdout)


def _pearl_cites(features: dict, rule_reasons: list | str) -> list[dict]:
    """Return cited authorities drawn from the pearl's rule output."""
    reasons = rule_reasons if isinstance(rule_reasons, list) else [str(rule_reasons)]
    cites: list[dict] = []
    seen: set[str] = set()
    for feat, meta in FD.items():
        if not features.get(feat):
            continue
        pretty = feat.replace("_", " ").title()
        if any(pretty in str(r) for r in reasons):
            cite = meta["cite"]
            if cite in seen:
                continue
            seen.add(cite)
            cites.append({"cite": cite, "excerpt": meta["label"]})
    # Fallback: if we found no match (reason text differs from title-case), cite
    # every TRUE feature's authority.
    if not cites:
        for feat, meta in FD.items():
            if features.get(feat):
                cite = meta["cite"]
                if cite in seen:
                    continue
                seen.add(cite)
                cites.append({"cite": cite, "excerpt": meta["label"]})
    return cites


def _compose_template_rationale(action: str, features: dict, cited: list[dict]) -> str:
    """Deterministic, LLM-free rationale for keyword-mode pearl runs."""
    if action == "releasable":
        true_feats = [k for k, v in features.items() if v]
        if not true_feats:
            return (
                "No feature in the pearl's schema was triggered by the record "
                "description. The reviewed rules do not reach any exemption; "
                "the record is releasable under FOIA's default presumption."
            )
        return (
            f"The record triggered {len(true_feats)} feature(s) "
            f"({', '.join(true_feats)}) but no exemption rule fires on this "
            "combination. The reviewed rules treat partial elements of an "
            "exemption as insufficient to withhold; the record is releasable."
        )
    cite_lines = "; ".join(c["cite"] for c in cited)
    return (
        f"The record is exempt under {action} because the features "
        f"{', '.join(k for k, v in features.items() if v)} match the rule "
        f"reviewed in the pearl. Authorities: {cite_lines}."
    )


def answer(scenario_path: Path, llm_cfg: LLMConfig, extractor: str = "llm") -> dict:
    """Run the scenario through the pearl.

    extractor:
      "llm"     - use LLM tool-use to extract features (default, most robust)
      "keyword" - use the deterministic keyword extractor (zero LLM calls)
    """
    s = load_scenario(scenario_path)

    # Step 1: feature extraction.
    t0 = time.time()
    if extractor == "keyword":
        from .keyword_extractor import extract_features as kw_extract

        features = kw_extract(s.description, FD)
    else:
        llm = make_llm(llm_cfg)
        tool = build_extract_tool()
        try:
            features = llm.chat_tool(
                system=EXTRACT_SYSTEM,
                user=s.description,
                tool=tool,
                temperature=0.0,
            )
        except Exception as e:
            return {"error": "feature_extraction_failed", "detail": str(e)}
    t_extract = time.time() - t0

    # Validate feature shape; refuse if malformed rather than guess.
    missing = [k for k in FD if k not in features]
    extra = [k for k in features if k not in FD]
    if missing or extra:
        return {
            "error": "feature_extraction_failed",
            "detail": f"missing={missing} extra={extra}",
            "features": features,
        }

    # Step 2: pearl subprocess.
    t1 = time.time()
    try:
        pearl_out = run_pearl(features)
    except RuntimeError as e:
        return {"error": "pearl_run_failed", "detail": str(e), "features": features}
    t_pearl = time.time() - t1

    action = (
        pearl_out.get("action")
        or pearl_out.get("decision")
        or pearl_out.get("result", {}).get("action")
        or "releasable"
    )
    reasons = (
        pearl_out.get("reason")
        or pearl_out.get("rules")
        or pearl_out.get("explanation")
        or []
    )
    cited = _pearl_cites(features, reasons)

    # Step 3: explanation. Template (deterministic) in keyword mode; LLM in
    # llm mode. In both cases the action is fixed by the artifact.
    t2 = time.time()
    if extractor == "keyword":
        explained = {
            "rationale": _compose_template_rationale(action, features, cited),
            "cited_authorities": cited,
        }
    else:
        explain_user = (
            f"RECORD DESCRIPTION:\n{s.description}\n\n"
            f"ARTIFACT ACTION: {action}\n"
            f"ARTIFACT REASON: {json.dumps(reasons)}\n"
            f"AUTHORITIES FROM ARTIFACT: {json.dumps(cited)}\n"
        )
        try:
            llm = make_llm(llm_cfg)
            explained = llm.chat_json(
                system=EXPLAIN_SYSTEM,
                user=explain_user,
                schema=EXPLAIN_SCHEMA,
                temperature=0.0,
            )
        except Exception as e:
            explained = {"rationale": f"(LLM explanation failed: {e})", "cited_authorities": cited}
    t_explain = time.time() - t2

    # Architectural rule: action/releasable/confidence come from the artifact.
    result = {
        "exemption": action,
        "releasable": action == "releasable",
        "rationale": explained.get("rationale", ""),
        "cited_authorities": explained.get("cited_authorities") or cited,
        "confidence": "deterministic",
        "_latency_s": {
            "extract": round(t_extract, 3),
            "pearl": round(t_pearl, 3),
            "explain": round(t_explain, 3),
        },
        "_features": features,
        "_pearl_reasons": reasons,
    }
    return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument("scenario", type=Path)
    p.add_argument("--provider", default=os.environ.get("LP_LLM_PROVIDER", "openai"))
    p.add_argument("--model", default=os.environ.get("LP_LLM_MODEL", "gpt-4o"))
    p.add_argument(
        "--extractor",
        default=os.environ.get("LP_PEARL_EXTRACTOR", "llm"),
        choices=["llm", "keyword"],
        help="LLM tool-use (default) or deterministic keyword match (no LLM)",
    )
    args = p.parse_args()
    cfg = LLMConfig(provider=args.provider, model=args.model)
    print(json.dumps(answer(args.scenario, cfg, extractor=args.extractor), indent=2))


if __name__ == "__main__":
    main()
