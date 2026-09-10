#!/usr/bin/env bash
set -euo pipefail

# Guardrails for ui-truth-mapping skill wording. If these markers regress,
# agents re-learn whole-page-dump / get_code-then-prune / HTML-then-Flutter
# failure modes.

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
EN="$ROOT/.agents/skills/ui-truth-mapping/SKILL.md"
ZH="$ROOT/.agents-zh/skills/ui-truth-mapping/SKILL-zh.md"
ORCH="$ROOT/.agents/skills/ai-delivery-orchestrator/SKILL.md"

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
require "$EN" "Real data or intentional emptiness" "EN real-data emptiness"
require "$EN" "motion_decision" "EN motion decision"
require "$EN" "Stage 4 must later record independent motion acceptance" "EN separate motion acceptance"
require "$EN" "test-harness fixture" "EN fixture containment"
require "$EN" "If a temporary placeholder is genuinely necessary, ask separately whether it is allowed" "EN placeholder approval"
require "$EN" "Preserve the required resource class" "EN resource class preservation"
require "$EN" "do not use a poster frame or static substitute" "EN no poster fallback"
require "$EN" "This is the Stage 2 UI Truth Mapping freeze gate; it is not a separate stage" "EN Stage 2 freeze gate"
require "$EN" "Static golden confirmation alone never advances \`acceptance_frozen\`" "EN golden cannot advance freeze"
require "$EN" "motion preview" "EN generic motion output"

# ZH — motion and resource guardrails stay explicit in the localized entrypoint
unicode_text() {
  python3 -c 'import sys; print("".join(chr(int(codepoint, 16)) for codepoint in sys.argv[1].split()), end="")' "$1"
}

ZH_SEPARATE_MOTION_CONFIRMATION=$(unicode_text '9759 6001 89C6 89C9 786E 8BA4 548C 52A8 6548 786E 8BA4 002F 8C41 514D 662F 5206 5F00 7684 8BC1 636E')
ZH_GIF_SCOPE=$(unicode_text '4E0D 8981 65B0 589E')
ZH_GIF_ENCODER=$(unicode_text '7F16 7801 5668')
ZH_REAL_WIDGET_API=$(unicode_text '771F 5B9E')
ZH_STRICT_KEYFRAMES=$(unicode_text '4E25 683C 9012 589E 7684 7D2F 8BA1')
ZH_MINIMUM_GIF_FRAMES=$(unicode_text '81F3 5C11 4E24 4E2A')
ZH_ALTERNATE_FORMATS=$(unicode_text '6216 5BBF 4E3B 5DF2 652F 6301 7684 5176 4ED6 683C 5F0F 002F 5B98 65B9 8FD0 884C 65F6 5F55 5236')
ZH_RESOURCE_CLASS=$(unicode_text '4FDD 7559 6240 9700 8D44 6E90 7C7B 522B')
ZH_NO_POSTER_FALLBACK=$(unicode_text '4E0D 5F97 4F7F 7528 6D77 62A5 5E27 6216 9759 6001 66FF 4EE3')
ZH_STAGE2_FREEZE_GATE=$(unicode_text '8FD9 662F 0020 0053 0074 0061 0067 0065 0020 0032 0020 0055 0049 0020 0054 0072 0075 0074 0068 0020 004D 0061 0070 0070 0069 006E 0067 0020 5185 7684 51BB 7ED3 95E8 69DB FF0C 4E0D 662F 72EC 7ACB 0020 0053 0074 0061 0067 0065')
ZH_GOLDEN_CANNOT_FREEZE=$(unicode_text '4EC5 9759 6001 0020 0067 006F 006C 0064 0065 006E 0020 786E 8BA4 7EDD 4E0D 80FD 63A8 8FDB 5230 0020 0060 0061 0063 0063 0065 0070 0074 0061 006E 0063 0065 005F 0066 0072 006F 007A 0065 006E 0060')
ZH_EXPLICIT_ENCODER_RATE=$(unicode_text '663E 5F0F 63A5 6536 0020 0032 0035 0020 0046 0050 0053 0020 7684 8F93 5165 002F 8F93 51FA 901F 7387')
ZH_IME_MATRIX=$(unicode_text '6BCF 4E2A 53EF 7F16 8F91 8F93 5165 90FD 5FC5 987B 6709 660E 786E 7684 72B6 6001 002F 0049 004D 0045 0020 77E9 9635')
ZH_COMPOSED_ASSETS=$(unicode_text '5728 8BED 4E49 7EC4 4EF6 8FB9 754C 89E3 6790 8D44 6E90 7EC4 5408')
ZH_CONTROL_STATE_VARIANTS=$(unicode_text '4ECE 771F 5B9E 63A7 4EF6 72B6 6001 63A8 5BFC 89C6 89C9 53D8 4F53')
ZH_MEASUREMENT_FONT=$(unicode_text '4F7F 7528 4E0E 5B9E 9645 6E32 67D3 76F8 540C 7684 5DF2 89E3 6790 5B57 4F53 65CF')

