#!/bin/zsh
set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "$0")" && pwd)

exec zsh "$SCRIPT_DIR/bootstrap-ai-delivery-project.sh" --mode sync "$@"
