# AI Delivery Project Data Layer Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build the project-local `.ai-delivery/` data layer in `/Users/charvin/Projects/Codex`, including hidden directory structure, versioned contract files, sample requirement and Figma artifacts, and contract validation tooling that later admin and skill/MCP tracks can safely consume.

**Architecture:** Keep all workflow truth for the host project inside `.ai-delivery/` as structured Markdown, JSON, and NDJSON artifacts with explicit version fields and deterministic IDs. This plan defines only the project-side storage substrate and contract validation layer; it intentionally does not implement the separate `ai-delivery-admin` project or the custom skills/MCP runtime, but it produces the stable data surface those tracks will depend on.

**Tech Stack:** `Markdown`, `JSON`, `NDJSON`, `zsh`, `jq`, filesystem directory contracts, shell-based contract tests under `/Users/charvin/Projects/Codex/tests`, and a shell-based validator under `/Users/charvin/Projects/Codex/scripts`.

---

> Git note: `/Users/charvin/Projects/Codex` is currently not a git repository, so each task's commit step is marked unavailable until this workspace is initialized as a repository.

### Task 1: Scaffold The Root `.ai-delivery/` Hidden Directory Tree

**Files:**
- Create: `/Users/charvin/Projects/Codex/.ai-delivery/.gitkeep`
- Create: `/Users/charvin/Projects/Codex/.ai-delivery/requirements/.gitkeep`
- Create: `/Users/charvin/Projects/Codex/.ai-delivery/figma-cache/.gitkeep`
- Create: `/Users/charvin/Projects/Codex/.ai-delivery/runtime/.gitkeep`
- Create: `/Users/charvin/Projects/Codex/.ai-delivery/meta/.gitkeep`
- Create: `/Users/charvin/Projects/Codex/.ai-delivery/logs/events.ndjson`
- Create: `/Users/charvin/Projects/Codex/.ai-delivery/logs/sessions/.gitkeep`
- Create: `/Users/charvin/Projects/Codex/.ai-delivery/logs/subagents/.gitkeep`

**Step 1: Verify the target directories are currently absent or safe to create**

Run: `find /Users/charvin/Projects/Codex/.ai-delivery -maxdepth 3 -print 2>/dev/null || true`
Expected: no output or only paths you explicitly intend to keep

**Step 2: Create the root hidden directory tree**

Run:

```bash
mkdir -p \
  /Users/charvin/Projects/Codex/.ai-delivery/requirements \
  /Users/charvin/Projects/Codex/.ai-delivery/figma-cache \
  /Users/charvin/Projects/Codex/.ai-delivery/runtime \
  /Users/charvin/Projects/Codex/.ai-delivery/meta \
  /Users/charvin/Projects/Codex/.ai-delivery/logs/sessions \
  /Users/charvin/Projects/Codex/.ai-delivery/logs/subagents
```

Expected: all directories exist with no errors

**Step 3: Create empty placeholder files**

Run:

```bash
touch \
  /Users/charvin/Projects/Codex/.ai-delivery/.gitkeep \
  /Users/charvin/Projects/Codex/.ai-delivery/requirements/.gitkeep \
  /Users/charvin/Projects/Codex/.ai-delivery/figma-cache/.gitkeep \
  /Users/charvin/Projects/Codex/.ai-delivery/runtime/.gitkeep \
  /Users/charvin/Projects/Codex/.ai-delivery/meta/.gitkeep \
  /Users/charvin/Projects/Codex/.ai-delivery/logs/events.ndjson \
  /Users/charvin/Projects/Codex/.ai-delivery/logs/sessions/.gitkeep \
  /Users/charvin/Projects/Codex/.ai-delivery/logs/subagents/.gitkeep
```

Expected: files exist and `events.ndjson` is an empty file

**Step 4: Review the resulting tree**

Run: `find /Users/charvin/Projects/Codex/.ai-delivery -maxdepth 3 -print | sort`
Expected: only the planned root directories and placeholder files appear

