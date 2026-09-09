#!/usr/bin/env bash
set -euo pipefail

# Pressure markers for Stage 4 visual-truth and framework-artifact rules.
#
# Observed failures without these rules:
# 1. Agents re-called TemPad get_code/get_structure during implement because
#    stage-implementation said "Run figma-design-to-code only in this stage",
#    creating a second visual truth that can disagree with the frozen HTML.
# 2. Agents copied contract/get_code pixel widths as runtime constants
#    instead of fill + parent insets.
# 3. External frameworks persisted plans, reviews, and session state in their
#    own repository-root directories instead of the governed sub-requirement.
# 4. Agents treated CP-UI as worktree consent and accepted a native tool's
#    only placement under /private/tmp without asking the user.

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
EN="$ROOT/.agents/skills/ai-delivery-orchestrator/references/stage-implementation.md"
ZH="$ROOT/.agents-zh/skills/ai-delivery-orchestrator/references/stage-implementation.md"
EN_UI="$ROOT/.agents/skills/ai-delivery-orchestrator/references/stage-ui-truth.md"
EN_SKILL="$ROOT/.agents/skills/ai-delivery-orchestrator/SKILL.md"
EN_BRIDGE="$ROOT/.agents/skills/ai-delivery-orchestrator/references/stage-4-sdd-bridge.md"
EN_DESIGN_STAGE="$ROOT/.agents/skills/ai-delivery-orchestrator/references/stage-design-and-spec.md"
ZH_DESIGN_STAGE="$ROOT/.agents-zh/skills/ai-delivery-orchestrator/references/stage-design-and-spec.md"
EN_DESIGN_TEMPLATE="$ROOT/.agents/skills/ai-delivery-orchestrator/templates/design-template.md"
EN_ADAPT="$ROOT/.agents/skills/ai-delivery-orchestrator/references/framework-adaptation.md"
ZH_ADAPT="$ROOT/.agents-zh/skills/ai-delivery-orchestrator/references/framework-adaptation.md"
EN_WORKSPACE="$ROOT/.agents/skills/ai-delivery-orchestrator/references/workspace-policy.md"
ZH_WORKSPACE="$ROOT/.agents-zh/skills/ai-delivery-orchestrator/references/workspace-policy.md"
ZH_UI="$ROOT/.agents-zh/skills/ai-delivery-orchestrator/references/stage-ui-truth.md"
ZH_SKILL="$ROOT/.agents-zh/skills/ai-delivery-orchestrator/SKILL-zh.md"
EN_FRAMEWORKS="$ROOT/.agents/skills/ai-delivery-orchestrator/references/frameworks"
ZH_FRAMEWORKS="$ROOT/.agents-zh/skills/ai-delivery-orchestrator/references/frameworks"
ARTIFACT_LAYOUT="$ROOT/docs/artifact-layout.md"
ZH_PROTOCOL_HEADING="$(python3 -c 'print("## \u4ea7\u7269\u8fb9\u754c\u534f\u8bae\uff08\u5fc5\u987b\uff09")')"
ZH_METHOD_ONLY="$(python3 -c 'print("\u5916\u90e8 skill \u53ea\u63d0\u4f9b\u65b9\u6cd5\u4e0e\u6267\u884c\u7eaa\u5f8b")')"
ZH_NO_MOVE="$(python3 -c 'print("\u7981\u6b62\u5148\u5728\u5176\u4ed6\u4f4d\u7f6e\u751f\u6210\u518d\u642c\u8fd0")')"
ZH_BOUNDARY_HEADING="$(python3 -c 'print("## \u4ea7\u7269\u8fb9\u754c")')"
ZH_LAYOUT_HEADING="$(python3 -c 'print("## 2. \u6846\u67b6\u9694\u79bb\uff08\u65e0\u6d3e\u751f\u6cbb\u7406\u89c6\u56fe\uff09")')"
ZH_FRAMEWORK_FIRST="$(python3 -c 'print("\u4ea7\u7269\u843d\u6846\u67b6\u76ee\u5f55")')"
ZH_FINGERPRINT="$(python3 -c 'print("\u72b6\u6001/\u5185\u5bb9\u6307\u7eb9\u8d26\u672c")')"
ZH_IGNORED_FINGERPRINT="$(python3 -c 'print("\u72ec\u7acb\u6587\u4ef6\u7cfb\u7edf\u6307\u7eb9")')"
ZH_SKIP_PERSISTENCE="$(python3 -c 'print("\u4e0d\u8c03\u7528\u8be5\u6301\u4e45\u5316\u6b65\u9aa4")')"
ZH_SESSION_METADATA="$(python3 -c 'print("\u4f1a\u8bdd\u5143\u6570\u636e")')"
ZH_HOST_ALLOWLIST="$(python3 -c 'print("\u5bbf\u4e3b\u6811\u53ea\u5141\u8bb8\u5199\u751f\u4ea7\u6e90\u7801")')"
ZH_STAGE2_AUDIT="$(python3 -c 'print("Stage 2 \u4ea7\u7269\u8fb9\u754c\u8def\u5f84\u5ba1\u8ba1")')"
ZH_WORKTREE_OPTIONAL="$(python3 -c 'print("worktree \u662f\u53ef\u9009\u7684")')"
ZH_WORKTREE_CONFIRM="$(python3 -c 'print("\u5f53\u524d\u5b50\u9700\u6c42\u7684\u7528\u6237\u660e\u786e\u786e\u8ba4")')"
ZH_EXTERNAL_WORKTREE="$(python3 -c 'print("\u5916\u90e8 worktree")')"
ZH_EXTERNAL_ROOTS="$(python3 -c 'print("\u7981\u6b62 `/private/tmp`\u3001`/tmp`")')"
ZH_ONLY_WORKTREE_PATH="$(python3 -c 'print("\u552f\u4e00\u5141\u8bb8\u7684 worktree \u8def\u5f84")')"
ZH_SWITCH_NOT_DESTRUCTIVE="$(python3 -c 'print("\u5207\u6362 workspace \u4e0d\u6388\u6743\u8fc1\u79fb\u3001\u91cd\u5efa\u6216\u5220\u9664")')"
ZH_LEAVE_EXTERNAL_UNCHANGED="$(python3 -c 'print("\u4fdd\u6301\u5916\u90e8 worktree \u539f\u6837")')"

