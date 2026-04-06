# AI Delivery Full-Chain Consistency Repair Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Close the remaining contract gaps between project-local skill outputs, `.ai-delivery` truth, `ai-delivery-admin` governed surfaces, and the `.specify` bridge so the workflow is actually governed end to end instead of partially relying on convention.

**Architecture:** Keep `.ai-delivery/` as the only workflow truth in the business project, keep `ai-delivery-admin` as the separate control plane, and split governed writes by semantic class. Bootstrap, dependency sync, state transitions, blocker recovery, traceability bridge updates, and markdown artifact edits should not all flow through one generic JSON merge path. Runtime projections should be derived from canonical requirement data, and governed actions should auto-log so auditability is enforced by the system rather than left to agent discipline.

**Tech Stack:** TypeScript, Node.js, Hono, React, zod, vitest, MCP tool wrappers, project-local workflow skills, `.ai-delivery/` contracts, `.specify/` bridge fixtures.

---

## Verified Current Flow

The current codebase already proves a partial happy path:

1. Bind a project through `ai-delivery-admin`.
2. Read requirements, traceability, and Figma cache state.
3. Update governed artifacts.
4. Enter a blocked state and recover through the HTTP API.
5. Create a downstream sub-requirement.
6. Seed dependency and status data.
7. Finalize merge and unlock downstream work.

The following checks passed during this audit:

- `zsh scripts/validate-project-ai-delivery-skills.sh`
- `zsh scripts/validate-full-chain-repair-contracts.sh`
- `npm test -- tests/server/full-chain-repair-smoke.test.ts tests/mcp/codex-smoke.test.ts tests/mcp/write-tools.test.ts tests/server/requirement-bootstrap.test.ts tests/server/blocker-recovery.test.ts tests/server/merge-finalization.test.ts`

## Repair Targets

- remove governed-write bypasses for status and dependency semantics
- expose blocker resolution to agents through MCP, not only HTTP or test-only service access
- choose and enforce one dependency truth flow instead of letting three representations drift
- auto-log governed actions and honor workflow policy at runtime
- realign bootstrap ownership with the three project-local skills
- bring the Web console to the same governed scope promised by the design docs

### Task 1: Remove Generic JSON Governance Bypasses

**Files:**
- Modify: `/Users/charvin/Projects/ai-delivery-admin/server/src/services/artifact-service.ts`
- Modify: `/Users/charvin/Projects/ai-delivery-admin/shared/src/schemas/artifact.ts`
- Modify: `/Users/charvin/Projects/ai-delivery-admin/mcp-server/src/tools/artifacts.ts`
- Modify: `/Users/charvin/Projects/ai-delivery-admin/server/src/routes/artifacts.ts`
- Modify: `/Users/charvin/Projects/ai-delivery-admin/web/src/lib/types.ts`
- Modify: `/Users/charvin/Projects/ai-delivery-admin/web/src/App.tsx`
- Test: `/Users/charvin/Projects/ai-delivery-admin/tests/mcp/write-tools.test.ts`
- Test: `/Users/charvin/Projects/ai-delivery-admin/tests/server/full-chain-repair-smoke.test.ts`

**Step 1: Write failing tests for forbidden generic writes**

- Prove `upsert_artifact` rejects direct mutation of `status.json`.
- Prove `upsert_artifact` rejects direct mutation of dependency truth files.
- Keep markdown artifact writes passing.

**Step 2: Split artifact editing by semantic class**

- Keep generic governed editing only for markdown documents and other safe, schema-validated content.
- Move `status.json` changes behind transition and resume services only.
- Move dependency truth changes behind a dedicated dependency sync service.

**Step 3: Add artifact-specific validation**

- Parse each allowed JSON artifact with its real schema before writing.
- Reject writes that would create illegal states, missing bridge fields, or malformed dependency data.
- Return explicit validation errors instead of accepting opaque `Record<string, unknown>` merges.

**Step 4: Remove unsafe UI affordances**

- Remove direct `status` and raw dependency editing from the Web artifact editor.
- Keep the UI aligned with the narrowed governed artifact surface.