**Step 5: Commit**

Not available until `/Users/charvin/Projects/Codex` becomes a git repository.

### Task 2: Define The `.ai-delivery/meta/` Policy Contracts

**Files:**
- Create: `/Users/charvin/Projects/Codex/.ai-delivery/meta/project-binding.json`
- Create: `/Users/charvin/Projects/Codex/.ai-delivery/meta/naming-rules.json`
- Create: `/Users/charvin/Projects/Codex/.ai-delivery/meta/workflow-policy.json`

**Step 1: Write `project-binding.json`**

Use this minimal shape:

```json
{
  "version": 1,
  "project_id": "codex",
  "project_root": "/Users/charvin/Projects/Codex",
  "specify_path": ".specify",
  "ai_delivery_path": ".ai-delivery",
  "updated_at": "2026-04-04T00:00:00Z",
  "updated_by": "system"
}
```

**Step 2: Write `naming-rules.json`**

Use this minimal shape:

```json
{
  "version": 1,
  "sub_requirement_id_pattern": "SR-%03d",
  "commit_prefix_template": "[{{subreq_id}}] ",
  "require_commit_prefix": true,
  "updated_at": "2026-04-04T00:00:00Z",
  "updated_by": "system"
}
```

**Step 3: Write `workflow-policy.json`**

Use this minimal shape:

```json
{
  "version": 1,
  "truth_policy": {
    "functional_source": "Requirement",
    "visual_source": "Figma",
    "conflict_behavior": "block"
  },
  "worktree_policy": {
    "require_isolated_worktree": true,
    "allow_precreate_before_dependencies": false
  },
  "logging_policy": {
    "require_logs_for_main_session": true,
    "require_logs_for_subagent": true,
    "require_logs_for_state_change": true
  },
  "updated_at": "2026-04-04T00:00:00Z",
  "updated_by": "system"
}
```

**Step 4: Validate all meta JSON files**

Run:

```bash
jq empty \
  /Users/charvin/Projects/Codex/.ai-delivery/meta/project-binding.json \
  /Users/charvin/Projects/Codex/.ai-delivery/meta/naming-rules.json \
  /Users/charvin/Projects/Codex/.ai-delivery/meta/workflow-policy.json
```

Expected: no output and zero exit status

**Step 5: Assert required keys exist**

Run:

```bash
jq -e '.version and .project_id and .project_root and .specify_path and .ai_delivery_path' /Users/charvin/Projects/Codex/.ai-delivery/meta/project-binding.json && \
jq -e '.version and .sub_requirement_id_pattern and .commit_prefix_template and .require_commit_prefix' /Users/charvin/Projects/Codex/.ai-delivery/meta/naming-rules.json && \
jq -e '.version and .truth_policy and .worktree_policy and .logging_policy' /Users/charvin/Projects/Codex/.ai-delivery/meta/workflow-policy.json
```

Expected: zero exit status

**Step 6: Commit**

Not available until `/Users/charvin/Projects/Codex` becomes a git repository.

### Task 3: Define The `.ai-delivery/runtime/` Empty-State Contracts

**Files:**
- Create: `/Users/charvin/Projects/Codex/.ai-delivery/runtime/main-branch.json`
- Create: `/Users/charvin/Projects/Codex/.ai-delivery/runtime/dependency-graph.json`
- Create: `/Users/charvin/Projects/Codex/.ai-delivery/runtime/worktrees.json`
- Create: `/Users/charvin/Projects/Codex/.ai-delivery/runtime/task-board.json`
- Create: `/Users/charvin/Projects/Codex/.ai-delivery/runtime/blockers.json`
- Create: `/Users/charvin/Projects/Codex/.ai-delivery/runtime/merge-queue.json`

**Step 1: Write `main-branch.json`**

Use this minimal shape:

