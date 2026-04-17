from __future__ import annotations

from typing import Any

from rag_vs_pag.hashutil import canonical_hash
from rag_vs_pag.jsonio import read_json


def _matches(rule: dict[str, Any], features: dict[str, bool]) -> bool:
    for feature in rule.get("all", []):
        if not features.get(feature, False):
            return False
    for feature in rule.get("any", []):
        if features.get(feature, False):
            return True
    if rule.get("any"):
        return False
    for feature in rule.get("none", []):
        if features.get(feature, False):
            return False
    return True


def evaluate_ruleset(ruleset: dict[str, Any], features: dict[str, bool]) -> dict[str, Any]:
    rules = sorted(ruleset.get("rules", []), key=lambda row: (row.get("priority", 1000), row.get("id", "")))
    matched = []
    for rule in rules:
        if _matches(rule, features):
            matched.append(rule)
            return {
                "verdict": rule["verdict"],
                "rule_id": rule["id"],
                "rule_label": rule.get("label", rule["id"]),
                "authority_ids": rule.get("authority_ids", []),
                "matched_rules": [rule["id"]],
                "ruleset_id": ruleset.get("ruleset_id"),
                "ruleset_version": ruleset.get("version"),
                "ruleset_hash": canonical_hash(ruleset),
                "defaulted": False,
            }
    default = ruleset.get("default", {"verdict": "insufficient_facts", "authority_ids": []})
    return {
        "verdict": default["verdict"],
        "rule_id": "default",
        "rule_label": default.get("label", "Insufficient request facts"),
        "authority_ids": default.get("authority_ids", []),
        "matched_rules": [],
        "ruleset_id": ruleset.get("ruleset_id"),
        "ruleset_version": ruleset.get("version"),
        "ruleset_hash": canonical_hash(ruleset),
        "defaulted": True,
    }


def evaluate_ruleset_file(path: str, features: dict[str, bool]) -> dict[str, Any]:
    return evaluate_ruleset(read_json(path), features)
