# AI Delivery Integration Repair And Full-Chain Verification Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Close the remaining cross-track architecture gaps so the AI delivery system can be verified from a zero-based start: requirement bootstrap, governed artifact coverage, blocked-state recovery, merge finalization, Figma cache visibility, and the `.ai-delivery` to `.specify` bridge.

**Architecture:** Implement this as a contract-first repair track across both repositories. Freeze the zero-based host-project fixture in `/Users/charvin/Projects/Codex`, then expand `ai-delivery-admin` schemas, adapters, APIs, MCP tools, and selected Web read surfaces until they can govern the same artifact truth the three project-local skills produce. Use `traceability.json` as the formal cross-layer bridge carrier for Spec Kit references instead of inventing another artifact family.

**Tech Stack:** Host-project hidden directories under `.ai-delivery/` and `.specify/`, shell validators in `Codex`, `TypeScript`, `Node.js`, `Hono`, `React`, `zod`, `vitest`, local MCP tools, and governed JSON or Markdown contract files.

---

### Task 1: Create Paired Worktrees And Capture The Baseline

**Files:**
- No new files

**Step 1: Create an isolated worktree for `/Users/charvin/Projects/Codex`**

Use `superpowers:using-git-worktrees` against:

```text
/Users/charvin/Projects/Codex
```

Suggested branch:

```text
codex/ai-delivery-integration-repair
```

**Step 2: Create an isolated worktree for `/Users/charvin/Projects/ai-delivery-admin`**

Use `superpowers:using-git-worktrees` against:

```text
/Users/charvin/Projects/ai-delivery-admin
```

Suggested branch:

```text
codex/ai-delivery-integration-repair
```

**Step 3: Record the current baseline**

Run:

```bash
git -C /Users/charvin/Projects/Codex status --short && \
git -C /Users/charvin/Projects/ai-delivery-admin status --short
```

Expected: both worktrees are isolated and ready for new feature work.

**Step 4: Run current verification before changing anything**

Run:

```bash
cd /Users/charvin/Projects/ai-delivery-admin && npm run test && npm run typecheck
```

Expected: PASS on the current baseline so later failures are attributable to the repair work.

### Task 2: Freeze A Zero-Based Host-Project Fixture In `Codex`

**Files:**
- Create: `/Users/charvin/Projects/Codex/.specify/fixtures/example-sr-001/spec.md`
- Create: `/Users/charvin/Projects/Codex/.specify/fixtures/example-sr-001/plan.md`
- Create: `/Users/charvin/Projects/Codex/.specify/fixtures/example-sr-001/tasks.md`
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
- Create: `/Users/charvin/Projects/Codex/.ai-delivery/requirements/example-requirement/sub-requirements/SR-001/figma-mapping.md`
- Create: `/Users/charvin/Projects/Codex/.ai-delivery/requirements/example-requirement/sub-requirements/SR-001/interaction-design.md`
- Create: `/Users/charvin/Projects/Codex/scripts/validate-full-chain-repair-contracts.sh`
- Create: `/Users/charvin/Projects/Codex/tests/ai-delivery-contracts/zero-based-flow.test.sh`

**Step 1: Write the failing zero-based shell test**

The shell test should assert that the fixture host now has:

- a requirement package created from zero
- governed artifact coverage files for requirement and sub-requirement levels
- a blocked-recovery-ready `status.json`
- a `traceability.json` that includes `spec_kit_refs`
- `.specify/fixtures/example-sr-001/` targets that the bridge can point to

Run:

```bash
cd /Users/charvin/Projects/Codex && zsh tests/ai-delivery-contracts/zero-based-flow.test.sh
```

Expected: FAIL because the fixture tree does not exist yet.

**Step 2: Create the minimal zero-based fixture**

Use explicit versioned metadata in every editable JSON or Markdown artifact. The initial `traceability.json` should include a minimal bridge stub like:

```json
{
  "version": 1,
  "updated_at": "2026-04-05T00:00:00.000Z",
  "updated_by": "system",
  "requirement_refs": ["REQ-EXAMPLE-001"],
  "figma_nodes": [],
  "mapping_type": "fixture",
  "confidence": "fixture",
  "conflicts": [],
  "last_verified_at": "2026-04-05T00:00:00.000Z",
  "spec_kit_refs": {
    "feature_id": "example-sr-001",
    "spec_path": ".specify/fixtures/example-sr-001/spec.md",
    "plan_path": ".specify/fixtures/example-sr-001/plan.md",
    "tasks_path": ".specify/fixtures/example-sr-001/tasks.md",
    "bridge_status": "seeded",
    "last_synced_at": "2026-04-05T00:00:00.000Z"
  }
}
```