```json
{
  "version": 1,
  "branch_name": "main-dev",
  "status": "configured",
  "updated_at": "2026-04-04T00:00:00Z",
  "updated_by": "system"
}
```

**Step 2: Write the empty collection contracts**

Use this minimal shape for `dependency-graph.json`:

```json
{
  "version": 1,
  "requirements": [],
  "edges": [],
  "updated_at": "2026-04-04T00:00:00Z",
  "updated_by": "system"
}
```

Use this minimal shape for `worktrees.json`, `task-board.json`, `blockers.json`, and `merge-queue.json`:

```json
{
  "version": 1,
  "items": [],
  "updated_at": "2026-04-04T00:00:00Z",
  "updated_by": "system"
}
```

**Step 3: Validate the runtime JSON files**

Run:

```bash
jq empty /Users/charvin/Projects/Codex/.ai-delivery/runtime/*.json
```

Expected: no output and zero exit status

**Step 4: Assert the required collection keys exist**

Run:

```bash
jq -e '.version and .branch_name and .status' /Users/charvin/Projects/Codex/.ai-delivery/runtime/main-branch.json && \
jq -e '.version and .requirements and .edges' /Users/charvin/Projects/Codex/.ai-delivery/runtime/dependency-graph.json && \
jq -e '.version and .items' /Users/charvin/Projects/Codex/.ai-delivery/runtime/worktrees.json && \
jq -e '.version and .items' /Users/charvin/Projects/Codex/.ai-delivery/runtime/task-board.json && \
jq -e '.version and .items' /Users/charvin/Projects/Codex/.ai-delivery/runtime/blockers.json && \
jq -e '.version and .items' /Users/charvin/Projects/Codex/.ai-delivery/runtime/merge-queue.json
```

Expected: zero exit status

**Step 5: Commit**

Not available until `/Users/charvin/Projects/Codex` becomes a git repository.

### Task 4: Create A Sample Requirement Package And One Sample Sub-Requirement

**Files:**
- Create: `/Users/charvin/Projects/Codex/.ai-delivery/requirements/example-requirement/requirement.md`
- Create: `/Users/charvin/Projects/Codex/.ai-delivery/requirements/example-requirement/breakdown-summary.md`
- Create: `/Users/charvin/Projects/Codex/.ai-delivery/requirements/example-requirement/global-rules.md`
- Create: `/Users/charvin/Projects/Codex/.ai-delivery/requirements/example-requirement/dependency-graph.json`
- Create: `/Users/charvin/Projects/Codex/.ai-delivery/requirements/example-requirement/sub-requirements/SR-001/README.md`
- Create: `/Users/charvin/Projects/Codex/.ai-delivery/requirements/example-requirement/sub-requirements/SR-001/requirement-slice.md`
- Create: `/Users/charvin/Projects/Codex/.ai-delivery/requirements/example-requirement/sub-requirements/SR-001/dependency.json`
- Create: `/Users/charvin/Projects/Codex/.ai-delivery/requirements/example-requirement/sub-requirements/SR-001/status.json`
- Create: `/Users/charvin/Projects/Codex/.ai-delivery/requirements/example-requirement/sub-requirements/SR-001/traceability.json`
- Create: `/Users/charvin/Projects/Codex/.ai-delivery/requirements/example-requirement/sub-requirements/SR-001/decisions.md`

**Step 1: Create the requirement package tree**

Run:

```bash
mkdir -p /Users/charvin/Projects/Codex/.ai-delivery/requirements/example-requirement/sub-requirements/SR-001
```

Expected: directories exist

**Step 2: Write the Markdown files with minimal but meaningful content**

The sample package should demonstrate:

- one top-level requirement
- one sub-requirement with a clear title
- one placeholder global rule section
- one placeholder decisions log

Use `SR-001` and keep the sample clearly non-production.

**Step 3: Write the requirement-local `dependency-graph.json`**

Use this minimal shape:

