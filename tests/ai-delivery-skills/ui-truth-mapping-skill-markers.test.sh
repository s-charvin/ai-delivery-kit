#!/usr/bin/env bash
set -euo pipefail

# Guardrails for ui-truth-mapping skill wording. If these markers regress,
# agents re-learn whole-page-dump / get_code-then-prune / HTML-then-Flutter
# failure modes.

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

# EN — scope / split / evidence
require "$EN" "### 1b. Unit Split Plan (REQUIRED before any \`get_code\` or component code)" "EN §1b"
require "$EN" "get_code\` target **must equal**" "EN get_code==source_node"
require "$EN" "Enumerate frames to classify — not to freeze" "EN enumerate≠freeze"
require "$EN" "Full-page \`get_code\` then prune" "EN anti prune"
require "$EN" "Skipping the §1b Unit Split Plan" "EN anti skip plan"
require "$EN" "Scoped \`get_code\` only" "EN scoped get_code"
require "$EN" "Quick Reference — Scenario → Unit split" "EN scenario table"
require "$EN" "create** \`component\` rooted at the badge" "EN red-dot create component"

# EN — rebuild-lifecycle
require "$EN" "Do not write an unverified \`delivery.implemented.target\`" "EN unverified target ban"
require "$EN" "Reference check:" "EN two-step target verification"
require "$EN" "### 9. Replace or deprecate — sweep stale pointers in the same change" "EN §9 pointer sweep"
require "$EN" "**Rebuild/split metadata rule:**" "EN rebuild metadata"

# EN — motion
require "$EN" "Split a multi-clause SECTION note per unit" "EN split SECTION note per unit"
require "$EN" "Consistency check (REQUIRED before writing component code)" "EN consistency check"
require "$EN" "Coverage review after every prune (REQUIRED)" "EN coverage review"
require "$EN" "User-named reference implementation" "EN user-named reference"

# EN — sizing
require "$EN" "### 5b. Layout sizing classification" "EN §5b"
require "$EN" "fill detection rule" "EN fill detection rule"
require "$EN" "parent width minus symmetrical horizontal inset" "EN fill = parent − inset"
require "$EN" "fill / hug / fixed" "EN fill hug fixed"
require "$EN" "Preview px is an artboard snapshot, not runtime sizing" "EN preview px ≠ runtime"
require "$EN" "Copying get_code \`w-[Npx]\`" "EN anti hardcoded width"
require "$EN" "overflow policy" "EN overflow policy"
require "$EN" "stop and ask the user" "EN ask overflow"
require "$EN" "Dumping every snapshot box" "EN anti dump snapshot constants"

# EN — compositing
require "$EN" "### 3b. Paint compositing / mask scan" "EN §3b"
require "$EN" "not a second visible wash" "EN mask ≠ overlay wash"
require "$EN" "data-hint-mask=\"true\"" "EN TemPad hint-mask"
require "$EN" "data-hint-has-mask=\"true\"" "EN TemPad hint-has-mask"
require "$EN" "\"isMask\": true" "EN structure isMask"
require "$EN" "Never copy TemPad \`data-hint-*\`" "EN strip data-hint"
require "$EN" "Do not invent visual truth" "EN anti invent"

# EN — native stack freeze
require "$EN" "matchesGoldenFile" "EN golden matcher"
require "$EN" "--update-goldens" "EN update-goldens"
require "$EN" "absolute path" "EN absolute path"
require "$EN" "ui-truth-index.json" "EN truth index"
require "$EN" "generate \`ui-contract.html\`" "EN ban html contract"
require "$EN" "translate HTML into Flutter" "EN ban HTML→Flutter"
require "$EN" "Anti-patterns" "EN anti-patterns"

if grep -E '^description:.*Auto-detects' "$EN" >/dev/null; then
  fail "EN description summarizes workflow (Auto-detects) — SDO violation"
fi