ZH_GENERIC_GIF=$(unicode_text '4E0D 8981 4E3A 5176 4ED6 683C 5F0F 65B0 589E')
ZH_ADAPTER=$(unicode_text '6846 67B6 9002 914D 5668')
ZH_REAL_COMPONENT=$(unicode_text '771F 5B9E 7EC4 4EF6 884C 4E3A')
ZH_MOTION_OUTPUT=$(unicode_text '53EF 9009 7684 0020 0047 0049 0046 0020 52A8 6548 5BA1 9605 5A92 4ECB')

require "$ZH" "static / no motion" "ZH explicit static motion decision"
require "$ZH" "$ZH_SEPARATE_MOTION_CONFIRMATION" "ZH separate motion confirmation"
require "$ZH" "$ZH_GENERIC_GIF" "ZH GIF scope"
require "$EN" "strictly increasing cumulative keyframes" "EN strict motion keyframes"
require "$EN" "temporary or ignored build directory" "EN temporary frame lifecycle"
require "$EN" "framework adapter" "EN adapter abstraction"
require "$ZH" "$ZH_ADAPTER" "ZH adapter abstraction"
require "$ZH" "$ZH_REAL_COMPONENT" "ZH adapter trigger reference"
require "$ZH" "$ZH_RESOURCE_CLASS" "ZH resource class preservation"
require "$ZH" "$ZH_NO_POSTER_FALLBACK" "ZH no poster fallback"
require "$ZH" "$ZH_STAGE2_FREEZE_GATE" "ZH Stage 2 freeze gate"
require "$ZH" "$ZH_GOLDEN_CANNOT_FREEZE" "ZH golden cannot advance freeze"
require "$ZH" "$ZH_MOTION_OUTPUT" "ZH generic motion output"

for forbidden in "flutter-golden-preview" "matchesGoldenFile" "testWidgets" "RenderRepaintBoundary" "RepaintBoundary" "AssetEntity" "xc_video_player"; do
  if grep -Fq -- "$forbidden" "$EN"; then
    fail "core EN skill contains framework-specific token: $forbidden"
  fi
  if grep -Fq -- "$forbidden" "$ZH"; then
    fail "core ZH skill contains framework-specific token: $forbidden"
  fi
done

for f in "$EN" "$ZH"; do
  if grep -Fq 'test/motion/<unit>.*' "$f"; then
    fail "motion output path must be GIF-only in $(basename "$f")"
  fi
done

if grep -Fq 'GIF/video/runtime preview' "$ROOT/.agents/skills/ai-delivery-orchestrator/SKILL.md"; then
  fail "GIF-only contract still permits video motion previews"
fi
if grep -Fq "$ZH_ALTERNATE_FORMATS" "$ZH"; then
  fail "localized GIF-only contract still permits alternate motion formats"
fi

