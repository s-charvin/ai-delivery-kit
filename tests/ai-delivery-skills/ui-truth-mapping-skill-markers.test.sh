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
require "$EN" "User-named reference implementation" "EN user-named reference"

# EN — layout sizing (fill vs hug vs fixed). YAML-era L3 was dropped in HTML v2;
# agents then copied get_code pixel widths into runtime constants.
require "$EN" "### 5b. Layout sizing classification (REQUIRED after mechanical transfer)" "EN §5b"
require "$EN" "fill detection rule" "EN fill detection rule"
require "$EN" "parent width minus symmetrical horizontal inset" "EN fill = parent − inset"
require "$EN" "data-ui-sizing=\"fill|hug|fixed\"" "EN data-ui-sizing"
require "$EN" "Preview CSS px is an artboard snapshot, not runtime sizing" "EN preview px ≠ runtime"
require "$EN" "Copying get_code \`w-[Npx]\` into implementation as a hardcoded width" "EN anti hardcoded width"
require "$EN" "Implementation consumption (REQUIRED whenever this contract is implemented)" "EN implement from sizing not px"
require "$EN" "overflow policy" "EN overflow policy"
require "$EN" "stop and ask the user" "EN ask overflow"
require "$EN" "Dumping every snapshot box" "EN anti dump snapshot constants"
require "$EN" "dt[data-ui-sizing]\` — required attribute" "EN sizing table required attr"

# EN — paint compositing / mask (not a second overlay wash)
require "$EN" "### 3b. Paint compositing / mask scan" "EN §3b"
require "$EN" "not a second visible wash" "EN mask ≠ overlay wash"
require "$EN" "dt[data-ui-compositing]" "EN compositing table"
require "$EN" "Treating a mask / alpha gradient as a second src-over overlay" "EN anti mask-as-overlay"
require "$EN" "data-hint-mask=\"true\"" "EN TemPad hint-mask"
require "$EN" "data-hint-has-mask=\"true\"" "EN TemPad hint-has-mask"
require "$EN" "\"isMask\": true" "EN structure isMask"
require "$EN" "Never copy TemPad \`data-hint-*\`" "EN strip data-hint"

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
require "$ZH" "用户点名的参考实现" "ZH user-named reference"

# ZH parity for layout sizing
require "$ZH" "### 5b. 布局尺寸分类（机械转移后必做）" "ZH §5b"
require "$ZH" "fill 判定规则" "ZH fill detection rule"
require "$ZH" "父宽减去对称水平内边距" "ZH fill = parent − inset"
require "$ZH" "data-ui-sizing=\"fill|hug|fixed\"" "ZH data-ui-sizing"
require "$ZH" "预览 CSS 的 px 是画板快照，不是运行时尺寸" "ZH preview px ≠ runtime"
require "$ZH" "把 get_code 的 \`w-[Npx]\` 抄进实现当硬编码宽度" "ZH anti hardcoded width"
require "$ZH" "实现时如何消费（凡按本契约实现都必须遵守）" "ZH implement from sizing not px"
require "$ZH" "overflow 策略" "ZH overflow policy"
require "$ZH" "停下问用户" "ZH ask overflow"
require "$ZH" "把每个快照盒子" "ZH anti dump snapshot constants"
require "$ZH" "dt[data-ui-sizing]\` — 必须带此属性" "ZH sizing table required attr"

# ZH parity for paint compositing / mask
require "$ZH" "### 3b. 绘制合成 / 蒙版扫描" "ZH §3b"
require "$ZH" "不是第二层可见罩色" "ZH mask ≠ overlay wash"
require "$ZH" "dt[data-ui-compositing]" "ZH compositing table"
require "$ZH" "把蒙版 / 仅 alpha 渐变当成第二层 src-over 覆盖" "ZH anti mask-as-overlay"
require "$ZH" "data-hint-mask=\"true\"" "ZH TemPad hint-mask"
require "$ZH" "data-hint-has-mask=\"true\"" "ZH TemPad hint-has-mask"
require "$ZH" "\"isMask\": true" "ZH structure isMask"
require "$ZH" "禁止把 TemPad 的 \`data-hint-*\`" "ZH strip data-hint"

# Template still ships hydrate + switcher + light preview base
TPL="$ROOT/.agents/skills/ui-truth-mapping/templates/ui-contract-template.html"
[[ -f "$TPL" ]] || fail "Missing template: $TPL"
require "$TPL" "data-ui-state-preview" "template preview script"
require "$TPL" "data-ui-state-switcher" "template switcher"
require "$TPL" "data-ui-state-host" "template host"
require "$TPL" "html, body" "template light html/body base"
require "$TPL" "data-ui-sizing" "template sizing annotation"
require "$TPL" "data-ui-compositing" "template compositing annotation"

# Kit skills must stay framework-agnostic — no host-app size tokens or artboard numbers.
for f in "$EN" "$ZH"; do
  if grep -E '343|375[[:space:]]*artboard|343\.w' "$f" >/dev/null; then
    fail "project-specific size anecdote in $(basename "$f")"
  fi
done

echo "PASS: ui-truth-mapping skill markers"
