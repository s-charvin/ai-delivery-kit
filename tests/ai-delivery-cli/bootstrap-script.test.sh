#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
ROOT=$(cd -- "$SCRIPT_DIR/../.." && pwd)
BOOTSTRAP_SCRIPT="$ROOT/scripts/bootstrap-ai-delivery.sh"

fail() {
  printf '[bootstrap-script-test] %s\n' "$1" >&2
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

TEMP_DIR=$(mktemp -d "${TMPDIR:-/tmp}/ai-delivery-bootstrap-script.XXXXXX")
TARGET_REPO="$TEMP_DIR/target repo"
LOCAL_LOG="$TEMP_DIR/local-command.log"
DOWNLOAD_LOG="$TEMP_DIR/download-command.log"
CURL_LOG="$TEMP_DIR/curl.log"
LOCAL_CMD="$TEMP_DIR/local-ai-delivery"
DOWNLOAD_CMD="$TEMP_DIR/ai-delivery"
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

mkdir -p "$TARGET_REPO"
mkdir -p "$STUB_DIR"

cat >"$LOCAL_CMD" <<EOF
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "\$*" >"$LOCAL_LOG"
EOF
chmod +x "$LOCAL_CMD"

AI_DELIVERY_CMD="$LOCAL_CMD" \
  bash "$BOOTSTRAP_SCRIPT" \
    "$TARGET_REPO"

assert_file_contains "$LOCAL_LOG" 'init'
assert_file_contains "$LOCAL_LOG" "$TARGET_REPO"
if grep -Fq -- '--project-id' "$LOCAL_LOG"; then
  fail "did not expect manual project id flags in bootstrap invocation"
fi
if grep -Fq -- '--main-branch' "$LOCAL_LOG"; then
  fail "did not expect manual main branch flags in bootstrap invocation"
fi

cat >"$DOWNLOAD_CMD" <<EOF
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "\$*" >"$DOWNLOAD_LOG"
EOF
chmod +x "$DOWNLOAD_CMD"

tar -C "$TEMP_DIR" -czf "$TEMP_DIR/$ARCHIVE_NAME" "$(basename "$DOWNLOAD_CMD")"
CHECKSUM=$(shasum -a 256 "$TEMP_DIR/$ARCHIVE_NAME" | awk '{print $1}')
cat >"$TEMP_DIR/checksums.txt" <<EOF
$CHECKSUM  $ARCHIVE_NAME
deadbeef  ai-delivery_linux_amd64.tar.gz
EOF

AI_DELIVERY_DOWNLOAD_BASE_URL="file://$TEMP_DIR" \
  AI_DELIVERY_VERSION="v9.9.9" \
  bash "$BOOTSTRAP_SCRIPT" \
    "$TARGET_REPO"

assert_file_contains "$DOWNLOAD_LOG" 'init'
assert_file_contains "$DOWNLOAD_LOG" "$TARGET_REPO"
if grep -Fq -- '--project-id' "$DOWNLOAD_LOG"; then
  fail "did not expect manual project id flags in downloaded bootstrap invocation"
fi
if grep -Fq -- '--main-branch' "$DOWNLOAD_LOG"; then
  fail "did not expect manual main branch flags in downloaded bootstrap invocation"
fi

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
  https://api.github.com/repos/example/private-repo/releases/tags/v0.0.1)
    cat >"\$output" <<JSON
{
  "assets": [
    { "id": 201, "node_id": "asset-201", "name": "$ARCHIVE_NAME" },
    { "id": 202, "node_id": "asset-202", "name": "checksums.txt" }
  ]
}
JSON
    ;;
  https://api.github.com/repos/example/private-repo/releases/assets/201)
    cp "$TEMP_DIR/$ARCHIVE_NAME" "\$output"
    ;;
  https://api.github.com/repos/example/private-repo/releases/assets/202)
    cp "$TEMP_DIR/checksums.txt" "\$output"
    ;;
  *)
    printf '%s\n' "unexpected curl url: \$url" >&2
    exit 1
    ;;
esac
EOF
chmod +x "$STUB_DIR/curl"
rm -f "$DOWNLOAD_LOG"

PATH="$STUB_DIR:$PATH" \
  GITHUB_TOKEN="test-token" \
  AI_DELIVERY_REPO="example/private-repo" \
  AI_DELIVERY_VERSION="v0.0.1" \
  bash "$BOOTSTRAP_SCRIPT" \
    "$TARGET_REPO"

assert_file_contains "$CURL_LOG" 'Authorization: Bearer test-token'
assert_file_contains "$CURL_LOG" 'Accept: application/octet-stream'
assert_file_contains "$CURL_LOG" 'https://api.github.com/repos/example/private-repo/releases/tags/v0.0.1'
assert_file_contains "$CURL_LOG" 'https://api.github.com/repos/example/private-repo/releases/assets/201'
assert_file_contains "$CURL_LOG" 'https://api.github.com/repos/example/private-repo/releases/assets/202'
assert_file_not_contains "$CURL_LOG" "https://github.com/example/private-repo/releases/download/v0.0.1/$ARCHIVE_NAME"
assert_file_contains "$DOWNLOAD_LOG" 'init'
assert_file_contains "$DOWNLOAD_LOG" "$TARGET_REPO"
