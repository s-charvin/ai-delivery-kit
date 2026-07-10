#!/bin/bash
set -euo pipefail

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
    empty
  ' 2>/dev/null || true)
fi

if [[ -z "$file_path" || "$file_path" == "null" ]]; then
  file_path=$(printf '%s' "$input" | python3 -c '
import json
import sys

data = json.load(sys.stdin)
for key in ("file_path", "path", "filePath"):
    value = data.get(key)
    if isinstance(value, str) and value:
        print(value)
        raise SystemExit
for container_key in ("tool_input", "toolInput"):
    container = data.get(container_key)
    if isinstance(container, dict):
        for key in ("file_path", "path"):
            value = container.get(key)
            if isinstance(value, str) and value:
                print(value)
                raise SystemExit
' 2>/dev/null || true)
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

if [[ ! -f "$VALIDATOR" ]]; then
  printf '%s\n' '{"agent_message":"UI contract validator missing; cannot enforce contract gate."}'
  exit 2
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

escaped=$(printf '%s' "$OUTPUT" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))')
printf '{"agent_message":%s}\n' "$escaped"
exit 2