# ZH parity
require "$ZH" "### 1b. 单元拆分计划" "ZH §1b"
require "$ZH" "枚举帧是为了分类 — 不是为了冻结" "ZH enumerate≠freeze"
require "$ZH" "整页 \`get_code\` 再裁剪" "ZH anti prune"
require "$ZH" "跳过 §1b 单元拆分计划" "ZH anti skip plan"
require "$ZH" "只对作用域调 \`get_code\`" "ZH scoped get_code"
require "$ZH" "快速参考 — 场景 → 单元拆分" "ZH scenario table"
require "$ZH" "不要凭记忆写未经核实的 \`delivery.implemented.target\`" "ZH unverified target ban"
require "$ZH" "引用核实：" "ZH two-step target verification"
require "$ZH" "### 9. 替换或废弃 — 同一次变更内清扫陈旧指针" "ZH §9 pointer sweep"
require "$ZH" "**重建/拆分的元数据规则：**" "ZH rebuild metadata"
require "$ZH" "多条款 SECTION 备注按 unit 拆分" "ZH split SECTION note per unit"
require "$ZH" "一致性检查（写组件代码前必做）" "ZH consistency check"
require "$ZH" "每次裁剪后的覆盖复查（必做）" "ZH coverage review"
require "$ZH" "用户点名的参考实现" "ZH user-named reference"
require "$ZH" "### 5b. 布局尺寸分类" "ZH §5b"
require "$ZH" "fill 判定规则" "ZH fill detection rule"
require "$ZH" "父宽减去对称水平内边距" "ZH fill = parent − inset"
require "$ZH" "预览 px 是画板快照，不是运行时尺寸" "ZH preview px ≠ runtime"
require "$ZH" "把 get_code 的 \`w-[Npx]\`" "ZH anti hardcoded width"
require "$ZH" "overflow 策略" "ZH overflow policy"
require "$ZH" "停下问用户" "ZH ask overflow"
require "$ZH" "把每个快照盒子" "ZH anti dump snapshot constants"
require "$ZH" "### 3b. 绘制合成 / 蒙版扫描" "ZH §3b"
require "$ZH" "不是第二层可见罩色" "ZH mask ≠ overlay wash"
require "$ZH" "data-hint-mask=\"true\"" "ZH TemPad hint-mask"
require "$ZH" "data-hint-has-mask=\"true\"" "ZH TemPad hint-has-mask"
require "$ZH" "\"isMask\": true" "ZH structure isMask"
require "$ZH" "禁止把 TemPad \`data-hint-*\`" "ZH strip data-hint"
require "$ZH" "不要发明视觉真值" "ZH anti invent"
require "$ZH" "matchesGoldenFile" "ZH golden matcher"
require "$ZH" "--update-goldens" "ZH update-goldens"
require "$ZH" "绝对路径" "ZH absolute path"
require "$ZH" "ui-truth-index.json" "ZH truth index"
require "$ZH" "生成 \`ui-contract.html\`" "ZH ban html contract"
require "$ZH" "把 HTML 翻译成 Flutter" "ZH ban HTML→Flutter"
require "$ZH" "反模式" "ZH anti-patterns"

EXAMPLE="$ROOT/.agents/skills/ui-truth-mapping/templates/flutter-golden-preview-test.dart.example"
[[ -f "$EXAMPLE" ]] || fail "Missing golden example: $EXAMPLE"
require "$EXAMPLE" "matchesGoldenFile" "example golden matcher"
require "$EXAMPLE" "RepaintBoundary" "example repaint boundary"
require "$EXAMPLE" "--update-goldens" "example update-goldens"
require "$EXAMPLE" "PNG canvas" "example preview canvas ≠ runtime"
require "$EXAMPLE" "state-switcher" "example bans in-widget switcher"
require "$EXAMPLE" "viewPadding" "example strips system chrome"
require "$EXAMPLE" "per reviewable state" "example one test per state"

for f in "$EN" "$ZH"; do
  if grep -E '343|375[[:space:]]*artboard|343\.w' "$f" >/dev/null; then
    fail "project-specific size anecdote in $(basename "$f")"
  fi
done

echo "PASS: ui-truth-mapping skill markers"
