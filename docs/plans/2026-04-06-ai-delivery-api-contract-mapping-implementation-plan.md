# AI Delivery API Contract Mapping Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a governed `api-contract-mapping` stage, artifact, and traceability subtree across `Codex` and `ai-delivery-admin` without breaking existing workflow contracts.

**Architecture:** Keep `.ai-delivery/` inside the business project as the only workflow truth, add one new sub-requirement artifact `api-contract-mapping.md`, and extend `traceability.json` with a dedicated `api_contract_mapping` subtree whose ownership belongs only to the new stage. Update project-local skills, fixture contracts, validation scripts, and admin read/write surfaces in lockstep so the new stage is both executable and inspectable end to end.

**Tech Stack:** Project-local Markdown skills and templates, shell validators, fixture-driven shell tests, Zod schemas, Node file adapters, Hono server routes, MCP write tools, React + TypeScript admin UI, and Vitest.

---

### Task 1: Add the approved design and plan artifacts

**Files:**
- Create: `/Users/charvin/Projects/spec-dev/Codex/docs/plans/2026-04-06-ai-delivery-api-contract-mapping-design.md`
- Create: `/Users/charvin/Projects/spec-dev/Codex/docs/plans/2026-04-06-ai-delivery-api-contract-mapping-implementation-plan.md`

**Step 1: Write the design doc**

Include:

- workflow position
- artifact and schema contract
- blocker and revalidation rules
- Codex and admin adaptation scope

**Step 2: Verify the files exist**

Run:

```bash
test -f /Users/charvin/Projects/spec-dev/Codex/docs/plans/2026-04-06-ai-delivery-api-contract-mapping-design.md
test -f /Users/charvin/Projects/spec-dev/Codex/docs/plans/2026-04-06-ai-delivery-api-contract-mapping-implementation-plan.md
```

Expected: zero exit status

**Step 3: Commit the planning docs**

```bash
git -C /Users/charvin/Projects/spec-dev/Codex add docs/plans/2026-04-06-ai-delivery-api-contract-mapping-design.md docs/plans/2026-04-06-ai-delivery-api-contract-mapping-implementation-plan.md
git -C /Users/charvin/Projects/spec-dev/Codex commit -m "docs: add api contract mapping design and plan"
```

### Task 2: Write failing Codex contract tests for the new stage

**Files:**
- Modify: `/Users/charvin/Projects/spec-dev/Codex/tests/ai-delivery-contracts/zero-based-flow.test.sh`
- Modify: `/Users/charvin/Projects/spec-dev/Codex/scripts/validate-full-chain-repair-contracts.sh`
- Modify: `/Users/charvin/Projects/spec-dev/Codex/tests/ai-delivery-skills/validate-sources.test.sh`

**Step 1: Write failing checks for new artifact and traceability subtree**

Add expectations for:

- `api-contract-mapping.md` exists in the fixture
- `traceability.json` contains `api_contract_mapping`
- the traceability subtree records a valid `status`

**Step 2: Run tests to verify they fail**

Run:

```bash
zsh /Users/charvin/Projects/spec-dev/Codex/tests/ai-delivery-contracts/zero-based-flow.test.sh
zsh /Users/charvin/Projects/spec-dev/Codex/scripts/validate-full-chain-repair-contracts.sh
```

Expected: FAIL because the new artifact and subtree do not exist yet

**Step 3: Commit the failing-test checkpoint only after implementation is ready**

No commit in red state.

### Task 3: Implement the new project-local `api-contract-mapping` skill package

