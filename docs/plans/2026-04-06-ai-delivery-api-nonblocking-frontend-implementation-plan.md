# AI Delivery API Non-Blocking Frontend Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Rework the project-local `ai-delivery` skills so missing or partial API contracts do not block early frontend stages, while still preserving governed escalation when API truth would make current-stage output materially wrong.

**Architecture:** Keep the existing `api_contract_mapping` artifact and traceability subtree, but rewrite the workflow semantics across the relevant skills. The implementation should focus on documentation, templates, checklists, examples, and validator coverage so the governed chain consistently treats API protocol work as optional early-stage context and stronger late-stage implementation context.

**Tech Stack:** Markdown skill docs, governed templates under `.agents/skills/ai-delivery/`, shell-based repo contract tests under `tests/ai-delivery-*`, and repository validation scripts.

---

### Task 1: Add failing contract coverage for the new non-blocking API policy

**Files:**
- Create: `tests/ai-delivery-skills/api-nonblocking-policy.test.sh`
- Modify: `tests/ai-delivery-skills/validate-sources.test.sh`

**Step 1: Write the failing test**

Add a shell-based policy test that asserts:

- `api-contract-mapping/SKILL.md` no longer treats missing API contracts as a default blocker for early frontend stages
- the skill text contains non-blocking language around placeholders, known gaps, or integration risks
- downstream skills explicitly state that API incompleteness does not gate requirement breakdown, UI mapping, or interaction design

**Step 2: Run test to verify it fails**

Run: `zsh tests/ai-delivery-skills/api-nonblocking-policy.test.sh`
Expected: FAIL because the current skill docs still encode blocker-first wording.

**Step 3: Hook the test into the existing validation entrypoint**

Update `tests/ai-delivery-skills/validate-sources.test.sh` so the new policy test runs alongside the existing structural checks.

**Step 4: Run the validation wrapper to confirm the red state**

Run: `zsh tests/ai-delivery-skills/validate-sources.test.sh`
Expected: FAIL because the new policy contract is not implemented yet.

**Step 5: Commit**

```bash
git add tests/ai-delivery-skills/api-nonblocking-policy.test.sh tests/ai-delivery-skills/validate-sources.test.sh
git commit -m "test: add non-blocking api skill policy coverage"
```

### Task 2: Rework `api-contract-mapping` from gatekeeper to late-binding context stage

**Files:**
- Modify: `.agents/skills/ai-delivery/api-contract-mapping/SKILL.md`
- Modify: `.agents/skills/ai-delivery/api-contract-mapping/references/checklist.md`
- Modify: `.agents/skills/ai-delivery/api-contract-mapping/references/blocker-catalog.md`
- Modify: `.agents/skills/ai-delivery/api-contract-mapping/references/logging-checklist.md`
- Modify: `.agents/skills/ai-delivery/api-contract-mapping/templates/api-contract-mapping-template.md`

**Step 1: Update the failing expectations mentally against the current files**

Open each file and identify wording that currently:

- treats missing API contract material as a default blocker
- fails to distinguish `known_gap`, `integration_risk`, and `blocking_conflict`
- lacks reservation-point or deferred-implementation guidance

**Step 2: Write minimal doc changes that satisfy the new policy**

Implement these changes:

- rewrite the skill overview and missing-input handling so no-contract and partial-contract cases can still complete
- narrow blocker rules to user-visible distortion cases
- add template sections or guidance for frontend reservation points, known gaps, integration risks, and revalidation triggers
- clarify that `blocked_missing_api_contract` is rare in these early stages and not the default response

**Step 3: Run the new policy test**

Run: `zsh tests/ai-delivery-skills/api-nonblocking-policy.test.sh`
Expected: still FAIL until all relevant skills are updated.

**Step 4: Run the structural validator**

Run: `zsh tests/ai-delivery-skills/validate-sources.test.sh`
Expected: may still FAIL if upstream/downstream skill docs are not yet aligned.

**Step 5: Commit**

```bash
git add .agents/skills/ai-delivery/api-contract-mapping
git commit -m "docs: relax api contract mapping gatekeeping"
```

### Task 3: Update upstream breakdown semantics so API absence never destabilizes requirement slicing

**Files:**
- Modify: `.agents/skills/ai-delivery/requirement-breakdown/SKILL.md`
- Modify: `.agents/skills/ai-delivery/requirement-breakdown/references/checklist.md`
- Modify: `.agents/skills/ai-delivery/requirement-breakdown/references/subreq-readme-template.md`
- Modify: `.agents/skills/ai-delivery/requirement-breakdown/templates/requirement-slice-template.md`

**Step 1: Add requirement-breakdown-specific acceptance criteria**

Ensure the docs make clear that:

- API incompleteness does not reduce slice readiness
- `api-contract-mapping.md` should be seeded as a placeholder, not as an early pass/fail gate
- breakdown outputs should capture only requirement truth plus deferred API context

**Step 2: Apply the minimal documentation edits**

Update wording in the skill and templates so generated artifacts consistently describe API material as optional early-stage context and later integration guidance.

**Step 3: Re-run the policy validator**

Run: `zsh tests/ai-delivery-skills/api-nonblocking-policy.test.sh`
Expected: closer to passing but may still fail on downstream skills.