fail() { echo "FAIL: $*" >&2; exit 1; }

require() {
  local file="$1" needle="$2" label="$3"
  [[ -f "$file" ]] || fail "Missing file: $file"
  grep -F -q -- "$needle" "$file" || fail "$label missing in $(basename "$file"): $needle"
}

forbid() {
  local file="$1" needle="$2" label="$3"
  [[ -f "$file" ]] || fail "Missing file: $file"
  if grep -F -q -- "$needle" "$file"; then
    fail "$label still present in $(basename "$file"): $needle"
  fi
}

# The old sentence is read as "you MUST run TemPad in Stage 4".
forbid "$EN" "Run \`figma-design-to-code\` only in this stage" "EN old TemPad-must-run wording"

require "$EN" "Do not run \`figma-design-to-code\` or call TemPad" "EN no TemPad ritual"
require "$EN" "the frozen component wins" "EN frozen component wins vs live TemPad"
require "$EN" "fill / hug / fixed" "EN follow sizing classification"
require "$EN" "not a runtime constant" "EN preview px ≠ runtime"
require "$EN" "stop and ask" "EN ask overflow at implement"
require "$EN" "snapshot \`w×h\` equality" "EN VA not snapshot px"
require "$EN" "execute every v2 scenario" "EN complete runtime scenario execution"
require "$EN" "preview hashes remain identical" "EN preview hash invalidation"
require "$EN" "reference/candidate/diff hashes" "EN deterministic image diff evidence"
require "$EN" "one independent motion acceptance record for every indexed unit" "EN independent motion acceptance"
require "$EN" "fabricated fixture content" "EN no fabricated data"

require "$EN_UI" "Stage 4 does not re-run it by default" "EN Stage 2 pointer"
require "$EN_UI" "all ten coverage dimensions" "EN runtime coverage freeze gate"
require "$EN_UI" "Static golden confirmation and motion confirmation/waiver are separate gates" "EN Stage 2 motion gate"