**Files:**
- Create: `/Users/charvin/Projects/spec-dev/Codex/.agents/skills/ai-delivery/api-contract-mapping/SKILL.md`
- Create: `/Users/charvin/Projects/spec-dev/Codex/.agents/skills/ai-delivery/api-contract-mapping/agents/openai.yaml`
- Create: `/Users/charvin/Projects/spec-dev/Codex/.agents/skills/ai-delivery/api-contract-mapping/references/blocker-catalog.md`
- Create: `/Users/charvin/Projects/spec-dev/Codex/.agents/skills/ai-delivery/api-contract-mapping/references/checklist.md`
- Create: `/Users/charvin/Projects/spec-dev/Codex/.agents/skills/ai-delivery/api-contract-mapping/references/dual-truth-rules.md`
- Create: `/Users/charvin/Projects/spec-dev/Codex/.agents/skills/ai-delivery/api-contract-mapping/references/logging-checklist.md`
- Create: `/Users/charvin/Projects/spec-dev/Codex/.agents/skills/ai-delivery/api-contract-mapping/templates/api-contract-mapping-template.md`

**Step 1: Write the failing skill-validator expectation**

Add validator requirements for:

- `api-contract-mapping.md`
- Swagger / OpenAPI / contract parsing guidance
- `traceability.json`
- `downstream_revalidation`
- new API blockers

**Step 2: Run validator to verify failure**

Run:

```bash
zsh /Users/charvin/Projects/spec-dev/Codex/scripts/validate-project-ai-delivery-skills.sh
```

Expected: FAIL because the new skill package is still missing

**Step 3: Implement the minimal skill package**

Write:

- `SKILL.md` with a governed API contract mapping workflow
- local references and checklist
- `api-contract-mapping-template.md`
- copied or adapted local blocker, dual-truth, and logging references

**Step 4: Run validator to verify pass**

Run:

```bash
zsh /Users/charvin/Projects/spec-dev/Codex/scripts/validate-project-ai-delivery-skills.sh
```

Expected: PASS

**Step 5: Commit**

```bash
git -C /Users/charvin/Projects/spec-dev/Codex add .agents/skills/ai-delivery/api-contract-mapping scripts/validate-project-ai-delivery-skills.sh
git -C /Users/charvin/Projects/spec-dev/Codex commit -m "feat: add api contract mapping skill"
```

### Task 4: Update existing Codex skills and fixtures for the new chain stage

**Files:**
- Modify: `/Users/charvin/Projects/spec-dev/Codex/.agents/skills/ai-delivery/requirement-breakdown/SKILL.md`
- Modify: `/Users/charvin/Projects/spec-dev/Codex/.agents/skills/ai-delivery/requirement-breakdown/references/checklist.md`
- Modify: `/Users/charvin/Projects/spec-dev/Codex/.agents/skills/ai-delivery/requirement-breakdown/references/subreq-readme-template.md`
- Modify: `/Users/charvin/Projects/spec-dev/Codex/.agents/skills/ai-delivery/requirement-breakdown/templates/requirement-slice-template.md`
- Modify: `/Users/charvin/Projects/spec-dev/Codex/.agents/skills/ai-delivery/ui-requirement-mapping/SKILL.md`
- Modify: `/Users/charvin/Projects/spec-dev/Codex/.agents/skills/ai-delivery/ui-interaction-design/SKILL.md`
- Modify: `/Users/charvin/Projects/spec-dev/Codex/.ai-delivery/requirements/example-requirement/sub-requirements/SR-001/traceability.json`
- Create: `/Users/charvin/Projects/spec-dev/Codex/.ai-delivery/requirements/example-requirement/sub-requirements/SR-001/api-contract-mapping.md`

**Step 1: Write the failing fixture check**

Re-run:

```bash
zsh /Users/charvin/Projects/spec-dev/Codex/tests/ai-delivery-contracts/zero-based-flow.test.sh
```

Expected: FAIL because the fixture lacks the new artifact and subtree

**Step 2: Implement minimal governed fixture**

Add:

- `api-contract-mapping.md` with markdown metadata
- `traceability.json.api_contract_mapping`
- requirement-breakdown initialization guidance
- downstream skill ownership language

**Step 3: Re-run contract tests**

Run:

```bash
zsh /Users/charvin/Projects/spec-dev/Codex/tests/ai-delivery-contracts/zero-based-flow.test.sh
zsh /Users/charvin/Projects/spec-dev/Codex/scripts/validate-full-chain-repair-contracts.sh
```

Expected: PASS

**Step 4: Commit**

