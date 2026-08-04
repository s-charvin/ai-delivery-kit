#!/bin/zsh
set -euo pipefail

# Pressure scenario: agent under delivery time pressure must not be able to
# shortcut the HTML UI contract gate by claiming a delivered status without
# the evidence the validator requires. This test encodes the failure mode as
# mechanical rejection, not agent behavior replay.

SCRIPT_DIR=$(cd -- "$(dirname -- "$0")" && pwd)

if ROOT=$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null); then
  :
else
  ROOT=$(cd -- "$SCRIPT_DIR/../.." && pwd)
fi

if [[ -f "$ROOT/managedassets.go" ]]; then
  VALIDATOR="$ROOT/scripts/validate-ui-contract-html.py"
else
  VALIDATOR="$ROOT/.ai-delivery/scripts/validate-ui-contract-html.py"
fi

fail() {
  print -u2 -- "[ui-contract-gate-pressure] $1"
  exit 1
}

[[ -f "$VALIDATOR" ]] || fail "Missing validator"

TMP_DIR=$(mktemp -d "${TMPDIR:-/tmp}/ui-contract-gate-pressure.XXXXXX")
trap 'rm -rf "$TMP_DIR"' EXIT

BAD="$TMP_DIR/ui-contract-pressure-bad.html"

# Shortcut attempt: claim delivery.status "implemented" without the required
# delivery.implemented object, and mark an element data-evidence="inferred"
# without a matching review-panel note.
cat > "$BAD" <<'EOF'
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>UI Contract: pressure-fixture</title>
  <script type="application/json" id="ui-contract-meta">
  {
    "schema_version": 2,
    "contract_id": "pressure-fixture",
    "source": {
      "requirement": "requirement-slice.md",
      "design_file": "fixture-file-key",
      "root_node": "1:100"
    },
    "unit": {
      "id": "pressure-page",
      "type": "page",
      "title": "Pressure Page",
      "route_or_trigger": "/pressure",
      "requirements": ["fixture-subreq-1"],
      "source_node": "1:200",
      "dependencies": []
    },
    "states": [
      { "id": "idle", "source_node": "1:200", "default": true }
    ],
    "revision": 1,
    "delivery": {
      "status": "implemented"
    }
  }
  </script>
  <style>
    [data-ui-contract] { min-height: 100vh; }
  </style>
</head>
<body>
  <main data-ui-contract data-ui-unit-id="pressure-page" data-ui-unit-type="page" data-ui-state-default="idle">
    <div data-ui-id="pressure-summary" data-ui-kind="text" data-figma-node="1:201" data-evidence="inferred">
      Shipped under deadline pressure, evidence to follow.
    </div>
  </main>
</body>
</html>
EOF

OUTPUT=$(python3 "$VALIDATOR" "$BAD" 2>&1 || true)

for needle in \
  'delivery.implemented is required' \
  'has data-evidence="inferred" but no evidence' \
  ; do
  [[ "$OUTPUT" == *"$needle"* ]] || fail "Expected pressure fixture rejection to mention: $needle"
done

print -- 'PASS: pressure fixture (delivered status + unbacked inferred evidence) is mechanically rejected.'