# EN — runtime coverage
require "$EN" "### 3c. Runtime Coverage Plan" "EN runtime coverage plan"
require "$ORCH" "ui_truth_mode" "EN capability mode"
require "$ORCH" "Capability-gated" "EN capability-gated UI truth"
require "$EN" 'figma` / `requirement` / `project` / `user-decision' "EN evidence origins"
require "$EN" "all ten coverage dimensions" "EN complete coverage"
require "$EN" 'reviewed_preview_sha256' "EN preview-bound confirmation"
require "$EN" 'structured `visual-acceptance.json`' "EN structured Stage 4 acceptance"
require "$EN" "A static golden never substitutes for motion acceptance" "EN golden cannot replace motion"
require "$EN" '`component-only`, `host-static`, or `host-runtime`' "EN evidence scope enum"
require "$EN" "Host Capability Decision (REQUIRED before preview generation)" "EN host capability decision"
require "$EN" "part of the requirement's visual truth" "EN host visual scope check"
require "$EN" "existing runnable host test entrypoint" "EN existing host entrypoint check"
require "$EN" "real production host" "EN production host check"
require "$EN" "deterministically prepare" "EN deterministic state check"
require "$EN" "reviewable screenshot" "EN reviewable screenshot check"
require "$EN" "A test shell assembled from otherwise real components is not a production host" "EN fake host ban"
require "$EN" "shrink the acceptance claim" "EN component-only claim boundary"
require "$EN" "Every editable input must have an explicit state/IME matrix" "EN input IME matrix"
require "$EN" "Resolve asset composition at the semantic component boundary" "EN composed assets"
require "$EN" "derive visual variants from the real control state" "EN input icon from control state"
require "$EN" "use the same resolved font family" "EN measurement matches renderer"
require "$ZH" "$ZH_IME_MATRIX" "ZH input IME matrix"
require "$ZH" "$ZH_COMPOSED_ASSETS" "ZH composed assets"
require "$ZH" "$ZH_CONTROL_STATE_VARIANTS" "ZH input icon from control state"
require "$ZH" "$ZH_MEASUREMENT_FONT" "ZH measurement matches renderer"

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
require "$EN" "absolute path" "EN absolute path"
require "$EN" "ui-truth-index.json" "EN truth index"
require "$EN" "generate \`ui-contract.html\`" "EN ban html contract"
require "$EN" "translate between host stacks" "EN ban cross-stack translation"
require "$EN" "Anti-patterns" "EN anti-patterns"

if grep -E '^description:.*Auto-detects' "$EN" >/dev/null; then
  fail "EN description summarizes workflow (Auto-detects) — SDO violation"
fi

EXAMPLE="$ROOT/.agents/skills/ui-truth-mapping/references/framework-adapters/flutter/golden-preview-test.dart.example"
[[ -f "$EXAMPLE" ]] || fail "Missing golden example: $EXAMPLE"
require "$EXAMPLE" "matchesGoldenFile" "example golden matcher"
require "$EXAMPLE" "RepaintBoundary" "example repaint boundary"
require "$EXAMPLE" "--update-goldens" "example update-goldens"
require "$EXAMPLE" "PNG canvas" "example preview canvas ≠ runtime"
require "$EXAMPLE" "state-switcher" "example bans in-widget switcher"
require "$EXAMPLE" "viewPadding" "example strips system chrome"
require "$EXAMPLE" "per reviewable visual scenario" "example one test per visual scenario"