```bash
git -C /Users/charvin/Projects/spec-dev/Codex add .agents/skills/ai-delivery/requirement-breakdown .agents/skills/ai-delivery/ui-requirement-mapping .agents/skills/ai-delivery/ui-interaction-design .ai-delivery/requirements/example-requirement tests/ai-delivery-contracts scripts/validate-full-chain-repair-contracts.sh
git -C /Users/charvin/Projects/spec-dev/Codex commit -m "feat: wire api contract mapping into ai delivery chain"
```

### Task 5: Update Codex docs and onboarding to describe the optional API stage

**Files:**
- Modify: `/Users/charvin/Projects/spec-dev/Codex/docs/guides/ai-delivery-any-repo-onboarding.md`
- Modify: `/Users/charvin/Projects/spec-dev/Codex/scripts/validate-project-ai-delivery-skills.sh`

**Step 1: Write failing doc/validator expectation if needed**

Ensure the skill validator or doc wording checks require the new stage mention.

**Step 2: Implement docs**

Document:

- default stage order
- optional late-arrival API rerun
- parallel-safe ownership of `traceability.json`

**Step 3: Verify**

Run:

```bash
zsh /Users/charvin/Projects/spec-dev/Codex/scripts/validate-project-ai-delivery-skills.sh
```

Expected: PASS

**Step 4: Commit**

```bash
git -C /Users/charvin/Projects/spec-dev/Codex add docs/guides/ai-delivery-any-repo-onboarding.md scripts/validate-project-ai-delivery-skills.sh
git -C /Users/charvin/Projects/spec-dev/Codex commit -m "docs: describe api contract mapping stage"
```

### Task 6: Write failing ai-delivery-admin shared and server tests

**Files:**
- Modify: `/Users/charvin/Projects/spec-dev/ai-delivery-admin/tests/shared/contracts.test.ts`
- Modify: `/Users/charvin/Projects/spec-dev/ai-delivery-admin/tests/server/write-api.test.ts`
- Modify: `/Users/charvin/Projects/spec-dev/ai-delivery-admin/tests/server/requirement-bootstrap.test.ts`
- Modify: `/Users/charvin/Projects/spec-dev/ai-delivery-admin/tests/mcp/write-tools.test.ts`
- Modify: `/Users/charvin/Projects/spec-dev/ai-delivery-admin/tests/mcp/read-tools.test.ts`
- Modify: `/Users/charvin/Projects/spec-dev/ai-delivery-admin/tests/web/traceability.test.tsx`
- Modify: `/Users/charvin/Projects/spec-dev/ai-delivery-admin/tests/web/artifact-editor.test.tsx`

**Step 1: Add tests for the new schema and artifact type**

Cover:

- `api_contract_mapping` in traceability schema
- `api_contract_mapping` stage rendering
- `api_contract_mapping` artifact type in write APIs
- bootstrap fixture compatibility

**Step 2: Run targeted tests to verify failure**

Run:

```bash
cd /Users/charvin/Projects/spec-dev/ai-delivery-admin && npm test -- tests/shared/contracts.test.ts tests/server/write-api.test.ts tests/server/requirement-bootstrap.test.ts tests/mcp/read-tools.test.ts tests/mcp/write-tools.test.ts tests/web/traceability.test.tsx tests/web/artifact-editor.test.tsx
```

Expected: FAIL because schema, artifact enums, and UI do not yet support the new stage

**Step 3: Commit only after green**

No commit in red state.

### Task 7: Implement ai-delivery-admin schema, adapter, server, and web support

