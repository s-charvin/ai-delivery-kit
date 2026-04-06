#!/bin/zsh
set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "$0")" && pwd)

if ROOT=$(git -C "$SCRIPT_DIR/../.." rev-parse --show-toplevel 2>/dev/null); then
  :
else
  ROOT=$(cd -- "$SCRIPT_DIR/../.." && pwd)
fi

resolve_project_asset_path() {
  local relative_path=$1
  local candidate

  for candidate in "$ROOT/$relative_path" "$ROOT/.ai-delivery/$relative_path"; do
    if [[ -f "$candidate" ]]; then
      print -- "$candidate"
      return 0
    fi
  done

  print -u2 -- "[validate-sources-test] Missing managed asset: $relative_path"
  exit 1
}

VALIDATE_SCRIPT=$(resolve_project_asset_path "scripts/validate-project-ai-delivery-skills.sh")

zsh "$VALIDATE_SCRIPT"
