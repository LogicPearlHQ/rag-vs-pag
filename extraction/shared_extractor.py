from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from rag_vs_pag.features import validate_feature_payload
from rag_vs_pag.hashutil import canonical_hash, sha256_file, sha256_text
from rag_vs_pag.jsonio import read_json, write_json
from rag_vs_pag.openai_structured import responses_json_schema
from rag_vs_pag.schema import load_scenarios


EXTRACTOR_TEMPLATE_VERSION = "rag_vs_pag.openai_extractor.v2"


def feature_names(feature_dictionary_path: str | Path | None = None) -> list[str]:
    path = Path(feature_dictionary_path or Path(__file__).with_name("feature_dictionary.json"))
    return sorted(read_json(path))


def structured_schema(feature_dictionary_path: str | Path | None = None) -> dict[str, Any]:
    names = feature_names(feature_dictionary_path)
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "features": {
                "type": "object",
                "additionalProperties": False,
                "properties": {name: {"type": "boolean"} for name in names},
                "required": names,
            },
            "evidence": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "feature": {"type": "string", "enum": names},
                        "quote": {"type": "string"},
                    },
                    "required": ["feature", "quote"],
                },
            },
            "uncertain_features": {
                "type": "array",
                "items": {"type": "string", "enum": names},
            },
        },
        "required": ["features", "evidence", "uncertain_features"],
    }


def normalize_structured_payload(payload: dict[str, Any]) -> dict[str, Any]:
    evidence = payload.get("evidence", {})
    if isinstance(evidence, list):
        evidence = {
            str(item.get("feature")): str(item.get("quote", ""))
            for item in evidence
            if isinstance(item, dict) and item.get("feature")
        }
    return validate_feature_payload({**payload, "evidence": evidence})


def cache_key(
    *,
    request_text: str,
    agency_name: str,
    model: str,
    prompt_hash: str,
    feature_dictionary_hash: str,
) -> str:
    return canonical_hash(
        {
            "request_text_hash": sha256_text(request_text),
            "agency_name": agency_name,
            "model": model,
            "prompt_hash": prompt_hash,
            "feature_dictionary_hash": feature_dictionary_hash,
            "schema_version": EXTRACTOR_TEMPLATE_VERSION,
        }
    ).removeprefix("sha256:")


def feature_definitions_text(feature_dictionary_path: str | Path | None = None) -> str:
    path = Path(feature_dictionary_path or Path(__file__).with_name("feature_dictionary.json"))
    dictionary = read_json(path)
    lines = []
    for name in sorted(dictionary):
        item = dictionary[name]
        lines.append(f"- {name}: {item.get('label', name)}")
    return "\n".join(lines)


def openai_user_message(
    request_text: str,
    agency_name: str,
    feature_dictionary_path: str | Path | None = None,
) -> str:
    return (
        "Extract request facts for FOIA exemption classification.\n\n"
        "Available features:\n"
        f"{feature_definitions_text(feature_dictionary_path)}\n\n"
        f"Agency: {agency_name}\n\n"
        f"Request text:\n{request_text}\n\n"
        "Return JSON only. Do not choose an exemption. Mark a feature true only "
        "when the request text or agency context supports it. Evidence quotes "
        "must be short phrases from the request or a concise agency-context note. "
        "Do not mark law-enforcement features merely because the agency is a law "
        "enforcement agency; the requested records must concern investigations, "
        "enforcement proceedings, confidential sources, techniques, raids, case "
        "files, arrests, inspections, or similar enforcement activity."
    )


def extract_one(
    request_text: str,
    agency_name: str,
    *,
    model: str | None = None,
    cache_dir: str | Path = "extraction/cache/openai",
    force: bool = False,
    feature_dictionary_path: str | Path | None = None,
    prompt_path: str | Path | None = None,
) -> dict:
    model = model or os.getenv("LP_LLM_MODEL", "gpt-4o-mini")
    prompt = Path(prompt_path or Path(__file__).with_name("extractor_prompt.md")).read_text(encoding="utf-8")
    feature_dictionary = Path(feature_dictionary_path or Path(__file__).with_name("feature_dictionary.json"))
    prompt_hash = sha256_text(prompt)
    feature_dictionary_hash = sha256_file(feature_dictionary)
    key = cache_key(
        request_text=request_text,
        agency_name=agency_name,
        model=model,
        prompt_hash=prompt_hash,
        feature_dictionary_hash=feature_dictionary_hash,
    )
    cache_path = Path(cache_dir) / f"{key}.json"
    if cache_path.exists() and not force:
        cached = read_json(cache_path)
        return normalize_structured_payload(cached["payload"])
    result = responses_json_schema(
        model=model,
        system=prompt,
        user=openai_user_message(request_text, agency_name, feature_dictionary),
        schema=structured_schema(feature_dictionary),
        schema_name="foia_feature_extraction",
        temperature=0.0,
    )
    payload = normalize_structured_payload(result["parsed"])
    write_json(
        cache_path,
        {
            "schema_version": "rag_vs_pag.openai_extractor_cache.v1",
            "provider": "openai",
            "model": result["model"],
            "requested_model": model,
            "prompt_hash": prompt_hash,
            "feature_dictionary_hash": feature_dictionary_hash,
            "cache_key": key,
            "raw_response_id": result["raw_response_id"],
            "usage": result["usage"],
            "payload": payload,
        },
    )
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenarios", default="scenarios/muckrock_snapshot.100.live.json")
    parser.add_argument("--output", default="extraction/outputs/shared_features.100.live.openai.json")
    parser.add_argument("--model", default=os.getenv("LP_LLM_MODEL", "gpt-4o-mini"))
    parser.add_argument("--cache-dir", default="extraction/cache/openai")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    scenarios = load_scenarios(read_json(args.scenarios))
    rows = []
    for scenario in scenarios:
        payload = extract_one(
            scenario.request_text,
            scenario.agency_name,
            model=args.model,
            cache_dir=args.cache_dir,
            force=args.force,
        )
        rows.append(
            {
                "scenario_id": scenario.id,
                "agency_name": scenario.agency_name,
                "extractor_provider": "openai",
                "extractor_model": args.model,
                "feature_payload": payload,
                "feature_hash": canonical_hash(payload["features"]),
            }
        )
    result = {
        "schema_version": "rag_vs_pag.shared_features.v1",
        "extractor_prompt_hash": sha256_file(Path(__file__).with_name("extractor_prompt.md")),
        "rows": rows,
    }
    write_json(args.output, result)
    print(f"wrote {args.output}")


if __name__ == "__main__":
    main()