MOTION_EXAMPLE="$ROOT/.agents/skills/ui-truth-mapping/references/framework-adapters/flutter/motion-preview-test.dart.example"
[[ -f "$MOTION_EXAMPLE" ]] || fail "Missing motion example: $MOTION_EXAMPLE"
ZH_MOTION_EXAMPLE="$ROOT/.agents-zh/skills/ui-truth-mapping/references/framework-adapters/flutter/motion-preview-test.dart.example"
[[ -f "$ZH_MOTION_EXAMPLE" ]] || fail "Missing localized motion example: $ZH_MOTION_EXAMPLE"
require "$MOTION_EXAMPLE" "matchesGoldenFile" "motion example golden matcher"
require "$MOTION_EXAMPLE" "cumulative elapsed keyframes" "motion example cumulative keyframes"
require "$MOTION_EXAMPLE" "GIF" "motion example GIF output"
require "$MOTION_EXAMPLE" "Trigger the real widget behavior" "motion example real trigger"
require "$MOTION_EXAMPLE" "Process.runSync" "motion example GIF encoder"
require "$MOTION_EXAMPLE" "totalDuration" "motion example covers total duration"
require "$MOTION_EXAMPLE" "could not be decoded" "motion example validates GIF"
require "$MOTION_EXAMPLE" "at least two keyframes" "motion example minimum frames"
require "$MOTION_EXAMPLE" "must be strictly increasing cumulative keyframes" "motion example strict timing"
require "$MOTION_EXAMPLE" "NETSCAPE2.0" "motion example automatic loop"
require "$MOTION_EXAMPLE" "record why the preview is" "motion example records unavailable reason"
require "$MOTION_EXAMPLE" "obtain motion confirmation or an explicit waiver" "motion example requires disposition"
require "$MOTION_EXAMPLE" "25 FPS" "motion example high cadence"
require "$MOTION_EXAMPLE" "40,000 microseconds" "motion example frame interval"
require "$MOTION_EXAMPLE" "_elapsedTimesForMotion" "motion example samples every frame"
require "$MOTION_EXAMPLE" "'-f'" "motion example concat input format"
require "$MOTION_EXAMPLE" "'concat'" "motion example concat demuxer"
require "$MOTION_EXAMPLE" "'-fps_mode'" "motion example explicit VFR mode"
require "$MOTION_EXAMPLE" "'vfr'" "motion example duration-preserving output"
require "$MOTION_EXAMPLE" "padLeft(5, '0')" "motion example numbered frame input"
require "$MOTION_EXAMPLE" "Directory.systemTemp" "motion example temporary frame directory"
require "$MOTION_EXAMPLE" "deleteSync(recursive: true)" "motion example frame cleanup"
require "$MOTION_EXAMPLE" "finally" "motion example cleanup finally"
require "$ZH_MOTION_EXAMPLE" "25 FPS" "localized motion example high cadence"
require "$ZH_MOTION_EXAMPLE" "40000" "localized motion example frame interval"
require "$ZH_MOTION_EXAMPLE" "_elapsedTimesForMotion" "localized motion example samples every frame"
require "$ZH_MOTION_EXAMPLE" "'-f'" "localized motion example concat input format"
require "$ZH_MOTION_EXAMPLE" "'concat'" "localized motion example concat demuxer"
require "$ZH_MOTION_EXAMPLE" "'-fps_mode'" "localized motion example explicit VFR mode"
require "$ZH_MOTION_EXAMPLE" "'vfr'" "localized motion example duration-preserving output"
require "$ZH_MOTION_EXAMPLE" "padLeft(5, '0')" "localized motion example numbered frame input"
require "$ZH_MOTION_EXAMPLE" "Directory.systemTemp" "localized motion example temporary frame directory"
require "$ZH_MOTION_EXAMPLE" "deleteSync(recursive: true)" "localized motion example frame cleanup"
require "$ZH_MOTION_EXAMPLE" "finally" "localized motion example cleanup finally"
require "$ZH_MOTION_EXAMPLE" "NETSCAPE2.0" "localized motion example automatic loop"
require "$ZH_MOTION_EXAMPLE" "ffprobe" "localized motion example verifies GIF"

for f in "$MOTION_EXAMPLE" "$ZH_MOTION_EXAMPLE"; do
  if grep -Fq 'Duration(milliseconds: 120)' "$f"; then
    fail "motion example must not use sparse 120 ms frame steps in $(basename "$f")"
  fi
  if grep -Fq '30 FPS' "$f"; then
    fail "motion example must use the 25 FPS contract in $(basename "$f")"
  fi
  if grep -Fq "'cfr'" "$f"; then
    fail "motion example must preserve declared durations with VFR in $(basename "$f")"
  fi
  if ! grep -Fq "'concat'" "$f" || ! grep -Fq "'vfr'" "$f"; then
    fail "motion example must use concat/VFR duration-preserving encoding in $(basename "$f")"
  fi
done

for f in "$EN" "$ZH"; do
  if grep -E '343|375[[:space:]]*artboard|343\.w' "$f" >/dev/null; then
    fail "project-specific size anecdote in $(basename "$f")"
  fi
done

echo "PASS: ui-truth-mapping skill markers"