The initial `status.json` should include the normal status plus blocked-recovery placeholders such as:

```json
{
  "version": 1,
  "updated_at": "2026-04-05T00:00:00.000Z",
  "updated_by": "system",
  "status": "interaction_ready",
  "blocked_from_status": null,
  "resume_target_status": null
}
```

**Step 3: Write the validator script**

The validator must fail if:

- required governed artifacts are missing
- `traceability.json` lacks `spec_kit_refs`
- any `spec_kit_refs` path escapes `.specify/`
- blocked recovery fields are absent from `status.json`

**Step 4: Re-run the shell verification**

Run:

```bash
cd /Users/charvin/Projects/Codex && \
zsh scripts/validate-full-chain-repair-contracts.sh && \
zsh tests/ai-delivery-contracts/zero-based-flow.test.sh
```

Expected: PASS

**Step 5: Commit**

```bash
git -C /Users/charvin/Projects/Codex add .specify .ai-delivery scripts tests/ai-delivery-contracts
git -C /Users/charvin/Projects/Codex commit -m "test: add zero-based full-chain fixture"
```

### Task 3: Align Shared Schemas And Adapters With The Repair Contracts

**Files:**
- Modify: `/Users/charvin/Projects/ai-delivery-admin/shared/src/schemas/requirement.ts`
- Modify: `/Users/charvin/Projects/ai-delivery-admin/shared/src/schemas/artifact.ts`
- Modify: `/Users/charvin/Projects/ai-delivery-admin/shared/src/schemas/runtime.ts`
- Create: `/Users/charvin/Projects/ai-delivery-admin/shared/src/schemas/figma-cache.ts`
- Modify: `/Users/charvin/Projects/ai-delivery-admin/shared/src/index.ts`
- Modify: `/Users/charvin/Projects/ai-delivery-admin/adapters/src/requirements.ts`
- Modify: `/Users/charvin/Projects/ai-delivery-admin/adapters/src/traceability.ts`
- Create: `/Users/charvin/Projects/ai-delivery-admin/adapters/src/figma-cache.ts`
- Modify: `/Users/charvin/Projects/ai-delivery-admin/adapters/src/index.ts`
- Modify: `/Users/charvin/Projects/ai-delivery-admin/tests/shared/contracts.test.ts`
- Modify: `/Users/charvin/Projects/ai-delivery-admin/tests/adapters/requirements.test.ts`
- Modify: `/Users/charvin/Projects/ai-delivery-admin/tests/adapters/traceability.test.ts`
- Create: `/Users/charvin/Projects/ai-delivery-admin/tests/adapters/figma-cache.test.ts`

**Step 1: Write or tighten the failing tests first**

Add expectations for:

- requirement-level artifact summaries including `requirement.md`, `breakdown-summary.md`, `global-rules.md`, and `dependency-graph.json`
- sub-requirement summaries including `README.md`
- `traceability.json` support for `spec_kit_refs`
- `status.json` support for `blocked_from_status` and `resume_target_status`
- Figma cache inventory and freshness read models

Run:

```bash
cd /Users/charvin/Projects/ai-delivery-admin && \
npm run test -- tests/shared/contracts.test.ts tests/adapters/requirements.test.ts tests/adapters/traceability.test.ts tests/adapters/figma-cache.test.ts
```

Expected: FAIL

**Step 2: Update the shared schemas and adapters minimally**

Make the schemas and adapters agree on:

- governed artifact coverage
- bridge fields in `traceability.json`
- blocked recovery fields in `status.json`
- a read-only Figma cache inventory shape

Do not add a second bridge artifact type. Keep the bridge contract inside `traceability.json`.

**Step 3: Re-run the schema and adapter tests**

Expected: PASS

**Step 4: Commit**

```bash
git -C /Users/charvin/Projects/ai-delivery-admin add shared adapters tests/shared tests/adapters
git -C /Users/charvin/Projects/ai-delivery-admin commit -m "feat: align repair contracts across schemas and adapters"
```

### Task 4: Implement Governed Bootstrap Create Surfaces And Expand Artifact Coverage

