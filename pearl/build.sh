#!/usr/bin/env bash
# Build the LogicPearl artifact from pearl/traces.csv.
#
# traces.csv is the authoritative human review surface — it carries every
# feature column + the exemption label + a `source` citation + a `note`.
# LogicPearl's build would treat `source` and `note` as features; we strip
# them into traces_logic.csv first and feed that to the builder.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ARTIFACT="$HERE/artifact"
LOGIC_CSV="$HERE/traces_logic.csv"

python3 - "$HERE/traces.csv" "$LOGIC_CSV" <<'PY'
import csv, sys
src, dst = sys.argv[1], sys.argv[2]
skip = {"source", "note"}
with open(src) as f, open(dst, "w", newline="") as g:
    r = csv.reader(f)
    headers = next(r)
    keep = [i for i, h in enumerate(headers) if h not in skip]
    w = csv.writer(g)
    w.writerow([headers[i] for i in keep])
    for row in r:
        w.writerow([row[i] for i in keep])
print(f"wrote {dst}")
PY

rm -rf "$ARTIFACT"
logicpearl build "$LOGIC_CSV" \
  --action-column exemption \
  --default-action releasable \
  --gate-id foia_exemptions \
  --feature-dictionary "$HERE/feature_dictionary.json" \
  --output-dir "$ARTIFACT"

echo
echo "--- inspect ---"
logicpearl inspect "$ARTIFACT"
echo
echo "--- verify ---"
logicpearl artifact verify "$ARTIFACT"
