#!/bin/zsh
set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "$0")" && pwd)
ROOT=$(cd -- "$SCRIPT_DIR/.." && pwd)

usage() {
  /bin/cat <<'EOF'
Usage:
  zsh scripts/bootstrap-ai-delivery-project.sh --target-repo /path/to/repo [--project-id my-project] [--main-branch main]

Compatibility wrapper:
  Delegates to `go run ./cmd/ai-delivery init <target> --project-id ... --main-branch ...`
EOF
}

args=()
target_repo=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --target-repo)
      [[ $# -ge 2 ]] || {
        print -u2 -- "[bootstrap-ai-delivery-project] Missing value for --target-repo"
        exit 1
      }
      target_repo=$2
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      args+=("$1")
      shift
      ;;
  esac
done

if [[ -n "$target_repo" ]]; then
  args=("$target_repo" "${args[@]}")
fi

cd "$ROOT"
exec go run ./cmd/ai-delivery init "${args[@]}"