**Step 5: Re-run targeted verification**

- `npm test -- tests/mcp/write-tools.test.ts tests/server/full-chain-repair-smoke.test.ts`

### Task 2: Expose Blocker Resolution Through MCP

**Files:**
- Modify: `/Users/charvin/Projects/ai-delivery-admin/mcp-server/src/tools/blockers.ts`
- Modify: `/Users/charvin/Projects/ai-delivery-admin/mcp-server/src/tools/index.ts`
- Modify: `/Users/charvin/Projects/ai-delivery-admin/mcp-server/src/context.ts`
- Modify: `/Users/charvin/Projects/ai-delivery-admin/skills/ai-delivery-admin-support/SKILL.md`
- Modify: `/Users/charvin/Projects/ai-delivery-admin/skills/ai-delivery-admin-support/references/tool-usage-order.md`
- Test: `/Users/charvin/Projects/ai-delivery-admin/tests/mcp/write-tools.test.ts`
- Test: `/Users/charvin/Projects/ai-delivery-admin/tests/mcp/codex-smoke.test.ts`

**Step 1: Write a failing MCP recovery test**

- Bind a project.
- Open a blocker through a governed transition.
- Resolve that blocker through MCP instead of direct service access.
- Resume the sub-requirement through MCP.

**Step 2: Add a governed blocker update tool**

- Expose `update_blocker` or `resolve_blocker` in the MCP tool registry.
- Reuse the existing blocker service instead of inventing a second write path.

**Step 3: Align the admin support skill**

- Update the support skill and tool-order reference so blocker closure is part of the documented agent flow.
- Make the skill point to the actual MCP surface instead of an implied future capability.

**Step 4: Re-run targeted verification**

- `npm test -- tests/mcp/write-tools.test.ts tests/mcp/codex-smoke.test.ts`

### Task 3: Make Dependency Truth Canonical And Derived Everywhere Else

**Files:**
- Modify: `/Users/charvin/Projects/ai-delivery-admin/server/src/services/bootstrap-service.ts`
- Modify: `/Users/charvin/Projects/ai-delivery-admin/server/src/services/workflow-service.ts`
- Modify: `/Users/charvin/Projects/ai-delivery-admin/server/src/services/project-service.ts`
- Modify: `/Users/charvin/Projects/ai-delivery-admin/adapters/src/requirements.ts`
- Modify: `/Users/charvin/Projects/Codex/.ai-delivery/requirements/example-requirement/dependency-graph.json`
- Modify: `/Users/charvin/Projects/Codex/.ai-delivery/runtime/dependency-graph.json`
- Modify: `/Users/charvin/Projects/Codex/docs/plans/2026-04-04-ai-delivery-overall-chain-design.md`
- Test: `/Users/charvin/Projects/ai-delivery-admin/tests/server/merge-finalization.test.ts`
- Test: `/Users/charvin/Projects/ai-delivery-admin/tests/server/full-chain-repair-smoke.test.ts`
- Test: `/Users/charvin/Projects/ai-delivery-admin/tests/shared/contracts.test.ts`

**Step 1: Lock the dependency source of truth**

- Treat requirement-level `dependency-graph.json` as the authoring DAG for one requirement.
- Treat per-sub-requirement `dependency.json` as a derived local view.
- Treat `.ai-delivery/runtime/dependency-graph.json` as a derived execution projection.

**Step 2: Add a dependency sync service**

- Regenerate `dependency.json` files and runtime dependency projection from the requirement DAG.
- Run the sync after requirement breakdown bootstrap and after governed dependency edits.
- Refuse to write a graph with cycles or missing sub-requirement targets.

**Step 3: Stop using stale runtime graph data as a passive side file**

- Make execution-board dependency waves come from the regenerated runtime graph.
- Make downstream unlock logic consume the same synchronized dependency truth instead of bypassing it.

**Step 4: Update fixtures and contract tests**

- Refresh Codex and `ai-delivery-admin` fixtures to use the same dependency model.
- Add tests that prove the runtime graph changes when the authoring DAG changes.