```json
{
  "version": 1,
  "requirement_id": "example-requirement",
  "nodes": ["SR-001"],
  "edges": [],
  "updated_at": "2026-04-04T00:00:00Z",
  "updated_by": "system"
}
```

**Step 4: Write the sub-requirement JSON contracts**

Use this minimal shape for `dependency.json`:

```json
{
  "version": 1,
  "subreq_id": "SR-001",
  "depends_on": [],
  "blocks": [],
  "updated_at": "2026-04-04T00:00:00Z",
  "updated_by": "system"
}
```

Use this minimal shape for `status.json`:

```json
{
  "version": 1,
  "subreq_id": "SR-001",
  "state": "draft",
  "blockers": [],
  "updated_at": "2026-04-04T00:00:00Z",
  "updated_by": "system"
}
```

Use this minimal shape for `traceability.json`:

```json
{
  "version": 1,
  "subreq_id": "SR-001",
  "requirement_refs": [],
  "figma_nodes": [],
  "mapping_type": null,
  "confidence": null,
  "conflicts": [],
  "last_verified_at": null,
  "updated_at": "2026-04-04T00:00:00Z",
  "updated_by": "system"
}
```

**Step 5: Validate the sample requirement package JSON**

Run:

```bash
find /Users/charvin/Projects/Codex/.ai-delivery/requirements/example-requirement -name '*.json' -print0 | xargs -0 jq empty
```

Expected: no output and zero exit status

**Step 6: Review the resulting tree**

Run:

```bash
find /Users/charvin/Projects/Codex/.ai-delivery/requirements/example-requirement -maxdepth 4 -type f | sort
```

Expected: all planned files appear exactly once

**Step 7: Commit**

Not available until `/Users/charvin/Projects/Codex` becomes a git repository.

### Task 5: Create A Sample Figma Cache Package

**Files:**
- Create: `/Users/charvin/Projects/Codex/.ai-delivery/figma-cache/example-file-id/structure.json`
- Create: `/Users/charvin/Projects/Codex/.ai-delivery/figma-cache/example-file-id/nodes/example-node.json`
- Create: `/Users/charvin/Projects/Codex/.ai-delivery/figma-cache/example-file-id/comments/example-node.json`
- Create: `/Users/charvin/Projects/Codex/.ai-delivery/figma-cache/example-file-id/tokens/default.json`
- Create: `/Users/charvin/Projects/Codex/.ai-delivery/figma-cache/example-file-id/screenshots/.gitkeep`

**Step 1: Create the example Figma cache tree**

Run:

```bash
mkdir -p \
  /Users/charvin/Projects/Codex/.ai-delivery/figma-cache/example-file-id/nodes \
  /Users/charvin/Projects/Codex/.ai-delivery/figma-cache/example-file-id/comments \
  /Users/charvin/Projects/Codex/.ai-delivery/figma-cache/example-file-id/tokens \
  /Users/charvin/Projects/Codex/.ai-delivery/figma-cache/example-file-id/screenshots
```

Expected: directories exist

**Step 2: Write minimal JSON placeholders**

Use simple non-empty placeholders that prove the structure contract, for example:

- `structure.json` with `version`, `file_id`, `root_nodes`
- `nodes/example-node.json` with `version`, `node_id`, `node_type`
- `comments/example-node.json` with `version`, `node_id`, `items`
- `tokens/default.json` with `version`, `set_name`, `tokens`

**Step 3: Add the screenshot placeholder**

Run:

```bash
touch /Users/charvin/Projects/Codex/.ai-delivery/figma-cache/example-file-id/screenshots/.gitkeep
```

Expected: file exists

**Step 4: Validate the JSON placeholders**

Run:

```bash
find /Users/charvin/Projects/Codex/.ai-delivery/figma-cache/example-file-id -name '*.json' -print0 | xargs -0 jq empty
```

Expected: no output and zero exit status