**Step 4: Re-run the structural validator**

Run: `zsh tests/ai-delivery-skills/validate-sources.test.sh`
Expected: PASS or fail only for remaining downstream-policy gaps.

**Step 5: Commit**

```bash
git add .agents/skills/ai-delivery/requirement-breakdown
git commit -m "docs: make requirement breakdown api-agnostic"
```

### Task 4: Update UI stages to consume API context as optional support, not readiness criteria

**Files:**
- Modify: `.agents/skills/ai-delivery/ui-requirement-mapping/SKILL.md`
- Modify: `.agents/skills/ai-delivery/ui-requirement-mapping/references/mapping-checklist.md`
- Modify: `.agents/skills/ai-delivery/ui-interaction-design/SKILL.md`
- Modify: `.agents/skills/ai-delivery/ui-interaction-design/references/state-checklist.md`
- Modify: `.agents/skills/ai-delivery/ui-interaction-design/references/interaction-quality-guidelines.md`

**Step 1: Define the downstream rule**

Document that:

- missing or partial API truth does not stop UI mapping or interaction design
- API context matters only when it changes user-visible structure, states, or flows
- implementation-binding gaps should be called out as reservation points or risks, not blockers

**Step 2: Apply the minimal doc edits**

Rewrite relevant sections so the UI stages preserve API traceability but do not gate on API completeness.

**Step 3: Run the policy validator**

Run: `zsh tests/ai-delivery-skills/api-nonblocking-policy.test.sh`
Expected: PASS if all stage docs are aligned.

**Step 4: Run the structural validator**

Run: `zsh tests/ai-delivery-skills/validate-sources.test.sh`
Expected: PASS.

**Step 5: Commit**

```bash
git add .agents/skills/ai-delivery/ui-requirement-mapping .agents/skills/ai-delivery/ui-interaction-design
git commit -m "docs: make ui stages tolerant of api gaps"
```

### Task 5: Align examples, onboarding guidance, and governed fixtures with the new posture

**Files:**
- Modify: `docs/guides/ai-delivery-any-repo-onboarding.md`
- Modify: `.ai-delivery/requirements/example-requirement/sub-requirements/SR-001/api-contract-mapping.md`
- Modify: `.ai-delivery/requirements/example-requirement/sub-requirements/SR-001/traceability.json`
- Modify: `scripts/validate-full-chain-repair-contracts.sh`
- Modify: `tests/ai-delivery-contracts/zero-based-flow.test.sh`

**Step 1: Update the example artifact semantics**

Revise the example `api-contract-mapping.md` and traceability data so they show:

- placeholder or partial API context is normal
- ordinary missing contract details do not imply blocked status

**Step 2: Update user-facing chain docs**

Refresh onboarding and validation wording so the repo guidance reflects the new non-blocking model.

**Step 3: Update any fixture or validation assertions that still imply blocker-first API behavior**

Keep existing shape validation, but align the sample meanings and messages to the new posture.

**Step 4: Run contract checks**

Run:

- `zsh tests/ai-delivery-contracts/zero-based-flow.test.sh`
- `zsh scripts/validate-full-chain-repair-contracts.sh`

Expected: PASS.

**Step 5: Commit**

```bash
git add docs/guides/ai-delivery-any-repo-onboarding.md .ai-delivery/requirements/example-requirement/sub-requirements/SR-001/api-contract-mapping.md .ai-delivery/requirements/example-requirement/sub-requirements/SR-001/traceability.json scripts/validate-full-chain-repair-contracts.sh tests/ai-delivery-contracts/zero-based-flow.test.sh
git commit -m "docs: align fixtures with non-blocking api policy"
```

### Task 6: Final verification and single implementation commit if batching was used

**Files:**
- Modify: `docs/plans/2026-04-06-ai-delivery-api-nonblocking-frontend-design.md` only if correction notes are needed
- Modify: `docs/plans/2026-04-06-ai-delivery-api-nonblocking-frontend-implementation-plan.md` only if execution notes are needed

**Step 1: Run the complete validation set**

Run:

- `zsh tests/ai-delivery-skills/validate-sources.test.sh`
- `zsh tests/ai-delivery-contracts/zero-based-flow.test.sh`
- `zsh scripts/validate-full-chain-repair-contracts.sh`
- `zsh tests/ai-delivery-skills/bootstrap-project.test.sh`

Expected: PASS for all commands.

**Step 2: Review the git diff**

Run: `git diff --stat HEAD~1..HEAD` or `git status --short`
Expected: only intended skill/doc/template/example changes remain.

**Step 3: Write any minimal correction patch if a validator exposed a mismatch**

Keep fixes narrow and avoid introducing new schema churn unless a validator proves it necessary.

**Step 4: Re-run the failed validator if any correction was needed**

Expected: PASS.

**Step 5: Commit**

```bash
git add .agents/skills/ai-delivery docs/guides/ai-delivery-any-repo-onboarding.md .ai-delivery/requirements/example-requirement tests/ai-delivery-skills tests/ai-delivery-contracts scripts/validate-full-chain-repair-contracts.sh docs/plans/2026-04-06-ai-delivery-api-nonblocking-frontend-implementation-plan.md
git commit -m "feat: make ai-delivery api context non-blocking for early frontend stages"
```