**Step 5: Re-run targeted verification**

- `npm test -- tests/server/merge-finalization.test.ts tests/server/full-chain-repair-smoke.test.ts tests/shared/contracts.test.ts`

### Task 4: Auto-Log Governed Actions And Enforce Workflow Policy

**Files:**
- Modify: `/Users/charvin/Projects/ai-delivery-admin/shared/src/schemas/event.ts`
- Modify: `/Users/charvin/Projects/ai-delivery-admin/server/src/services/event-service.ts`
- Modify: `/Users/charvin/Projects/ai-delivery-admin/server/src/services/transition-service.ts`
- Modify: `/Users/charvin/Projects/ai-delivery-admin/server/src/services/blocker-service.ts`
- Modify: `/Users/charvin/Projects/ai-delivery-admin/server/src/services/workflow-service.ts`
- Modify: `/Users/charvin/Projects/ai-delivery-admin/server/src/services/artifact-service.ts`
- Modify: `/Users/charvin/Projects/ai-delivery-admin/adapters/src/events.ts`
- Modify: `/Users/charvin/Projects/Codex/.ai-delivery/meta/workflow-policy.json`
- Test: `/Users/charvin/Projects/ai-delivery-admin/tests/server/blocker-recovery.test.ts`
- Test: `/Users/charvin/Projects/ai-delivery-admin/tests/server/full-chain-repair-smoke.test.ts`
- Test: `/Users/charvin/Projects/ai-delivery-admin/tests/mcp/write-tools.test.ts`

**Step 1: Expand the event contract**

- Add optional structured fields for `status_before`, `status_after`, `artifact_type`, `result`, and human-readable message text.
- Keep `payload` for extensibility.

**Step 2: Add automatic event emission**

- Emit events from transitions, blocker updates, worktree reservation or creation, merge recording, merge finalization, and artifact writes.
- Preserve manual `append_execution_log` for caller-supplied progress messages, but stop relying on it for core governance bookkeeping.

**Step 3: Enforce workflow policy**

- Read `workflow-policy.json` during governed writes.
- If policy says state changes must be logged, treat a logging failure as a failed operation.
- Keep the existing project-local logging checklist as guidance, but back it with runtime enforcement.

**Step 4: Re-run targeted verification**

- `npm test -- tests/server/blocker-recovery.test.ts tests/server/full-chain-repair-smoke.test.ts tests/mcp/write-tools.test.ts`

### Task 5: Realign Bootstrap Ownership With Skill Responsibilities

**Files:**
- Modify: `/Users/charvin/Projects/ai-delivery-admin/server/src/services/bootstrap-service.ts`
- Modify: `/Users/charvin/Projects/Codex/.agents/skills/ai-delivery/requirement-breakdown/SKILL.md`
- Modify: `/Users/charvin/Projects/Codex/.agents/skills/ai-delivery/ui-requirement-mapping/SKILL.md`
- Modify: `/Users/charvin/Projects/Codex/.agents/skills/ai-delivery/ui-interaction-design/SKILL.md`
- Modify: `/Users/charvin/Projects/Codex/.agents/skills/ai-delivery/common/README.md`
- Modify: `/Users/charvin/Projects/Codex/docs/plans/2026-04-04-ai-delivery-overall-chain-design.md`
- Modify: `/Users/charvin/Projects/Codex/docs/plans/2026-04-04-ai-delivery-admin-system-design.md`
- Test: `/Users/charvin/Projects/ai-delivery-admin/tests/server/requirement-bootstrap.test.ts`
- Script: `/Users/charvin/Projects/Codex/scripts/validate-project-ai-delivery-skills.sh`
- Script: `/Users/charvin/Projects/Codex/scripts/validate-full-chain-repair-contracts.sh`

**Step 1: Shrink bootstrap to true intake responsibilities**

- `createRequirementPackage` should create only intake-owned requirement artifacts.
- `createSubRequirementPackage` should create only breakdown-owned bootstrap artifacts and the minimal traceability stub.
- Stop pre-seeding downstream Figma or interaction documents unless the design explicitly reclassifies them as bootstrap placeholders.

