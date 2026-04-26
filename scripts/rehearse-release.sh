#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
GOCACHE_DIR="${AI_DELIVERY_GOCACHE:-${ROOT}/.gocache}"
RUN_GORELEASER="${AI_DELIVERY_RUN_GORELEASER:-auto}"
RUN_PWSH="${AI_DELIVERY_RUN_PWSH:-auto}"

log() {
  printf '[release-rehearsal] %s\n' "$1"
}

run_step() {
  local label=$1
  shift

  log "START ${label}"
  "$@"
  log "PASS  ${label}"
}

maybe_run_goreleaser() {
  if [[ "$RUN_GORELEASER" == "never" ]]; then
    log "SKIP  goreleaser checks (AI_DELIVERY_RUN_GORELEASER=never)"
    return 0
  fi

  if ! command -v goreleaser >/dev/null 2>&1; then
    if [[ "$RUN_GORELEASER" == "always" ]]; then
      log "FAIL  goreleaser is required but not installed"
      return 1
    fi
    log "SKIP  goreleaser checks (binary not installed)"
    return 0
  fi

  run_step "goreleaser check" goreleaser check
  run_step "goreleaser snapshot" goreleaser release --snapshot --clean --skip=publish
}

maybe_run_pwsh() {
  if [[ "$RUN_PWSH" == "never" ]]; then
    log "SKIP  PowerShell syntax checks (AI_DELIVERY_RUN_PWSH=never)"
    return 0
  fi

  if ! command -v pwsh >/dev/null 2>&1; then
    if [[ "$RUN_PWSH" == "always" ]]; then
      log "FAIL  pwsh is required but not installed"
      return 1
    fi
    log "SKIP  PowerShell syntax checks (pwsh not installed)"
    return 0
  fi

  run_step "powershell syntax" pwsh -NoProfile -Command '$null = [System.Management.Automation.Language.Parser]::ParseFile("scripts/install-ai-delivery.ps1", [ref]$null, [ref]$null); $null = [System.Management.Automation.Language.Parser]::ParseFile("scripts/bootstrap-ai-delivery.ps1", [ref]$null, [ref]$null)'
}

main() {
  cd "$ROOT"

  run_step "go test ./..." env GOCACHE="$GOCACHE_DIR" go test ./...
  run_step "skill validator" zsh scripts/validate-project-ai-delivery-skills.sh
  run_step "legacy bootstrap contract" env GOCACHE="$GOCACHE_DIR" zsh tests/ai-delivery-skills/bootstrap-project.test.sh
  run_step "bootstrap smoke" bash tests/ai-delivery-cli/bootstrap-script.test.sh
  run_step "install smoke" bash tests/ai-delivery-cli/install-script.test.sh
  run_step "diff check" git diff --check
  maybe_run_pwsh
  maybe_run_goreleaser
}

main "$@"
