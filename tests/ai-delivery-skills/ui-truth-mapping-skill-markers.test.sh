#!/usr/bin/env bash
set -euo pipefail

# Guardrails for ui-truth-mapping skill wording that decision/authoring
# pressure tests rely on. If these markers regress, agents re-learn the
# whole-page-dump / get_code-then-prune failure modes.

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
EN="$ROOT/.agents/skills/ui-truth-mapping/SKILL.md"
ZH="$ROOT/.agents-zh/skills/ui-truth-mapping/SKILL-zh.md"

fail() { echo "FAIL: $*" >&2; exit 1; }

[[ -f "$EN" ]] || fail "Missing EN skill: $EN"
[[ -f "$ZH" ]] || fail "Missing ZH skill: $ZH"

require() {
  local file="$1" needle="$2" label="$3"
  grep -F -q -- "$needle" "$file" || fail "$label missing in $(basename "$file"): $needle"
}

# EN — scope / split / evidence authorship
require "$EN" "### 1b. Unit Split Plan (REQUIRED before any \`get_code\` or HTML)" "EN §1b"
require "$EN" "get_code target\` **must equal**" "EN get_code==source_node"
require "$EN" "Enumerate frames to classify — not to freeze" "EN enumerate≠freeze"
require "$EN" "Full-page \`get_code\` then prune" "EN anti prune"
require "$EN" "Skipping the §1b Unit Split Plan" "EN anti skip plan"
require "$EN" "Scoped \`get_code\` only" "EN hard boundary scoped get_code"
require "$EN" "script[data-ui-state-preview]" "EN preview script"
require "$EN" "data-ui-state-switcher" "EN state switcher"
require "$EN" "Quick Reference — Scenario → Unit split" "EN scenario table"
require "$EN" "create** \`component\` rooted at the badge" "EN red-dot create component"

# EN — rebuild-lifecycle gates (delivery target verification + pointer sweep)
require "$EN" "Do not write an unverified \`delivery.implemented.target\`" "EN unverified target ban"
require "$EN" "Reference check:** run a reference/usage search" "EN two-step target verification"
require "$EN" "### 9. Replace or deprecate — sweep stale pointers in the same change" "EN §9 pointer sweep"
require "$EN" "**Rebuild/split metadata rule:**" "EN rebuild inherited-delivery re-verification"

# EN — motion note split / consistency / coverage review
require "$EN" "Split a multi-clause SECTION note per unit" "EN split SECTION note per unit"
require "$EN" "Consistency check (REQUIRED before writing HTML)" "EN §2c consistency check"
require "$EN" "Coverage review after every prune (REQUIRED)" "EN §2c coverage review"

# Description must stay discovery-only (no procedure shortcut like "Auto-detects…")
if grep -E '^description:.*Auto-detects' "$EN" >/dev/null; then
  fail "EN description summarizes workflow (Auto-detects) — SDO violation"
fi

# ZH parity for the same gates
require "$ZH" "### 1b. 单元拆分计划" "ZH §1b"
require "$ZH" "枚举帧是为了分类 — 不是为了冻结" "ZH enumerate≠freeze"
require "$ZH" "整页 \`get_code\` 再裁剪" "ZH anti prune"
require "$ZH" "跳过 §1b 单元拆分计划" "ZH anti skip plan"
require "$ZH" "只对作用域调 \`get_code\`" "ZH hard boundary scoped get_code"
require "$ZH" "快速参考 — 场景 → 单元拆分" "ZH scenario table"

# ZH parity for the rebuild-lifecycle gates
require "$ZH" "不要写入未经核实的 \`delivery.implemented.target\`" "ZH unverified target ban"
require "$ZH" "引用核实：** 运行引用/使用搜索" "ZH two-step target verification"
require "$ZH" "### 9. 替换或废弃 — 同一次变更内清扫陈旧指针" "ZH §9 pointer sweep"
require "$ZH" "**重建/拆分的元数据规则：**" "ZH rebuild inherited-delivery re-verification"

# ZH parity for motion note split / consistency / coverage review
require "$ZH" "多条款 SECTION 备注按 unit 拆分" "ZH split SECTION note per unit"
require "$ZH" "一致性检查（写 HTML 前必做）" "ZH §2c consistency check"
require "$ZH" "每次裁剪后的覆盖复查（必做）" "ZH §2c coverage review"

# Template still ships hydrate + switcher + light preview base
TPL="$ROOT/.agents/skills/ui-truth-mapping/templates/ui-contract-template.html"
[[ -f "$TPL" ]] || fail "Missing template: $TPL"
require "$TPL" "data-ui-state-preview" "template preview script"
require "$TPL" "data-ui-state-switcher" "template switcher"
require "$TPL" "data-ui-state-host" "template host"
require "$TPL" "html, body" "template light html/body base"

echo "PASS: ui-truth-mapping skill markers"