**Files:**
- Modify: `/Users/charvin/Projects/ai-delivery-admin/server/src/services/artifact-service.ts`
- Create: `/Users/charvin/Projects/ai-delivery-admin/server/src/services/bootstrap-service.ts`
- Modify: `/Users/charvin/Projects/ai-delivery-admin/server/src/routes/artifacts.ts`
- Modify: `/Users/charvin/Projects/ai-delivery-admin/server/src/routes/requirements.ts`
- Modify: `/Users/charvin/Projects/ai-delivery-admin/mcp-server/src/tools/artifacts.ts`
- Modify: `/Users/charvin/Projects/ai-delivery-admin/mcp-server/src/tools/requirements.ts`
- Modify: `/Users/charvin/Projects/ai-delivery-admin/mcp-server/src/tools/index.ts`
- Create: `/Users/charvin/Projects/ai-delivery-admin/tests/server/requirement-bootstrap.test.ts`
- Modify: `/Users/charvin/Projects/ai-delivery-admin/tests/server/write-api.test.ts`
- Modify: `/Users/charvin/Projects/ai-delivery-admin/tests/mcp/write-tools.test.ts`

**Step 1: Write the failing bootstrap tests**

Cover at least:

- `create_requirement_package`
- `create_sub_requirement_package`
- expanding `upsert_artifact` to permit all governed artifact classes
- rejecting unsupported create targets or escaped paths
- preserving version metadata on newly created files

Run:

```bash
cd /Users/charvin/Projects/ai-delivery-admin && \
npm run test -- tests/server/requirement-bootstrap.test.ts tests/server/write-api.test.ts tests/mcp/write-tools.test.ts
```

Expected: FAIL

**Step 2: Implement the minimal bootstrap services**

Rules to enforce:

- create must work for zero-based requirement intake and sub-requirement bootstrap
- update must still reject stale versions
- `traceability.json` and `README.md` are now governed artifacts, not local sidecars
- raw Figma cache files remain outside generic artifact create or update editing

**Step 3: Re-run the write-path tests**

Expected: PASS

**Step 4: Commit**

```bash
git -C /Users/charvin/Projects/ai-delivery-admin add server mcp-server tests/server tests/mcp
git -C /Users/charvin/Projects/ai-delivery-admin commit -m "feat: add governed bootstrap and artifact coverage repair"
```

### Task 5: Implement Blocked-State Recovery And Governed Resume Flow

**Files:**
- Modify: `/Users/charvin/Projects/ai-delivery-admin/server/src/services/transition-service.ts`
- Modify: `/Users/charvin/Projects/ai-delivery-admin/server/src/services/blocker-service.ts`
- Modify: `/Users/charvin/Projects/ai-delivery-admin/server/src/routes/transitions.ts`
- Modify: `/Users/charvin/Projects/ai-delivery-admin/server/src/routes/blocker-actions.ts`
- Modify: `/Users/charvin/Projects/ai-delivery-admin/mcp-server/src/tools/transitions.ts`
- Modify: `/Users/charvin/Projects/ai-delivery-admin/shared/src/schemas/runtime.ts`
- Create: `/Users/charvin/Projects/ai-delivery-admin/tests/server/blocker-recovery.test.ts`
- Modify: `/Users/charvin/Projects/ai-delivery-admin/tests/server/write-api.test.ts`
- Modify: `/Users/charvin/Projects/ai-delivery-admin/tests/mcp/write-tools.test.ts`

**Step 1: Write the failing blocker-recovery tests**

Cover:

- entering a blocked state stores `blocked_from_status` and `resume_target_status`
- closing a blocker does not silently advance the workflow
- `resume_sub_requirement_after_blocker` returns the sub-requirement to a legal active state
- illegal resume attempts are rejected and logged

Run:

```bash
cd /Users/charvin/Projects/ai-delivery-admin && \
npm run test -- tests/server/blocker-recovery.test.ts tests/server/write-api.test.ts tests/mcp/write-tools.test.ts
```

Expected: FAIL

**Step 2: Implement the recovery semantics**

The repaired flow must distinguish:

- “blocker closed”
- “sub-requirement resumed”

Those are not the same event.

**Step 3: Re-run the recovery tests**

Expected: PASS

**Step 4: Commit**

```bash
git -C /Users/charvin/Projects/ai-delivery-admin add server shared mcp-server tests/server tests/mcp
git -C /Users/charvin/Projects/ai-delivery-admin commit -m "feat: add blocked-state recovery flow"
```

