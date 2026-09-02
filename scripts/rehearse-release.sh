#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
GOCACHE_DIR="${AI_DELIVERY_GOCACHE:-${ROOT}/.gocache}"
RUN_GORELEASER="${AI_DELIVERY_RUN_GORELEASER:-auto}"
RUN_PWSH="${AI_DELIVERY_RUN_PWSH:-auto}"

log() {
  printf '[release-rehearsal] %s\n' "$1"
}

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    log "FAIL  missing required command: $1"
    return 1
  }
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
  run_step "powershell install smoke" pwsh -NoProfile -File tests/ai-delivery-cli/install-script-powershell.test.ps1
  run_step "powershell bootstrap smoke" pwsh -NoProfile -File tests/ai-delivery-cli/bootstrap-script-powershell.test.ps1
}

main() {
  cd "$ROOT"

  need_cmd zsh
  run_step "go test ./..." env GOCACHE="$GOCACHE_DIR" go test ./...
  run_step "skill validator" zsh scripts/validate-project-ai-delivery-skills.sh
  run_step "English source policy" bash tests/ai-delivery-skills/english-source-policy.test.sh
  run_step "artifact language policy" bash tests/ai-delivery-skills/artifact-language-policy.test.sh
  run_step "ui-truth-mapping skill markers" bash tests/ai-delivery-skills/ui-truth-mapping-skill-markers.test.sh
  run_step "change-scenario guidance markers" bash tests/ai-delivery-skills/change-scenario-guidance.test.sh
  run_step "orchestrator Stage 4 skill markers" bash tests/ai-delivery-skills/orchestrator-stage4-skill-markers.test.sh
  run_step "UI truth index v2 gate" bash tests/ai-delivery-skills/ui-truth-index-validator.test.sh
  run_step "structured visual acceptance gate" bash tests/ai-delivery-skills/visual-acceptance-validator.test.sh
  run_step "layout contract" bash tests/ai-delivery-skills/layout.test.sh
  run_step "artifact layout + drift" bash tests/ai-delivery-skills/artifact-layout.test.sh
  run_step "verification gate" bash tests/ai-delivery-skills/verification-gate.test.sh
  run_step "reconcile delivery" zsh tests/ai-delivery-skills/reconcile-delivery.test.sh
  run_step "archive immutability" bash tests/ai-delivery-skills/archive-immutability.test.sh
  run_step "delivery report language" bash tests/ai-delivery-skills/delivery-report-language.test.sh
  run_step "retrospective ledger and index" bash tests/ai-delivery-skills/retrospective-feature.test.sh
  run_step "zero-based flow fixture" zsh tests/ai-delivery-contracts/zero-based-flow.test.sh
  run_step "ui composition guardrails" bash tests/ai-delivery-skills/ui-composition-guardrails.test.sh
  run_step "human gate pressure" bash tests/ai-delivery-skills/human-gate-pressure.test.sh
  run_step "legacy bootstrap contract" env GOCACHE="$GOCACHE_DIR" zsh tests/ai-delivery-skills/bootstrap-project.test.sh
  run_step "bootstrap smoke" bash tests/ai-delivery-cli/bootstrap-script.test.sh
  run_step "install smoke" bash tests/ai-delivery-cli/install-script.test.sh
  run_step "diff check" git diff --check
  maybe_run_pwsh
  maybe_run_goreleaser
}

main "$@"
