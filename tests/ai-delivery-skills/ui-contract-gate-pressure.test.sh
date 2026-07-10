#!/bin/zsh
set -euo pipefail

# Pressure scenario: agent under delivery time pressure must not accept summary YAML.
# This test encodes the failure mode as mechanical rejection, not agent behavior replay.

SCRIPT_DIR=$(cd -- "$(dirname -- "$0")" && pwd)
ROOT=$(cd -- "$SCRIPT_DIR/../.." && pwd)
VALIDATOR="$ROOT/scripts/validate-ui-contract.py"
BAD="$ROOT/.agents/skills/ui-truth-mapping/fixtures/ui-acceptance-contract-bad.yaml"

fail() {
  print -u2 -- "[ui-contract-gate-pressure] $1"
  exit 1
}

[[ -f "$VALIDATOR" ]] || fail "Missing validator"
[[ -f "$BAD" ]] || fail "Missing bad fixture"

python3 -c 'import yaml' 2>/dev/null || python3 -m pip install pyyaml -q || pip3 install pyyaml -q

OUTPUT=$(python3 "$VALIDATOR" "$BAD" 2>&1 || true)

for needle in "code-baseline" "layout_note" "visual_truth" "regions must not be empty"; do
  [[ "$OUTPUT" == *"$needle"* ]] || fail "Expected pressure fixture rejection to mention: $needle"
done

print -- 'PASS: pressure fixture (summary YAML + code-baseline bypass) is mechanically rejected.'