### Task 6: Implement Merge Finalization, Branch Validation, And Downstream Unlock

**Files:**
- Modify: `/Users/charvin/Projects/ai-delivery-admin/server/src/services/workflow-service.ts`
- Modify: `/Users/charvin/Projects/ai-delivery-admin/server/src/routes/execution.ts`
- Modify: `/Users/charvin/Projects/ai-delivery-admin/mcp-server/src/tools/worktrees.ts`
- Modify: `/Users/charvin/Projects/ai-delivery-admin/shared/src/schemas/runtime.ts`
- Create: `/Users/charvin/Projects/ai-delivery-admin/tests/server/merge-finalization.test.ts`
- Modify: `/Users/charvin/Projects/ai-delivery-admin/tests/server/write-api.test.ts`
- Modify: `/Users/charvin/Projects/ai-delivery-admin/tests/mcp/write-tools.test.ts`
- Modify: `/Users/charvin/Projects/ai-delivery-admin/tests/server/read-api.test.ts`

**Step 1: Write the failing workflow-governance tests**

Cover at least:

- `reserve_worktree_slot` rejects `base_branch` values that do not match `.ai-delivery/runtime/main-branch.json`
- `record_commit` rejects commit messages that do not satisfy `.ai-delivery/meta/naming-rules.json`
- `finalize_merge_and_unlock` updates:
  - `merge-queue.json`
  - `worktrees.json`
  - `status.json`
  - `task-board.json`
  - downstream dependency readiness

Run:

```bash
cd /Users/charvin/Projects/ai-delivery-admin && \
npm run test -- tests/server/merge-finalization.test.ts tests/server/write-api.test.ts tests/server/read-api.test.ts tests/mcp/write-tools.test.ts
```

Expected: FAIL

**Step 2: Implement the merge-finalization orchestrator**

Keep `record_merge_result` as a raw event or queue operation if needed, but do not let it stand in for a full workflow-convergence step.

**Step 3: Re-run the workflow-governance tests**

Expected: PASS

**Step 4: Commit**

```bash
git -C /Users/charvin/Projects/ai-delivery-admin add server shared mcp-server tests/server tests/mcp
git -C /Users/charvin/Projects/ai-delivery-admin commit -m "feat: finalize merge and downstream unlock flow"
```

### Task 7: Add Figma Cache Inventory And Traceability-Based Spec Kit Bridge Visibility

**Files:**
- Create: `/Users/charvin/Projects/ai-delivery-admin/server/src/routes/figma-cache.ts`
- Modify: `/Users/charvin/Projects/ai-delivery-admin/server/src/app.ts`
- Create: `/Users/charvin/Projects/ai-delivery-admin/mcp-server/src/tools/figma-cache.ts`
- Modify: `/Users/charvin/Projects/ai-delivery-admin/mcp-server/src/tools/traceability.ts`
- Modify: `/Users/charvin/Projects/ai-delivery-admin/mcp-server/src/tools/index.ts`
- Modify: `/Users/charvin/Projects/ai-delivery-admin/web/src/lib/api.ts`
- Modify: `/Users/charvin/Projects/ai-delivery-admin/web/src/lib/types.ts`
- Modify: `/Users/charvin/Projects/ai-delivery-admin/web/src/pages/TraceabilityPage.tsx`
- Modify: `/Users/charvin/Projects/ai-delivery-admin/tests/adapters/traceability.test.ts`
- Create: `/Users/charvin/Projects/ai-delivery-admin/tests/server/figma-cache-routes.test.ts`
- Modify: `/Users/charvin/Projects/ai-delivery-admin/tests/mcp/read-tools.test.ts`
- Modify: `/Users/charvin/Projects/ai-delivery-admin/tests/web/traceability.test.tsx`

**Step 1: Write the failing read-surface tests**

Cover:

- listing Figma cache entries and freshness
- exposing `spec_kit_refs` from `traceability.json`
- showing both Figma evidence status and bridge status in the Traceability view

Run:

```bash
cd /Users/charvin/Projects/ai-delivery-admin && \
npm run test -- tests/adapters/traceability.test.ts tests/server/figma-cache-routes.test.ts tests/mcp/read-tools.test.ts tests/web/traceability.test.tsx
```

Expected: FAIL

**Step 2: Implement the minimal read surfaces**

Rules:

