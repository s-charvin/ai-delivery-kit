#!/bin/zsh
set -euo pipefail
ROOT=$(git rev-parse --show-toplevel)
zsh "$ROOT/scripts/validate-project-ai-delivery-skills.sh"
