#!/usr/bin/env bash
set -euo pipefail

AI_DELIVERY_REPO="${AI_DELIVERY_REPO:-s-charvin/ai-delivery-kit}"
AI_DELIVERY_VERSION="${AI_DELIVERY_VERSION:-latest}"
AI_DELIVERY_INSTALL_DIR="${AI_DELIVERY_INSTALL_DIR:-${HOME}/.local/bin}"
AI_DELIVERY_DOWNLOAD_BASE_URL="${AI_DELIVERY_DOWNLOAD_BASE_URL:-}"
AI_DELIVERY_TEMP_DIR=""

usage() {
  cat <<'EOF'
Usage: install-ai-delivery.sh

Environment overrides:
  AI_DELIVERY_REPO              GitHub owner/repo. Default: s-charvin/ai-delivery-kit
  AI_DELIVERY_VERSION           Release tag or latest. Default: latest
  AI_DELIVERY_INSTALL_DIR       Install destination. Default: $HOME/.local/bin
  AI_DELIVERY_DOWNLOAD_BASE_URL Override release asset base URL for testing or mirrors
  GITHUB_TOKEN                  Optional GitHub token used for authenticated downloads
EOF
}

log() {
  printf '[install-ai-delivery] %s\n' "$1"
}

fail() {
  printf '[install-ai-delivery] %s\n' "$1" >&2
  exit 1
}

cleanup() {
  if [[ -n "$AI_DELIVERY_TEMP_DIR" && -d "$AI_DELIVERY_TEMP_DIR" ]]; then
    rm -rf "$AI_DELIVERY_TEMP_DIR"
  fi
}

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || fail "Missing required command: $1"
}