**Step 5: Commit**

Not available until `/Users/charvin/Projects/Codex` becomes a git repository.

### Task 6: Add Failing Contract Tests For Valid And Invalid `.ai-delivery/` Layouts

**Files:**
- Create: `/Users/charvin/Projects/Codex/tests/test_ai_delivery_contracts.sh`
- Create: `/Users/charvin/Projects/Codex/tests/fixtures/ai-delivery/valid/.ai-delivery/meta/project-binding.json`
- Create: `/Users/charvin/Projects/Codex/tests/fixtures/ai-delivery/valid/.ai-delivery/meta/naming-rules.json`
- Create: `/Users/charvin/Projects/Codex/tests/fixtures/ai-delivery/valid/.ai-delivery/meta/workflow-policy.json`
- Create: `/Users/charvin/Projects/Codex/tests/fixtures/ai-delivery/valid/.ai-delivery/runtime/main-branch.json`
- Create: `/Users/charvin/Projects/Codex/tests/fixtures/ai-delivery/valid/.ai-delivery/runtime/dependency-graph.json`
- Create: `/Users/charvin/Projects/Codex/tests/fixtures/ai-delivery/valid/.ai-delivery/runtime/worktrees.json`
- Create: `/Users/charvin/Projects/Codex/tests/fixtures/ai-delivery/valid/.ai-delivery/runtime/task-board.json`
- Create: `/Users/charvin/Projects/Codex/tests/fixtures/ai-delivery/valid/.ai-delivery/runtime/blockers.json`
- Create: `/Users/charvin/Projects/Codex/tests/fixtures/ai-delivery/valid/.ai-delivery/runtime/merge-queue.json`
- Create: `/Users/charvin/Projects/Codex/tests/fixtures/ai-delivery/invalid-missing-meta/.ai-delivery/runtime/main-branch.json`
- Create: `/Users/charvin/Projects/Codex/tests/fixtures/ai-delivery/invalid-bad-json/.ai-delivery/meta/project-binding.json`

**Step 1: Create the fixture directory roots**

Run:

```bash
mkdir -p \
  /Users/charvin/Projects/Codex/tests/fixtures/ai-delivery/valid/.ai-delivery/{meta,runtime} \
  /Users/charvin/Projects/Codex/tests/fixtures/ai-delivery/invalid-missing-meta/.ai-delivery/runtime \
  /Users/charvin/Projects/Codex/tests/fixtures/ai-delivery/invalid-bad-json/.ai-delivery/meta
```

Expected: directories exist

**Step 2: Populate the valid fixture by copying the minimal contract shapes from Tasks 2 and 3**

Expected: the valid fixture represents a minimal passing `.ai-delivery` layout

**Step 3: Create the intentionally bad fixtures**

- `invalid-missing-meta` should omit the entire `.ai-delivery/meta/` contract set
- `invalid-bad-json` should contain malformed JSON in `project-binding.json`

Expected: both fixtures are intentionally invalid

**Step 4: Write the failing test file**

Use this test shape:

```sh
#!/bin/zsh
set -euo pipefail

SCRIPT="/Users/charvin/Projects/Codex/scripts/validate-ai-delivery-contracts.sh"
VALID_ROOT="/Users/charvin/Projects/Codex/tests/fixtures/ai-delivery/valid"
INVALID_MISSING_META="/Users/charvin/Projects/Codex/tests/fixtures/ai-delivery/invalid-missing-meta"
INVALID_BAD_JSON="/Users/charvin/Projects/Codex/tests/fixtures/ai-delivery/invalid-bad-json"

zsh "$SCRIPT" "$VALID_ROOT"
! zsh "$SCRIPT" "$INVALID_MISSING_META"
! zsh "$SCRIPT" "$INVALID_BAD_JSON"
```

**Step 5: Run the test and verify it fails because the validator does not exist yet**

