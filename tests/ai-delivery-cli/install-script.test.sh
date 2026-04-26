#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
ROOT=$(cd -- "$SCRIPT_DIR/../.." && pwd)
INSTALL_SCRIPT="$ROOT/scripts/install-ai-delivery.sh"

fail() {
  printf '[install-script-test] %s\n' "$1" >&2
  exit 1
}

assert_file_contains() {
  local file=$1
  local needle=$2

  grep -Fq -- "$needle" "$file" || fail "expected '$needle' in $file"
}

TEMP_DIR=$(mktemp -d "${TMPDIR:-/tmp}/ai-delivery-install-script.XXXXXX")
INSTALL_DIR="$TEMP_DIR/bin"
STUB_BIN="$TEMP_DIR/ai-delivery"
OUTPUT_LOG="$TEMP_DIR/install-output.log"

OS=$(uname -s | tr '[:upper:]' '[:lower:]')
ARCH=$(uname -m)
case "$ARCH" in
  x86_64|amd64)
    ARCH="amd64"
    ;;
  arm64|aarch64)
    ARCH="arm64"
    ;;
  *)
    fail "unsupported test architecture: $ARCH"
    ;;
esac

ARCHIVE_NAME="ai-delivery_${OS}_${ARCH}.tar.gz"

cleanup() {
  rm -rf "$TEMP_DIR"
}

trap cleanup EXIT

mkdir -p "$INSTALL_DIR"

cat >"$STUB_BIN" <<EOF
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "installed-stub" >"$OUTPUT_LOG"
EOF
chmod +x "$STUB_BIN"

tar -C "$TEMP_DIR" -czf "$TEMP_DIR/$ARCHIVE_NAME" "$(basename "$STUB_BIN")"
CHECKSUM=$(shasum -a 256 "$TEMP_DIR/$ARCHIVE_NAME" | awk '{print $1}')
cat >"$TEMP_DIR/checksums.txt" <<EOF
$CHECKSUM  $ARCHIVE_NAME
deadbeef  ai-delivery_linux_amd64.tar.gz
EOF

AI_DELIVERY_INSTALL_DIR="$INSTALL_DIR" \
  AI_DELIVERY_DOWNLOAD_BASE_URL="file://$TEMP_DIR" \
  AI_DELIVERY_VERSION="v9.9.9" \
  bash "$INSTALL_SCRIPT"

[[ -x "$INSTALL_DIR/ai-delivery" ]] || fail "expected installed ai-delivery binary"
"$INSTALL_DIR/ai-delivery"
assert_file_contains "$OUTPUT_LOG" 'installed-stub'