should_use_github_auth() {
  local url=$1

  [[ -n "${GITHUB_TOKEN:-}" ]] || return 1

  case "$url" in
    https://github.com/*|https://api.github.com/*)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

download_to() {
  local url=$1
  local output=$2
  shift 2
  local -a curl_args
  local -a wget_args

  curl_args=(-fsSL)
  wget_args=(-qO "$output")

  for header in "$@"; do
    curl_args+=(-H "$header")
    wget_args+=(--header="$header")
  done

  if should_use_github_auth "$url"; then
    curl_args+=(-H "Authorization: Bearer $GITHUB_TOKEN")
    wget_args+=(--header="Authorization: Bearer $GITHUB_TOKEN")
  fi

  curl_args+=("$url" -o "$output")
  wget_args+=("$url")

  if command -v curl >/dev/null 2>&1; then
    curl "${curl_args[@]}"
    return 0
  fi

  if command -v wget >/dev/null 2>&1; then
    wget "${wget_args[@]}"
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

github_api_base_url() {
  printf 'https://api.github.com/repos/%s\n' "$AI_DELIVERY_REPO"
}

github_release_api_url() {
  local api_base

  api_base=$(github_api_base_url)
  if [[ "$AI_DELIVERY_VERSION" == "latest" ]]; then
    printf '%s/releases/latest\n' "$api_base"
    return 0
  fi

  printf '%s/releases/tags/%s\n' "$api_base" "$AI_DELIVERY_VERSION"
}

release_source_description() {
  if [[ -n "$AI_DELIVERY_DOWNLOAD_BASE_URL" ]]; then
    printf '%s\n' "$AI_DELIVERY_DOWNLOAD_BASE_URL"
    return 0
  fi

  if [[ -n "${GITHUB_TOKEN:-}" ]]; then
    printf 'GitHub Releases API for %s (%s)\n' "$AI_DELIVERY_REPO" "$AI_DELIVERY_VERSION"
    return 0
  fi

  release_base_url
}

escape_sed_regex() {
  printf '%s' "$1" | sed 's/[][\/.^$*]/\\&/g'
}

release_metadata_path() {
  printf '%s/release.json\n' "$AI_DELIVERY_TEMP_DIR"
}

find_github_release_asset_id() {
  local metadata_path=$1
  local asset_name=$2
  local escaped_name
  local release_json

  escaped_name=$(escape_sed_regex "$asset_name")
  release_json=$(tr -d '\r\n' <"$metadata_path")

  printf '%s\n' "$release_json" | sed -n "s/.*\"id\":[[:space:]]*\([0-9][0-9]*\)[[:space:]]*,[[:space:]]*\"node_id\":[[:space:]]*\"[^\"]*\"[[:space:]]*,[[:space:]]*\"name\":[[:space:]]*\"$escaped_name\".*/\1/p"
}

download_github_release_metadata() {
  local metadata_path=$1

  [[ -f "$metadata_path" ]] && return 0
  download_to "$(github_release_api_url)" "$metadata_path" 'Accept: application/vnd.github+json'
}

download_github_release_asset() {
  local asset_name=$1
  local output=$2
  local metadata_path
  local asset_id

  metadata_path=$(release_metadata_path)
  download_github_release_metadata "$metadata_path"
  asset_id=$(find_github_release_asset_id "$metadata_path" "$asset_name")
  [[ -n "$asset_id" ]] || fail "Could not find release asset $asset_name for $AI_DELIVERY_REPO@$AI_DELIVERY_VERSION"

  download_to "$(github_api_base_url)/releases/assets/$asset_id" "$output" 'Accept: application/octet-stream'
}

download_release_asset() {
  local asset_name=$1
  local output=$2

  if [[ -n "$AI_DELIVERY_DOWNLOAD_BASE_URL" ]]; then
    download_to "$AI_DELIVERY_DOWNLOAD_BASE_URL/$asset_name" "$output"
    return 0
  fi

  if [[ -n "${GITHUB_TOKEN:-}" ]]; then
    download_github_release_asset "$asset_name" "$output"
    return 0
  fi

  download_to "$(release_base_url)/$asset_name" "$output"
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

  log "Verifying checksum for $archive_name"
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

main() {
  local os arch archive_name source_desc archive_path checksums_path extracted_dir binary_path target_path

  if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
    usage
    exit 0
  fi

  need_cmd tar
  os=$(detect_os)
  arch=$(detect_arch)
  archive_name="ai-delivery_${os}_${arch}.tar.gz"
  source_desc=$(release_source_description)
  AI_DELIVERY_TEMP_DIR=$(mktemp -d "${TMPDIR:-/tmp}/ai-delivery-install.XXXXXX")
  archive_path="$AI_DELIVERY_TEMP_DIR/$archive_name"
  checksums_path="$AI_DELIVERY_TEMP_DIR/checksums.txt"
  extracted_dir="$AI_DELIVERY_TEMP_DIR/extracted"
  target_path="$AI_DELIVERY_INSTALL_DIR/ai-delivery"

  trap cleanup EXIT

  mkdir -p "$AI_DELIVERY_INSTALL_DIR" "$extracted_dir"

  log "Downloading ${archive_name} from ${source_desc}"
  download_release_asset "$archive_name" "$archive_path"

  if download_release_asset "checksums.txt" "$checksums_path"; then
    verify_checksum "$archive_path" "$checksums_path"
  else
    log "Could not download checksums.txt; continuing without checksum verification."
  fi

  tar -xzf "$archive_path" -C "$extracted_dir"
  binary_path=$(find "$extracted_dir" -type f -name 'ai-delivery' | head -n 1)
  [[ -n "$binary_path" ]] || fail "Extracted archive did not contain ai-delivery"

  install -m 0755 "$binary_path" "$target_path"

  log "Installed ai-delivery to $target_path"
  log "Add $AI_DELIVERY_INSTALL_DIR to PATH if it is not already available:"
  log "  export PATH=\"$AI_DELIVERY_INSTALL_DIR:\$PATH\""
  log "Run: ai-delivery init /path/to/repo"
}

main "$@"