require "$EN_SKILL" "do not re-query TemPad / run \`figma-design-to-code\` by default" "EN SKILL Stage 4"
require "$EN_SKILL" "structured \`visual-acceptance.json\`" "EN structured acceptance gate"
require "$EN_SKILL" "state_flow_required" "EN state-flow trigger"
require "$EN_SKILL" "design_review" "EN design review binding"
require "$EN_BRIDGE" "exactly one result for every indexed scenario id" "EN exact scenario acceptance"
require "$EN_DESIGN_STAGE" "every frozen unit/scenario id" "EN scenario-linked spec"
require "$EN_DESIGN_STAGE" "which task implements or verifies each scenario id" "EN scenario-linked plan"
require "$EN_DESIGN_STAGE" "complete scenario-to-test/acceptance coverage" "EN scenario-linked tasks"
require "$EN_DESIGN_STAGE" "solution-design" "EN solution-design stage"
require "$EN_DESIGN_STAGE" "ui_truth_mode" "EN UI truth mode routing"
require "$EN_DESIGN_STAGE" "design_mode" "EN design mode routing"
require "$EN_DESIGN_STAGE" "reviewed_design_sha256" "EN design hash binding"
require "$EN_DESIGN_STAGE" "state-flow contract" "EN state-flow design contract"
require "$EN_DESIGN_TEMPLATE" "UI Scenario References" "EN UI scenario references"
require "$EN_DESIGN_TEMPLATE" "Scenario IDs" "EN scenario ID references"
for forbidden in "Responsive" "Reduced motion" "Figma source"; do
  forbid "$EN_DESIGN_TEMPLATE" "$forbidden" "EN design template must not duplicate runtime coverage ($forbidden)"
done
require "$EN_DESIGN_TEMPLATE" "does not duplicate their Runtime Coverage Plan" "EN design template delegates runtime coverage"
require "$EN_DESIGN_TEMPLATE" "State and Transition Model" "EN design state model"
require "$EN_DESIGN_TEMPLATE" "ai-delivery:state-flow:start" "EN state-flow marker"
require "$EN_DESIGN_TEMPLATE" "authoritative Transition Matrix" "EN transition matrix"
require "$EN_DESIGN_TEMPLATE" "sequenceDiagram" "EN async sequence diagram"

# Frameworks contribute methods only. Every process/governance artifact stays
# in the current sub-requirement's canonical .ai-delivery tree.
require "$EN_ADAPT" "## Artifact containment protocol (REQUIRED)" "EN artifact containment protocol"
require "$EN_ADAPT" "External skills provide methods and execution discipline only" "EN external skills are method-only"
require "$EN_ADAPT" "Do not create an artifact elsewhere and move it afterward" "EN no create-then-move"
require "$EN_ADAPT" 'docs/superpowers/**`, `.superpowers/**`, `.specify/**`, or `openspec/**' "EN forbidden framework roots"
require "$EN_ADAPT" "blocked_verification_failure" "EN containment failure status"
require "$EN_ADAPT" "status/content fingerprint ledger" "EN dirty-path fingerprint audit"
require "$EN_ADAPT" "independent filesystem fingerprint" "EN ignored-path fingerprint audit"
require "$EN_ADAPT" "including ignored files" "EN ignored paths are auditable"
require "$ZH_ADAPT" "$ZH_PROTOCOL_HEADING" "ZH artifact containment protocol"
require "$ZH_ADAPT" "$ZH_METHOD_ONLY" "ZH external skills are method-only"
require "$ZH_ADAPT" "$ZH_NO_MOVE" "ZH no create-then-move"
require "$ZH_ADAPT" "blocked_verification_failure" "ZH containment failure status"
require "$ZH_ADAPT" "$ZH_FINGERPRINT" "ZH dirty-path fingerprint audit"
require "$ZH_ADAPT" "$ZH_IGNORED_FINGERPRINT" "ZH ignored-path fingerprint audit"

for guide in spec-kit.md openspec.md superpowers.md ecc.md native.md; do
  require "$EN_FRAMEWORKS/$guide" "## Artifact containment" "EN framework containment ($guide)"
  require "$ZH_FRAMEWORKS/$guide" "$ZH_BOUNDARY_HEADING" "ZH framework containment ($guide)"
done