**Step 2: Allow first governed write for downstream artifacts**

- If `figma-mapping.md` or `interaction-design.md` does not exist yet, support governed create-on-first-write for those files.
- Preserve explicit version metadata when the first real mapping or interaction contract is written.

**Step 3: Update the skill docs to match runtime truth**

- Make the three project-local skills describe the actual bootstrap, create, and update responsibilities.
- Keep the docs honest about what admin governs versus what the skills originate.

**Step 4: Re-run verification**

- `zsh scripts/validate-project-ai-delivery-skills.sh`
- `zsh scripts/validate-full-chain-repair-contracts.sh`
- `npm test -- tests/server/requirement-bootstrap.test.ts`

### Task 6: Bring The Web Console To Design Parity

**Files:**
- Modify: `/Users/charvin/Projects/ai-delivery-admin/web/src/lib/api.ts`
- Modify: `/Users/charvin/Projects/ai-delivery-admin/web/src/lib/types.ts`
- Modify: `/Users/charvin/Projects/ai-delivery-admin/web/src/App.tsx`
- Modify: `/Users/charvin/Projects/ai-delivery-admin/web/src/pages/BlockerCenterPage.tsx`
- Modify: `/Users/charvin/Projects/ai-delivery-admin/web/src/pages/ArtifactEditorPage.tsx`
- Add or Modify: `/Users/charvin/Projects/ai-delivery-admin/tests/web/*.test.tsx`
- Modify: `/Users/charvin/Projects/Codex/docs/plans/2026-04-04-ai-delivery-admin-system-design.md`

**Step 1: Add blocker actions**

- Add resolve and dismiss controls in the blocker center.
- Add resume entry points where the status model allows it.

**Step 2: Expand governed artifact coverage in the Web UI**

- Support requirement-level artifacts promised in the design doc.
- Add read or edit affordances for `traceability.json` when appropriate.
- Keep raw Figma cache out of the generic artifact editor.

**Step 3: Remove misleading affordances**

- Do not present status or dependency JSON as freeform editable text once Task 1 lands.
- If a capability remains intentionally unsupported in the Web UI, update the design doc so the promise matches the product.

**Step 4: Re-run targeted verification**

- `npm test -- tests/web`

### Task 7: Rebuild The Full-Chain Verification Suite Around The Repaired Contracts

**Files:**
- Modify: `/Users/charvin/Projects/ai-delivery-admin/tests/server/full-chain-repair-smoke.test.ts`
- Modify: `/Users/charvin/Projects/ai-delivery-admin/tests/mcp/codex-smoke.test.ts`
- Modify: `/Users/charvin/Projects/ai-delivery-admin/tests/mcp/write-tools.test.ts`
- Modify: `/Users/charvin/Projects/Codex/scripts/validate-full-chain-repair-contracts.sh`
- Add: `/Users/charvin/Projects/Codex/scripts/verify-ai-delivery-full-chain.sh`

**Step 1: Extend the smoke path**

- Require MCP-based blocker resolution.
- Require dependency sync before downstream unlock.
- Require auto-generated governance events for transitions and merge actions.

**Step 2: Add a single verification entrypoint**

- One shell script should run the skill validator, contract validator, and the critical `ai-delivery-admin` smoke tests in the correct order.

**Step 3: Freeze success criteria**

- A repair is not complete unless the zero-based path works from intake to merge unlock without direct file mutation or test-only service shortcuts.

**Step 4: Final verification command**

- `zsh scripts/verify-ai-delivery-full-chain.sh`

## Exit Criteria

- No governed path can mutate `status.json` or dependency truth through a generic artifact merge.
- Agents can resolve blockers through MCP and then resume through MCP.
- Runtime dependency state is derived from the same dependency truth used for readiness and unlock checks.
- Core governed actions emit events automatically and respect workflow policy.
- Bootstrap behavior matches the documented skill responsibilities.
- The Web console no longer promises governance actions it cannot actually perform.
- The full-chain verification script passes on the canonical Codex fixture and on `ai-delivery-admin` fixtures.