**Files:**
- Modify: `/Users/charvin/Projects/spec-dev/ai-delivery-admin/shared/src/schemas/artifact.ts`
- Modify: `/Users/charvin/Projects/spec-dev/ai-delivery-admin/shared/src/schemas/requirement.ts`
- Modify: `/Users/charvin/Projects/spec-dev/ai-delivery-admin/shared/src/index.ts`
- Modify: `/Users/charvin/Projects/spec-dev/ai-delivery-admin/adapters/src/requirements.ts`
- Modify: `/Users/charvin/Projects/spec-dev/ai-delivery-admin/adapters/src/traceability.ts`
- Modify: `/Users/charvin/Projects/spec-dev/ai-delivery-admin/server/src/services/artifact-service.ts`
- Modify: `/Users/charvin/Projects/spec-dev/ai-delivery-admin/server/src/services/bootstrap-service.ts`
- Modify: `/Users/charvin/Projects/spec-dev/ai-delivery-admin/web/src/lib/types.ts`
- Modify: `/Users/charvin/Projects/spec-dev/ai-delivery-admin/web/src/lib/workflow-chain.ts`
- Modify: `/Users/charvin/Projects/spec-dev/ai-delivery-admin/web/src/components/ArtifactPreview.tsx`
- Modify: `/Users/charvin/Projects/spec-dev/ai-delivery-admin/web/src/components/TraceabilityChain.tsx`

**Step 1: Implement minimal schema changes**

Add:

- governed artifact type `api_contract_mapping`
- `Traceability.api_contract_mapping`
- API status enum and nested fields

**Step 2: Implement adapter and bootstrap changes**

Support:

- reading the new subtree
- returning the new artifact path when present
- seeding minimal bootstrap values without breaking older fixtures

**Step 3: Implement server write logic**

Allow:

- create-on-first-write for `api-contract-mapping.md`
- traceability updates that include `api_contract_mapping`

**Step 4: Implement UI stage rendering**

Show:

- API Contract stage between Requirement and UI Mapping
- status, operations, gaps, conflicts, and revalidation hints

**Step 5: Run targeted tests to verify pass**

Run:

```bash
cd /Users/charvin/Projects/spec-dev/ai-delivery-admin && npm test -- tests/shared/contracts.test.ts tests/server/write-api.test.ts tests/server/requirement-bootstrap.test.ts tests/mcp/read-tools.test.ts tests/mcp/write-tools.test.ts tests/web/traceability.test.tsx tests/web/artifact-editor.test.tsx
```

Expected: PASS

**Step 6: Commit**

```bash
git -C /Users/charvin/Projects/spec-dev/ai-delivery-admin add shared adapters server web tests
git -C /Users/charvin/Projects/spec-dev/ai-delivery-admin commit -m "feat: support api contract mapping artifacts"
```

### Task 8: Run full verification across both repos

**Files:**
- Verify only

**Step 1: Run Codex verification**

Run:

```bash
zsh /Users/charvin/Projects/spec-dev/Codex/tests/ai-delivery-skills/validate-sources.test.sh
zsh /Users/charvin/Projects/spec-dev/Codex/tests/ai-delivery-contracts/zero-based-flow.test.sh
zsh /Users/charvin/Projects/spec-dev/Codex/scripts/validate-full-chain-repair-contracts.sh
```

Expected: PASS

**Step 2: Run ai-delivery-admin verification**

Run:

```bash
cd /Users/charvin/Projects/spec-dev/ai-delivery-admin && npm test -- tests/shared/contracts.test.ts tests/server/write-api.test.ts tests/server/requirement-bootstrap.test.ts tests/mcp/read-tools.test.ts tests/mcp/write-tools.test.ts tests/web/traceability.test.tsx tests/web/artifact-editor.test.tsx
```

Expected: PASS

**Step 3: Review git state**

Run:

```bash
git -C /Users/charvin/Projects/spec-dev/Codex status --short
git -C /Users/charvin/Projects/spec-dev/ai-delivery-admin status --short
```

Expected: only intended tracked changes or clean working trees after commit

**Step 4: Final commit if anything remains**

```bash
git -C /Users/charvin/Projects/spec-dev/Codex add -A
git -C /Users/charvin/Projects/spec-dev/Codex commit -m "chore: finish api contract mapping rollout"
git -C /Users/charvin/Projects/spec-dev/ai-delivery-admin add -A
git -C /Users/charvin/Projects/spec-dev/ai-delivery-admin commit -m "chore: finish api contract mapping admin rollout"
```