- Figma cache remains read-only or index-oriented in admin
- `traceability.json` becomes the formal carrier for bridge visibility
- do not add a new `spec-kit-bridge.json`

**Step 3: Re-run the read-surface tests**

Expected: PASS

**Step 4: Commit**

```bash
git -C /Users/charvin/Projects/ai-delivery-admin add server mcp-server web tests/adapters tests/server tests/mcp tests/web
git -C /Users/charvin/Projects/ai-delivery-admin commit -m "feat: expose figma cache and spec kit bridge visibility"
```

### Task 8: Run Full-Chain Verification Against The Real `Codex` Project And Update Handoff Docs

**Files:**
- Modify: `/Users/charvin/Projects/ai-delivery-admin/README.md`
- Modify: `/Users/charvin/Projects/ai-delivery-admin/mcp-server/README.md`
- Modify: `/Users/charvin/Projects/Codex/.agents/skills/ai-delivery/common/README.md`
- Create: `/Users/charvin/Projects/ai-delivery-admin/tests/server/full-chain-repair-smoke.test.ts`

**Step 1: Write the failing smoke test**

The smoke test should verify that the repaired admin system can:

- bind `/Users/charvin/Projects/Codex`
- read the zero-based fixture package
- create or update governed artifacts without escaping `.ai-delivery/`
- resume a blocked sub-requirement legally
- finalize a merge and expose unlocked downstream state
- expose `spec_kit_refs` and Figma cache status from the same traceability flow

Run:

```bash
cd /Users/charvin/Projects/ai-delivery-admin && npm run test -- tests/server/full-chain-repair-smoke.test.ts
```

Expected: FAIL

**Step 2: Implement the last missing glue only if the smoke test demands it**

Prefer small fixes over new abstractions. This task is for closure, not for a second redesign.

**Step 3: Update the usage docs**

Document at least:

- that full-chain closure depends on governed bootstrap, blocked recovery, merge finalization, and traceability-based Spec Kit bridge refs
- that `traceability.json` is now a first-class governed artifact
- that Figma cache is indexed and freshness-checked, not treated as a generic editable document
- that runtime daemon management remains separate from workflow truth

**Step 4: Run the full verification suite**

Run:

```bash
cd /Users/charvin/Projects/Codex && \
zsh scripts/validate-project-ai-delivery-skills.sh && \
zsh scripts/validate-full-chain-repair-contracts.sh && \
zsh tests/ai-delivery-contracts/zero-based-flow.test.sh
```

Expected: PASS

Run:

```bash
cd /Users/charvin/Projects/ai-delivery-admin && \
npm run test && \
npm run typecheck && \
npm run build:web
```

Expected: PASS

**Step 5: Commit**

```bash
git -C /Users/charvin/Projects/Codex add .specify .ai-delivery .agents/skills scripts tests/ai-delivery-contracts
git -C /Users/charvin/Projects/Codex commit -m "docs: finalize full-chain repair fixtures and contracts"

git -C /Users/charvin/Projects/ai-delivery-admin add README.md mcp-server/README.md server web adapters shared tests
git -C /Users/charvin/Projects/ai-delivery-admin commit -m "test: finalize integration repair and full-chain verification"
```

## Handoff After Implementation

After this plan is implemented and verified:

- the host project can demonstrate a true zero-based `Requirement Intake -> Breakdown -> Mapping -> Interaction -> Spec Kit Bridge -> Runtime Governance` path
- the admin system and project-local skills will be operating over the same governed artifact set
- blocked states will have formal recovery semantics
- merge completion will imply runtime convergence rather than just queue bookkeeping
- `traceability.json` will serve as the cross-layer bridge carrier for both Figma evidence and Spec Kit references

If future work needs to:

- replace the traceability-based bridge with a separate bridge artifact
- move raw Figma evidence into a richer managed storage layer
- redesign the bridge target from `.specify/fixtures/` to a live Spec Kit install
- restructure ownership boundaries between `Codex` and `ai-delivery-admin`

then reconcile that change against:

- `/Users/charvin/Projects/Codex/docs/plans/2026-04-04-ai-delivery-implementation-plan.md`
- `/Users/charvin/Projects/Codex/docs/plans/2026-04-05-ai-delivery-architecture-repair-plan.md`
- `/Users/charvin/Projects/Codex/docs/plans/2026-04-05-ai-delivery-zero-based-flow-audit.md`