Run: `zsh /Users/charvin/Projects/Codex/tests/test_ai_delivery_contracts.sh`
Expected: FAIL with “no such file” or equivalent because `/Users/charvin/Projects/Codex/scripts/validate-ai-delivery-contracts.sh` has not been created yet

**Step 6: Commit**

Not available until `/Users/charvin/Projects/Codex` becomes a git repository.

### Task 7: Implement The `.ai-delivery/` Contract Validator Script

**Files:**
- Create: `/Users/charvin/Projects/Codex/scripts/validate-ai-delivery-contracts.sh`
- Modify: `/Users/charvin/Projects/Codex/tests/test_ai_delivery_contracts.sh`

**Step 1: Create the `scripts/` directory**

Run: `mkdir -p /Users/charvin/Projects/Codex/scripts`
Expected: directory exists

**Step 2: Implement the validator script**

The validator should:

- accept a project root path argument
- resolve `.ai-delivery/` under that root
- verify the required directories exist
- verify the required meta and runtime JSON files exist
- validate all required JSON files with `jq empty`
- assert the presence of key fields using `jq -e`
- return non-zero on any contract violation

Use this starting shape:

```sh
#!/bin/zsh
set -euo pipefail

ROOT="${1:?project root required}"
AI_DELIVERY_ROOT="$ROOT/.ai-delivery"

require_path() {
  local path="$1"
  [[ -e "$path" ]] || { echo "missing: $path" >&2; return 1; }
}

require_json_keys() {
  local path="$1"
  local expr="$2"
  jq -e "$expr" "$path" >/dev/null
}
```

**Step 3: Syntax-check the validator script**

Run: `zsh -n /Users/charvin/Projects/Codex/scripts/validate-ai-delivery-contracts.sh`
Expected: no output and zero exit status

**Step 4: Re-run the contract tests and verify they now pass**

Run: `zsh /Users/charvin/Projects/Codex/tests/test_ai_delivery_contracts.sh`
Expected: PASS

**Step 5: Commit**

Not available until `/Users/charvin/Projects/Codex` becomes a git repository.

### Task 8: Validate The Real Workspace `.ai-delivery/` Tree Against The New Contract

**Files:**
- Verify: `/Users/charvin/Projects/Codex/.ai-delivery/**`
- Verify: `/Users/charvin/Projects/Codex/scripts/validate-ai-delivery-contracts.sh`
- Verify: `/Users/charvin/Projects/Codex/tests/test_ai_delivery_contracts.sh`

**Step 1: Run the validator against the real workspace**

Run: `zsh /Users/charvin/Projects/Codex/scripts/validate-ai-delivery-contracts.sh /Users/charvin/Projects/Codex`
Expected: PASS

**Step 2: Review the final project-local data tree**

Run:

```bash
find /Users/charvin/Projects/Codex/.ai-delivery -maxdepth 5 -print | sort
```

Expected: all planned directories, sample requirement artifacts, sample Figma cache artifacts, runtime files, meta files, and log files are present

**Step 3: Review the test and validator outputs together**

Run:

```bash
zsh /Users/charvin/Projects/Codex/tests/test_ai_delivery_contracts.sh && \
zsh /Users/charvin/Projects/Codex/scripts/validate-ai-delivery-contracts.sh /Users/charvin/Projects/Codex
```

Expected: both commands pass with no unexpected output

**Step 4: Commit**

Not available until `/Users/charvin/Projects/Codex` becomes a git repository.

## Handoff After Implementation

After this plan is implemented and verified, the next eligible execution plans are:

- `ai-delivery-admin execution plan`
- `skills & mcp execution plan`

Both downstream tracks depend on the project-local data contract remaining stable. If either downstream plan needs to change the structure or semantics of `.ai-delivery/`, that change must first be reconciled against the governing master plan at `/Users/charvin/Projects/Codex/docs/plans/2026-04-04-ai-delivery-implementation-plan.md` before implementation proceeds.
