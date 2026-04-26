#!/usr/bin/env bash
set -euo pipefail

AI_DELIVERY_REPO="${AI_DELIVERY_REPO:-s-charvin/ai-delivery-kit}"
AI_DELIVERY_VERSION="${AI_DELIVERY_VERSION:-latest}"
AI_DELIVERY_DOWNLOAD_BASE_URL="${AI_DELIVERY_DOWNLOAD_BASE_URL:-}"
AI_DELIVERY_CMD="${AI_DELIVERY_CMD:-}"
AI_DELIVERY_TEMP_DIR=""

usage() {
  cat <<'EOF'
Usage: bootstrap-ai-delivery.sh /path/to/repo [--project-id my-project] [--main-branch main]

Environment overrides:
  AI_DELIVERY_CMD               Local ai-delivery executable for tests and development
  AI_DELIVERY_REPO              GitHub owner/repo. Default: s-charvin/ai-delivery-kit
  AI_DELIVERY_VERSION           Release tag or latest. Default: latest
  AI_DELIVERY_DOWNLOAD_BASE_URL Override release asset base URL for testing or mirrors
EOF
}

log() {
  printf '[bootstrap-ai-delivery] %s\n' "$1"
}

fail() {
  printf '[bootstrap-ai-delivery] %s\n' "$1" >&2
  exit 1
}

cleanup() {
  if [[ -n "$AI_DELIVERY_TEMP_DIR" && -d "$AI_DELIVERY_TEMP_DIR" ]]; then
    rm -rf "$AI_DELIVERY_TEMP_DIR"
  fi
}

download_to() {
  local url=$1
  local output=$2

  if command -v curl >/dev/null 2>&1; then
    curl -fsSL "$url" -o "$output"
    return 0
  fi

  if command -v wget >/dev/null 2>&1; then
    wget -qO "$output" "$url"
    return 0
  fi

  fail "Missing required downloader: curl or wget"
}

detect_os() {
  local os
  os=$(uname -s | tr '[:upper:]' '[:lower:]')
  case "$os" in
    darwin|linux)
      printf '%s\n' "$os"
      ;;
    *)
      fail "Unsupported OS: $os"
      ;;
  esac
}

detect_arch() {
  local arch
  arch=$(uname -m)
  case "$arch" in
    x86_64|amd64)
      printf 'amd64\n'
      ;;
    arm64|aarch64)
      printf 'arm64\n'
      ;;
    *)
      fail "Unsupported architecture: $arch"
      ;;
  esac
}

release_base_url() {
  if [[ -n "$AI_DELIVERY_DOWNLOAD_BASE_URL" ]]; then
    printf '%s\n' "$AI_DELIVERY_DOWNLOAD_BASE_URL"
    return 0
  fi

  if [[ "$AI_DELIVERY_VERSION" == "latest" ]]; then
    printf 'https://github.com/%s/releases/latest/download\n' "$AI_DELIVERY_REPO"
    return 0
  fi

  printf 'https://github.com/%s/releases/download/%s\n' "$AI_DELIVERY_REPO" "$AI_DELIVERY_VERSION"
}

checksum_tool() {
  if command -v shasum >/dev/null 2>&1; then
    printf 'shasum\n'
    return 0
  fi

  if command -v sha256sum >/dev/null 2>&1; then
    printf 'sha256sum\n'
    return 0
  fi

  printf '\n'
}

verify_checksum() {
  local archive_path=$1
  local checksums_path=$2
  local archive_name
  local expected_line
  local tool
  local verify_file

  archive_name=$(basename "$archive_path")
  expected_line=$(grep -F "  $archive_name" "$checksums_path" || true)
  if [[ -z "$expected_line" ]]; then
    log "No checksum entry found for $archive_name; skipping verification."
    return 0
  fi

  tool=$(checksum_tool)
  if [[ -z "$tool" ]]; then
    log "No sha256 tool found; skipping checksum verification."
    return 0
  fi

  verify_file=$(mktemp "${AI_DELIVERY_TEMP_DIR:-${TMPDIR:-/tmp}}/ai-delivery-checksum.XXXXXX")
  printf '%s\n' "$expected_line" >"$verify_file"
  (
    cd -- "$(dirname "$archive_path")"
    case "$tool" in
      shasum)
        shasum -a 256 -c "$verify_file" >/dev/null
        ;;
      sha256sum)
        sha256sum -c "$verify_file" >/dev/null
        ;;
    esac
  ) || {
    rm -f "$verify_file"
    fail "Checksum verification failed for $archive_name"
  }
  rm -f "$verify_file"
}

run_ai_delivery() {
  local ai_delivery_cmd=$1
  local target_repo=$2
  local project_id=$3
  local main_branch=$4

  "$ai_delivery_cmd" init "$target_repo" --project-id "$project_id" --main-branch "$main_branch"
}

main() {
  local target_repo="" project_id="" main_branch="main"
  local os arch archive_name base_url temp_dir archive_path checksums_path extracted_dir binary_path

  if [[ $# -eq 0 ]]; then
    fail "You must provide a target repository path."
  fi

  case "${1:-}" in
    -h|--help)
      usage
      exit 0
      ;;
  esac

  target_repo=$1
  shift

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --project-id)
        [[ $# -ge 2 ]] || fail "Missing value for --project-id"
        project_id=$2
        shift 2
        ;;
      --main-branch)
        [[ $# -ge 2 ]] || fail "Missing value for --main-branch"
        main_branch=$2
        shift 2
        ;;
      -h|--help)
        usage
        exit 0
        ;;
      *)
        fail "Unknown argument: $1"
        ;;
    esac
  done

  [[ -n "$target_repo" ]] || fail "You must provide a target repository path."
  [[ -d "$target_repo" ]] || fail "Target repository directory does not exist: $target_repo"

  if [[ -n "$AI_DELIVERY_CMD" ]]; then
    log "Using local ai-delivery command override"
    run_ai_delivery "$AI_DELIVERY_CMD" "$target_repo" "$project_id" "$main_branch"
    exit 0
  fi

  os=$(detect_os)
  arch=$(detect_arch)
  archive_name="ai-delivery_${os}_${arch}.tar.gz"
  base_url=$(release_base_url)
  AI_DELIVERY_TEMP_DIR=$(mktemp -d "${TMPDIR:-/tmp}/ai-delivery-bootstrap.XXXXXX")
  archive_path="$AI_DELIVERY_TEMP_DIR/$archive_name"
  checksums_path="$AI_DELIVERY_TEMP_DIR/checksums.txt"
  extracted_dir="$AI_DELIVERY_TEMP_DIR/extracted"

  trap cleanup EXIT

  mkdir -p "$extracted_dir"

  log "Downloading temporary ai-delivery binary from ${base_url}"
  download_to "$base_url/$archive_name" "$archive_path"

  if download_to "$base_url/checksums.txt" "$checksums_path"; then
    verify_checksum "$archive_path" "$checksums_path"
  else
    log "Could not download checksums.txt; continuing without checksum verification."
  fi

  tar -xzf "$archive_path" -C "$extracted_dir"
  binary_path=$(find "$extracted_dir" -type f -name 'ai-delivery' | head -n 1)
  [[ -n "$binary_path" ]] || fail "Extracted archive did not contain ai-delivery"
  chmod +x "$binary_path"

  run_ai_delivery "$binary_path" "$target_repo" "$project_id" "$main_branch"
}

main "$@"
