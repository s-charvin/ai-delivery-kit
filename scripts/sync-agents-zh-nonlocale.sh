#!/bin/zsh
# Sync non-localized assets from .agents/skills to .agents-zh/skills.
# Language-specific files (SKILL.md, *-zh.md templates, translated references) are maintained separately.

set -euo pipefail

ROOT=$(cd -- "$(dirname -- "$0")/.." && pwd)
SRC="$ROOT/.agents/skills"
DST="$ROOT/.agents-zh/skills"

copy_identical() {
  local rel=$1
  local from="$SRC/$rel"
  local to="$DST/$rel"
  [[ -f "$from" ]] || { print -u2 "missing source: $from"; return 1 }
  mkdir -p "$(dirname -- "$to")"
  cp "$from" "$to"
}

for skill in ai-delivery-orchestrator requirement-breakdown ui-truth-mapping; do
  copy_identical "$skill/agents/openai.yaml"
done

copy_identical "ai-delivery-orchestrator/scripts/reconcile-delivery.py"
copy_identical "ai-delivery-orchestrator/templates/status-template.json"
copy_identical "ui-truth-mapping/templates/section-map-template.json"
cp -R "$SRC/ui-truth-mapping/fixtures" "$DST/ui-truth-mapping/"

print -- "Synced non-localized assets to .agents-zh/skills"
