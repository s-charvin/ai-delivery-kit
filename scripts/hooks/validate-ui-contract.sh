#!/bin/bash
# Shared UI acceptance contract gate for Cursor / Claude / Codex hooks.
# Reads hook JSON from stdin. Skips non-contract files.
# Failure feedback:
#   - Cursor afterFileEdit: agent_message JSON + exit 2
#   - Claude/Codex PostToolUse: hookSpecificOutput.additionalContext + exit 0

set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
input=$(cat)
file_path=""

if command -v jq >/dev/null 2>&1; then
  file_path=$(printf '%s' "$input" | jq -r '
    .file_path //
    .path //
    .filePath //
    .tool_input.file_path //
    .tool_input.path //
    .toolInput.file_path //
    .toolInput.path //
    .tool_response.file_path //
    .tool_response.path //
    empty
  ' 2>/dev/null || true)
fi

if [[ -z "$file_path" || "$file_path" == "null" ]]; then
  file_path=$(printf '%s' "$input" | python3 "$SCRIPT_DIR/extract-hook-path.py" 2>/dev/null || true)
fi

if [[ -z "$file_path" || "$file_path" == "null" ]]; then
  exit 0
fi

case "$file_path" in
  *ui-acceptance-contract.yaml) ;;
  *) exit 0 ;;
esac

ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
VALIDATOR="$ROOT/scripts/validate-ui-contract.py"
if [[ ! -f "$VALIDATOR" ]]; then
  VALIDATOR="$ROOT/.ai-delivery/scripts/validate-ui-contract.py"
fi

emit_failure() {
  local msg=$1
  printf '%s\n' "$msg" >&2
  local escaped
  escaped=$(printf '%s' "$msg" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))')

  # Cursor afterFileEdit: file_path + edits, no tool_name/tool_input.
  if printf '%s' "$input" | python3 -c '
import json, sys
try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(1)
if not isinstance(data, dict):
    sys.exit(1)
if isinstance(data.get("edits"), list):
    sys.exit(0)
if data.get("file_path") and "tool_name" not in data and "tool_input" not in data and "toolInput" not in data:
    sys.exit(0)
sys.exit(1)
' 2>/dev/null; then
    printf '{"agent_message":%s}\n' "$escaped"
    exit 2
  fi

  # Claude Code / Codex PostToolUse: official additionalContext, exit 0.
  printf '{"hookSpecificOutput":{"hookEventName":"PostToolUse","additionalContext":%s}}\n' "$escaped"
  exit 0
}

if [[ ! -f "$VALIDATOR" ]]; then
  emit_failure "UI contract validator missing; cannot enforce contract gate."
fi

python3 -c 'import yaml' 2>/dev/null || python3 -m pip install pyyaml -q 2>/dev/null || true

CONTRACT_PATH="$file_path"
if [[ "$CONTRACT_PATH" != /* ]]; then
  CONTRACT_PATH="$ROOT/$CONTRACT_PATH"
fi

SECTION_MAP=""
if [[ -f "$(dirname "$CONTRACT_PATH")/section-map.json" ]]; then
  SECTION_MAP="$(dirname "$CONTRACT_PATH")/section-map.json"
fi

STATUS=0
if [[ -n "$SECTION_MAP" ]]; then
  OUTPUT=$(python3 "$VALIDATOR" "$CONTRACT_PATH" --section-map "$SECTION_MAP" 2>&1) || STATUS=$?
else
  OUTPUT=$(python3 "$VALIDATOR" "$CONTRACT_PATH" 2>&1) || STATUS=$?
fi

if [[ "$STATUS" -eq 0 ]]; then
  exit 0
fi

emit_failure "$OUTPUT"