require "$EN_FRAMEWORKS/spec-kit.md" "do not invoke that persistence step" "EN spec-kit persistence override"
require "$EN_FRAMEWORKS/openspec.md" 'Do not run `openspec archive`' "EN OpenSpec external archive ban"
require "$EN_FRAMEWORKS/superpowers.md" 'docs/superpowers/**` or `.superpowers/**' "EN superpowers roots forbidden"
require "$EN_FRAMEWORKS/superpowers.md" 'layout key `solution_design`' "EN superpowers design canonical resolver"
require "$EN_FRAMEWORKS/superpowers.md" 'layout key `plan`' "EN superpowers plan canonical resolver"
require "$EN_FRAMEWORKS/ecc.md" "session metadata" "EN ECC metadata containment"
require "$EN_FRAMEWORKS/ecc.md" 'layout keys `solution_design`, `decisions`, `progress`, and `verification`' "EN ECC canonical resolvers"
require "$EN_FRAMEWORKS/native.md" "Host-tree writes are limited to production source" "EN native host allowlist"
require "$ZH_FRAMEWORKS/spec-kit.md" "$ZH_SKIP_PERSISTENCE" "ZH spec-kit persistence override"
require "$ZH_FRAMEWORKS/openspec.md" "$ZH_SKIP_PERSISTENCE" "ZH OpenSpec persistence override"
require "$ZH_FRAMEWORKS/superpowers.md" 'docs/superpowers/**' "ZH superpowers roots forbidden"
require "$ZH_FRAMEWORKS/superpowers.md" 'layout key `solution_design`' "ZH superpowers design canonical resolver"
require "$ZH_FRAMEWORKS/superpowers.md" 'layout key `plan`' "ZH superpowers plan canonical resolver"
require "$ZH_FRAMEWORKS/ecc.md" "$ZH_SESSION_METADATA" "ZH ECC metadata containment"
for key in solution_design decisions progress verification; do
  require "$ZH_FRAMEWORKS/ecc.md" "layout key \`$key\`" "ZH ECC canonical resolver ($key)"
done
require "$ZH_FRAMEWORKS/native.md" "$ZH_HOST_ALLOWLIST" "ZH native host allowlist"
for guide in spec-kit.md openspec.md native.md; do
  require "$EN_FRAMEWORKS/$guide" 'layout keys `spec`, `plan`, and `tasks`' "EN dynamic canonical outputs ($guide)"
  for key in spec plan tasks; do
    require "$ZH_FRAMEWORKS/$guide" "layout key \`$key\`" "ZH dynamic canonical output ($guide: $key)"
  done
  for field in kind canonical_path derived_paths content_sha256 sync_state; do
    require "$EN_FRAMEWORKS/$guide" "\"$field\"" "EN complete traceability field ($guide: $field)"
    require "$ZH_FRAMEWORKS/$guide" "\"$field\"" "ZH complete traceability field ($guide: $field)"
  done
  require "$EN_FRAMEWORKS/$guide" '"spec_refs"' "EN traceability wrapper ($guide)"
  require "$ZH_FRAMEWORKS/$guide" '"spec_refs"' "ZH traceability wrapper ($guide)"
  forbid "$EN_FRAMEWORKS/$guide" 'spec_refs.spec_path' "EN legacy traceability shape ($guide)"
  forbid "$ZH_FRAMEWORKS/$guide" 'spec_refs.spec_path' "ZH legacy traceability shape ($guide)"
done

require "$EN_UI" "artifact-boundary path audit" "EN Stage 2 path audit"
require "$EN_UI" "status/content fingerprint ledger" "EN Stage 2 dirty-path fingerprint"
require "$EN_UI" 'new or modified process/governance artifact outside `.ai-delivery/`' "EN Stage 2 escape detection"
require "$EN_UI" "blocked_verification_failure" "EN Stage 2 containment failure"
require "$ZH_UI" "$ZH_STAGE2_AUDIT" "ZH Stage 2 path audit"
require "$ZH_UI" "$ZH_FINGERPRINT" "ZH Stage 2 dirty-path fingerprint"
require "$ZH_UI" "blocked_verification_failure" "ZH Stage 2 containment failure"
require "$EN_SKILL" "External skill defaults never authorize framework-owned artifact paths" "EN orchestrator external path override"
require "$EN_SKILL" "status/content fingerprint" "EN orchestrator dirty-path fingerprint"
require "$ZH_SKILL" 'docs/superpowers/**' "ZH orchestrator external path override"
require "$ZH_SKILL" "$ZH_FINGERPRINT" "ZH orchestrator dirty-path fingerprint"
require "$ZH_DESIGN_STAGE" "content_sha256" "ZH traceability hash requirement"
require "$EN_DESIGN_STAGE" 'layout keys `spec`, `plan`, and `tasks`' "EN Stage 3 dynamic canonical paths"
for key in spec plan tasks; do
  require "$ZH_DESIGN_STAGE" "layout key \`$key\`" "ZH Stage 3 dynamic canonical path ($key)"
done
require "$ARTIFACT_LAYOUT" "$ZH_LAYOUT_HEADING" "artifact layout forbids derived views"

