#!/bin/zsh
set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "$0")" && pwd)
ROOT=$(git -C "$SCRIPT_DIR/../.." rev-parse --show-toplevel)
SUBREQ="$ROOT/.ai-delivery/requirements/im-contacts-and-add-friends/sub-requirements/contacts-directory"
SAMPLE_TODO_FILE="$ROOT/.ai-delivery/requirements/im-contacts-and-add-friends/todo.md"

[[ -f "$SUBREQ/ui-acceptance-contract.md" ]] || { echo "missing ui-acceptance-contract.md"; exit 1; }
[[ -f "$SUBREQ/delivery-slices/index.json" ]] || { echo "missing delivery-slices/index.json"; exit 1; }
grep -Fq '"status": "slices_ready"' "$SUBREQ/status.json" || { echo "status.json not migrated"; exit 1; }
grep -Fq '"ui_acceptance_contract"' "$SUBREQ/traceability.json" || { echo "traceability missing ui_acceptance_contract"; exit 1; }
grep -Fq 'Action Side Effects Matrix' "$SUBREQ/api-contract-mapping.md" || { echo "api mapping missing side effects matrix"; exit 1; }
grep -Fq 'Executable Screen States' "$SUBREQ/figma-mapping.md" || { echo "figma mapping missing executable states"; exit 1; }
grep -Fq 'Action Chain Matrix' "$SUBREQ/interaction-design.md" || { echo "interaction design missing action chain matrix"; exit 1; }
[[ -f "$SAMPLE_TODO_FILE" ]] || { echo "missing requirement todo.md"; exit 1; }
grep -Fq 'source_of_truth: .ai-delivery' "$SAMPLE_TODO_FILE" || { echo "todo missing source_of_truth"; exit 1; }
grep -Fq 'CP-001 | checkpoint=tasks_ready_user_confirmation' "$SAMPLE_TODO_FILE" || { echo "todo missing CP-001"; exit 1; }
grep -Fq 'CP-002 | checkpoint=hard_blocker_pause' "$SAMPLE_TODO_FILE" || { echo "todo missing CP-002"; exit 1; }
grep -Fq 'stage=prepare-speckit-context | scope=slice:contacts-friends-idle' "$SAMPLE_TODO_FILE" || { echo "todo missing contacts-friends-idle bridge step"; exit 1; }
grep -Fq 'stage=speckit-plan-bind | scope=slice:contacts-friends-idle' "$SAMPLE_TODO_FILE" || { echo "todo missing contacts-friends-idle plan bind step"; exit 1; }
grep -Fq 'stage=speckit-tasks-bind | scope=slice:contacts-friends-idle' "$SAMPLE_TODO_FILE" || { echo "todo missing contacts-friends-idle tasks bind step"; exit 1; }
grep -Fq 'spec-kit-input.md' "$SAMPLE_TODO_FILE" || { echo "todo missing spec-kit-input bridge artifact"; exit 1; }
grep -Fq 'status.json:tasks_ready' "$SAMPLE_TODO_FILE" || { echo "todo missing tasks_ready guard"; exit 1; }
if grep -Fq 'todo.json' "$SAMPLE_TODO_FILE"; then
  echo "todo should not reference todo.json"
  exit 1
fi
