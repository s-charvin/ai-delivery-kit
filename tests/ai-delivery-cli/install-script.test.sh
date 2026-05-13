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

assert_file_not_contains() {
  local file=$1
  local needle=$2

  if grep -Fq -- "$needle" "$file"; then
    fail "did not expect '$needle' in $file"
  fi
}

TEMP_DIR=$(mktemp -d "${TMPDIR:-/tmp}/ai-delivery-install-script.XXXXXX")
INSTALL_DIR="$TEMP_DIR/bin"
STUB_BIN="$TEMP_DIR/ai-delivery"
OUTPUT_LOG="$TEMP_DIR/install-output.log"
CURL_LOG="$TEMP_DIR/curl.log"
STUB_DIR="$TEMP_DIR/stubs"

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
mkdir -p "$STUB_DIR"

cat >"$STUB_BIN" <<EOF
#!/usr/bin/env bash
set -euo pipefail
if [[ \$# -eq 0 ]]; then
  printf '%s\n' "installed-stub" >"$OUTPUT_LOG"
else
  printf '%s\n' "\$*" >"$OUTPUT_LOG"
fi
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
  AI_DELIVERY_SKIP_SKILLS="1" \
  bash "$INSTALL_SCRIPT"

[[ -x "$INSTALL_DIR/ai-delivery" ]] || fail "expected installed ai-delivery binary"
"$INSTALL_DIR/ai-delivery"
assert_file_contains "$OUTPUT_LOG" 'installed-stub'

cat >"$STUB_DIR/curl" <<EOF
#!/usr/bin/env bash
set -euo pipefail

printf '%s\n' "\$*" >>"$CURL_LOG"

output=""
url=""
expect_output=0
for arg in "\$@"; do
  if [[ \$expect_output -eq 1 ]]; then
    output=\$arg
    expect_output=0
    continue
  fi

  case "\$arg" in
    -o)
      expect_output=1
      ;;
    http://*|https://*|file://*)
      url=\$arg
      ;;
  esac
done

[[ -n "\$output" ]] || {
  printf '%s\n' "curl stub missing output path" >&2
  exit 1
}
[[ -n "\$url" ]] || {
  printf '%s\n' "curl stub missing url" >&2
  exit 1
}

case "\$url" in
  https://api.github.com/repos/example/private-repo/releases/latest)
    cat >"\$output" <<JSON
{
  "assets": [
    { "id": 101, "node_id": "asset-101", "name": "$ARCHIVE_NAME" },
    { "id": 102, "node_id": "asset-102", "name": "checksums.txt" }
  ]
}
JSON
    ;;
  https://api.github.com/repos/example/private-repo/releases/assets/101)
    cp "$TEMP_DIR/$ARCHIVE_NAME" "\$output"
    ;;
  https://api.github.com/repos/example/private-repo/releases/assets/102)
    cp "$TEMP_DIR/checksums.txt" "\$output"
    ;;
  *)
    printf '%s\n' "unexpected curl url: \$url" >&2
    exit 1
    ;;
esac
EOF
chmod +x "$STUB_DIR/curl"

AUTH_INSTALL_DIR="$TEMP_DIR/auth-bin"
mkdir -p "$AUTH_INSTALL_DIR"

PATH="$STUB_DIR:$PATH" \
  GITHUB_TOKEN="test-token" \
  AI_DELIVERY_INSTALL_DIR="$AUTH_INSTALL_DIR" \
  AI_DELIVERY_REPO="example/private-repo" \
  AI_DELIVERY_VERSION="latest" \
  AI_DELIVERY_SKIP_SKILLS="1" \
  bash "$INSTALL_SCRIPT"

assert_file_contains "$CURL_LOG" 'Authorization: Bearer test-token'
assert_file_contains "$CURL_LOG" 'Accept: application/octet-stream'
assert_file_contains "$CURL_LOG" 'https://api.github.com/repos/example/private-repo/releases/latest'
assert_file_contains "$CURL_LOG" 'https://api.github.com/repos/example/private-repo/releases/assets/101'
assert_file_contains "$CURL_LOG" 'https://api.github.com/repos/example/private-repo/releases/assets/102'
assert_file_not_contains "$CURL_LOG" "https://github.com/example/private-repo/releases/latest/download/$ARCHIVE_NAME"

UPGRADE_INSTALL_DIR="$TEMP_DIR/upgrade-bin"
mkdir -p "$UPGRADE_INSTALL_DIR"

bash "$INSTALL_SCRIPT" \
  --install-dir "$UPGRADE_INSTALL_DIR" \
  --download-base-url "file://$TEMP_DIR" \
  --version "v9.9.9" \
  --upgrade-init /tmp/managed-repo \
  --skip-skills

assert_file_contains "$OUTPUT_LOG" 'init --upgrade /tmp/managed-repo'