# A worktree is an optional, user-owned workspace choice. CP-UI/CP-001 and
# legacy policy flags never count as consent, and external temp roots are invalid.
require "$EN_WORKSPACE" "Worktrees are optional" "EN optional worktree policy"
require "$EN_WORKSPACE" "explicit user confirmation for the current sub-requirement" "EN per-slice worktree confirmation"
require "$EN_WORKSPACE" '.worktrees/<req-id>-<sr-id>' "EN project-local worktree path"
require "$EN_WORKSPACE" 'The only allowed worktree path is' "EN exact worktree template is mandatory"
forbid "$EN_WORKSPACE" 'preferred path is' "EN worktree path must not be optional"
require "$EN_WORKSPACE" "CP-UI and CP-001 do not authorize a worktree" "EN checkpoints are not worktree consent"
require "$EN_WORKSPACE" "stop production edits and ask the user" "EN external worktree stop-and-ask"
require "$EN_WORKSPACE" '`/private/tmp`, `/tmp`' "EN external temporary roots"
require "$EN_WORKSPACE" 'every other external location are forbidden' "EN external worktree roots forbidden"
require "$EN_WORKSPACE" 'must accept the exact project-local path' "EN native tool exact-path constraint"
require "$EN_WORKSPACE" 'ignore legacy `require_isolated_worktree`' "EN legacy mandatory policy ignored"
require "$EN_WORKSPACE" 'Switching workspaces does not authorize migrating, recreating, or deleting' "EN switch choice is not destructive consent"
require "$EN_WORKSPACE" 'Leave the external worktree unchanged' "EN preserve external worktree"
require "$EN_WORKSPACE" 'separate explicit confirmation that names the exact action and target' "EN destructive action requires scoped consent"
require "$ZH_WORKSPACE" "$ZH_WORKTREE_OPTIONAL" "ZH optional worktree policy"
require "$ZH_WORKSPACE" "$ZH_WORKTREE_CONFIRM" "ZH per-slice worktree confirmation"
require "$ZH_WORKSPACE" '.worktrees/<req-id>-<sr-id>' "ZH project-local worktree path"
require "$ZH_WORKSPACE" "$ZH_ONLY_WORKTREE_PATH" "ZH exact worktree template is mandatory"
require "$ZH_WORKSPACE" "$ZH_EXTERNAL_WORKTREE" "ZH external worktree stop-and-ask"
require "$ZH_WORKSPACE" "$ZH_EXTERNAL_ROOTS" "ZH external worktree roots forbidden"
require "$ZH_WORKSPACE" "$ZH_SWITCH_NOT_DESTRUCTIVE" "ZH switch choice is not destructive consent"
require "$ZH_WORKSPACE" "$ZH_LEAVE_EXTERNAL_UNCHANGED" "ZH preserve external worktree"
require "$EN_ADAPT" "workspace-policy.md" "EN framework adaptation workspace policy"
require "$ZH_ADAPT" "workspace-policy.md" "ZH framework adaptation workspace policy"
forbid "$EN_SKILL" "must create or reuse the slice worktree" "EN mandatory Stage 2 worktree"
forbid "$EN_UI" "Create or reuse one isolated worktree/branch" "EN mandatory Stage 2 isolation"
forbid "$EN" "create one worktree/branch here" "EN mandatory Stage 4 worktree creation"
forbid "$EN_FRAMEWORKS/superpowers.md" "create one worktree per slice only when no recorded slice worktree exists" "EN superpowers auto-worktree creation"
forbid "$EN_FRAMEWORKS/native.md" "create one branch per slice (and a worktree when supported) only when no slice workspace exists" "EN native auto-worktree creation"

forbid "$EN_ADAPT" "framework tooling writes there first" "EN framework-first persistence"
forbid "$ARTIFACT_LAYOUT" "$ZH_FRAMEWORK_FIRST" "artifact layout framework-first persistence"
forbid "$EN_FRAMEWORKS/spec-kit.md" 'spec-kit feature branch area (`.specify/`)' "EN spec-kit external output"
forbid "$EN_FRAMEWORKS/openspec.md" 'One OpenSpec change per sub-requirement: `openspec/changes/' "EN OpenSpec external output"

# Kit skills must stay framework-agnostic — no host-app size tokens or live-node anecdotes.
for f in "$EN" "$ZH"; do
  if grep -E '343|375[[:space:]]*artboard|343\.w|left: 35|x=46' "$f" >/dev/null; then
    fail "project-specific anecdote in $(basename "$f")"
  fi
done

echo "PASS: orchestrator Stage 4 skill markers"
