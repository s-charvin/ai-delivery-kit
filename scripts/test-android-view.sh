#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd -- "$(dirname -- "$0")/.." && pwd)
: "${ANDROID_HOME:=${ANDROID_SDK_ROOT:-}}"
[[ -n "$ANDROID_HOME" && -d "$ANDROID_HOME/platforms/android-36" ]] || {
  echo 'Android SDK platform 36 is required; set ANDROID_HOME.' >&2
  exit 1
}
export ANDROID_HOME
cd "$ROOT/tests/fixtures/android-view"
./gradlew --no-daemon :app:testDebugUnitTest :app:lintDebug --console=plain "$@"
