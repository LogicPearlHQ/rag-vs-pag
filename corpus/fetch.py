"""Fetch docs listed in corpus/sources.toml into corpus/raw/, verifying sha256.

If a URL fails or its sha256 doesn't match, fall back to corpus/snapshot/<id>.txt
when present. Always writes corpus/raw/MANIFEST.json recording what was actually
stored (sha256, url, kind, cite_root) so downstream chunkers have a single
source of truth.
"""
from __future__ import annotations

import hashlib
import json
import sys
import tomllib
from pathlib import Path

import httpx

ROOT = Path(__file__).parent
SOURCES = ROOT / "sources.toml"
RAW = ROOT / "raw"
SNAPSHOT = ROOT / "snapshot"
MANIFEST = RAW / "MANIFEST.json"


class FetchError(RuntimeError):
    pass


def fetch_one(url: str, expected_sha: str, out: Path) -> str:
    """Fetch `url` to `out`; verify sha256 unless expected_sha == 'TBD'. Return observed sha256."""
    out.parent.mkdir(parents=True, exist_ok=True)
    with httpx.Client(
        follow_redirects=True,
        timeout=60,
        headers={"User-Agent": "rag-demo/0.1 (FOIA corpus fetcher)"},
    ) as c:
        r = c.get(url)
        r.raise_for_status()
        data = r.content
    actual = hashlib.sha256(data).hexdigest()
    if expected_sha not in ("TBD", "", None) and actual != expected_sha:
        raise FetchError(
            f"sha256 mismatch for {url}: expected {expected_sha}, got {actual}"
        )
    out.write_bytes(data)
    return actual


def main() -> int:
    RAW.mkdir(exist_ok=True)
    with SOURCES.open("rb") as f:
        cfg = tomllib.load(f)

    manifest: dict[str, dict] = {}
    failures: list[str] = []

    for doc in cfg["documents"]:
        out = RAW / f"{doc['id']}.bin"
        print(f"fetching {doc['id']}  <-  {doc['url']}")
        try:
            sha = fetch_one(doc["url"], doc["sha256"], out)
        except (httpx.HTTPError, FetchError) as e:
            print(f"  ! {e}", file=sys.stderr)
            snap = SNAPSHOT / f"{doc['id']}.txt"
            if snap.exists():
                print(f"  using snapshot fallback: {snap}")
                out.write_bytes(snap.read_bytes())
                sha = hashlib.sha256(out.read_bytes()).hexdigest()
            else:
                print(f"  no snapshot for {doc['id']}; skipping")
                failures.append(doc["id"])
                continue

        manifest[doc["id"]] = {
            "sha256": sha,
            "url": doc["url"],
            "kind": doc["kind"],
            "cite_root": doc["cite_root"],
        }
        print(f"  -> {out}  sha256={sha[:12]}...")

    MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True))
    print(f"\nmanifest: {MANIFEST}  ({len(manifest)} docs)")
    if failures:
        print(f"failed: {', '.join(failures)}", file=sys.stderr)
    return 0 if manifest else 1


if __name__ == "__main__":
    raise SystemExit(main())
