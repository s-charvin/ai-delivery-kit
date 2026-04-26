#!/bin/zsh
set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "$0")" && pwd)
ROOT=$(cd -- "$SCRIPT_DIR/.." && pwd)

usage() {
  /bin/cat <<'EOF'
Usage:
  zsh scripts/bootstrap-ai-delivery-project.sh /path/to/repo

Compatibility wrapper:
  Delegates to `go run ./cmd/ai-delivery init <target>`
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

target_repo=${1:-}
if [[ -z "$target_repo" ]]; then
  print -u2 -- "[bootstrap-ai-delivery-project] Missing target repository path"
  usage
  exit 1
fi

cd "$ROOT"
exec go run ./cmd/ai-delivery init "$target_repo"
