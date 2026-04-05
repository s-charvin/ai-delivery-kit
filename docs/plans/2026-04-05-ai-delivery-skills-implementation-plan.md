# AI Delivery Skills Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement the three project-local AI-delivery workflow skills inside `/Users/charvin/Projects/Codex/.codex/skills/ai-delivery/` so requirement breakdown, UI requirement mapping, and UI interaction design can be executed consistently against the host project's `.ai-delivery/` data contracts.

**Architecture:** Keep all workflow-skill source of truth inside the business project. This execution plan owns only the three project-local skill packages plus their shared references, templates, validators, and local install or sync scripts. It may consume the admin system's governed support surfaces when available, but it does not implement the admin support skill, the MCP server, or the `ai-delivery-admin` application itself.

**Tech Stack:** Project-local `SKILL.md` packages, Markdown references and templates, shell validation scripts, fixture-driven shell tests, and local Codex skill-install or sync helpers.

---

> Clarification: this plan owns only the three project-local workflow skills. The separate `ai-delivery-admin` execution plan owns the admin support skill and the MCP server.

> Readiness note: this plan can scaffold project-local skill sources as soon as the host project data contract exists, but any instructions that depend on governed logging or artifact mutation must defer to the admin support surfaces once `/Users/charvin/Projects/ai-delivery-admin` is implemented.

## Ownership Boundary

This execution plan owns only project-local workflow-skill assets in `/Users/charvin/Projects/Codex`.

It may:

- implement the project-local `requirement-breakdown` skill package
- implement the project-local `ui-requirement-mapping` skill package
- implement the project-local `ui-interaction-design` skill package
- add shared references, templates, validators, and usage docs for those three skill packages
- add install or sync scripts that make those project-local skills available from the current Codex environment
- document how project-local skills should cooperate with the separate admin support surfaces when those surfaces exist

It must not:

- implement the admin support skill package
- implement or modify the `ai-delivery-admin` MCP server
- redefine `.ai-delivery/` contract truth in `/Users/charvin/Projects/Codex`
- move the three workflow skills into `ai-delivery-admin`
- rebuild the admin Web console or its server stack
- implement product feature code outside the AI delivery system itself

## Governing References

This plan is derived from the following approved documents:

- `/Users/charvin/Projects/Codex/docs/plans/2026-04-04-ai-delivery-implementation-plan.md`
- `/Users/charvin/Projects/Codex/docs/plans/2026-04-04-ai-delivery-overall-chain-design.md`
- `/Users/charvin/Projects/Codex/docs/plans/2026-04-04-ai-delivery-admin-system-design.md`
- `/Users/charvin/Projects/Codex/docs/plans/2026-04-04-ai-delivery-master-plan-refactor-design.md`
- `/Users/charvin/Projects/Codex/docs/plans/2026-04-04-requirement-breakdown-skill-design.md`
- `/Users/charvin/Projects/Codex/docs/plans/2026-04-04-ui-requirement-mapping-skill-design.md`
- `/Users/charvin/Projects/Codex/docs/plans/2026-04-04-ui-interaction-design-skill-design.md`
- `/Users/charvin/Projects/Codex/docs/plans/2026-04-04-ai-delivery-project-data-layer-implementation-plan.md`
- `/Users/charvin/Projects/Codex/docs/plans/2026-04-05-ai-delivery-admin-implementation-plan.md`

## Preconditions

Before implementation starts:

- `/Users/charvin/Projects/Codex/.ai-delivery/` must already exist and remain the upstream workflow truth
- the project-local data-layer contract must be treated as stable input, not something this plan gets to redesign
- if `/Users/charvin/Projects/ai-delivery-admin` already exists, its support surfaces must be treated as governed dependencies rather than as a place to relocate project-local skill truth
- if the admin project is not implemented yet, this plan may still build the project-local skill sources, but any step that would otherwise require governed logging or state mutation must document the dependency rather than invent an alternate truth path

### Task 1: Verify Preconditions And Scaffold The Project-Local Skill Home

**Files:**
- Verify: `/Users/charvin/Projects/Codex/.ai-delivery/**`
- Create: `/Users/charvin/Projects/Codex/.codex/skills/ai-delivery/common/README.md`
- Create: `/Users/charvin/Projects/Codex/.codex/skills/ai-delivery/common/references/.gitkeep`
- Create: `/Users/charvin/Projects/Codex/.codex/skills/ai-delivery/common/templates/.gitkeep`
- Create: `/Users/charvin/Projects/Codex/.codex/skills/ai-delivery/requirement-breakdown/.gitkeep`
- Create: `/Users/charvin/Projects/Codex/.codex/skills/ai-delivery/ui-requirement-mapping/.gitkeep`
- Create: `/Users/charvin/Projects/Codex/.codex/skills/ai-delivery/ui-interaction-design/.gitkeep`
- Create: `/Users/charvin/Projects/Codex/tests/ai-delivery-skills/.gitkeep`

**Step 1: Verify the project-local data contract still parses**

Run:

```bash
jq empty /Users/charvin/Projects/Codex/.ai-delivery/meta/*.json /Users/charvin/Projects/Codex/.ai-delivery/runtime/*.json
```

Expected: zero exit status

**Step 2: Create the project-local skill root**

Run:

```bash
mkdir -p \
  /Users/charvin/Projects/Codex/.codex/skills/ai-delivery/common/references \
  /Users/charvin/Projects/Codex/.codex/skills/ai-delivery/common/templates \
  /Users/charvin/Projects/Codex/.codex/skills/ai-delivery/requirement-breakdown/references \
  /Users/charvin/Projects/Codex/.codex/skills/ai-delivery/ui-requirement-mapping/references \
  /Users/charvin/Projects/Codex/.codex/skills/ai-delivery/ui-interaction-design/references \
  /Users/charvin/Projects/Codex/tests/ai-delivery-skills
```

Expected: all directories exist with no errors

**Step 3: Write the root README marker**

The project-local README must say that:

- these three skills are business-project assets
- they operate on `/Users/charvin/Projects/Codex/.ai-delivery/`
- they are not owned by `ai-delivery-admin`
- governed logging or state mutation should use the separate admin support surfaces when available

**Step 4: Review the resulting root**

Run:

```bash
find /Users/charvin/Projects/Codex/.codex/skills/ai-delivery -maxdepth 3 -print | sort
```

Expected: only the planned roots and placeholder files appear

**Step 5: Commit**

```bash
git -C /Users/charvin/Projects/Codex add .codex/skills tests/ai-delivery-skills
git -C /Users/charvin/Projects/Codex commit -m "chore: scaffold project-local ai-delivery skill roots"
```

### Task 2: Add Shared References, Templates, And Skill Validation Tooling

**Files:**
- Create: `/Users/charvin/Projects/Codex/.codex/skills/ai-delivery/common/references/dual-truth-rules.md`
- Create: `/Users/charvin/Projects/Codex/.codex/skills/ai-delivery/common/references/blocker-catalog.md`
- Create: `/Users/charvin/Projects/Codex/.codex/skills/ai-delivery/common/references/logging-checklist.md`
- Create: `/Users/charvin/Projects/Codex/.codex/skills/ai-delivery/common/templates/requirement-slice-template.md`
- Create: `/Users/charvin/Projects/Codex/.codex/skills/ai-delivery/common/templates/figma-mapping-template.md`
- Create: `/Users/charvin/Projects/Codex/.codex/skills/ai-delivery/common/templates/interaction-design-template.md`
- Create: `/Users/charvin/Projects/Codex/scripts/validate-project-ai-delivery-skills.sh`
- Create: `/Users/charvin/Projects/Codex/tests/ai-delivery-skills/validate-sources.test.sh`

**Step 1: Write the shared reference docs**

The shared docs must centralize:

- Requirement/Figma dual-truth rules
- blocker names and meanings
- required logging order when admin support is available
- the rule that artifact truth stays in `.ai-delivery/`

**Step 2: Write reusable output templates**

The templates must align exactly with the approved artifact shapes for:

- `requirement-slice.md`
- `figma-mapping.md`
- `interaction-design.md`

**Step 3: Write the skill validation script**

The script should verify that each project-local skill package:

- has a `SKILL.md`
- references only existing local files
- mentions the correct output artifacts
- mentions the required blocker names for its own boundary
- does not claim ownership of admin-only capabilities

**Step 4: Write a shell test that fails if the validator or skill sources are broken**

Use this test shape:

```bash
#!/bin/zsh
set -euo pipefail
zsh /Users/charvin/Projects/Codex/scripts/validate-project-ai-delivery-skills.sh
```

**Step 5: Run the validator test**

Run:

```bash
zsh /Users/charvin/Projects/Codex/tests/ai-delivery-skills/validate-sources.test.sh
```

Expected: PASS

**Step 6: Commit**

```bash
git -C /Users/charvin/Projects/Codex add .codex/skills scripts tests/ai-delivery-skills
git -C /Users/charvin/Projects/Codex commit -m "feat: add shared project-local skill references"
```

### Task 3: Implement The Project-Local `requirement-breakdown` Skill Package

**Files:**
- Create: `/Users/charvin/Projects/Codex/.codex/skills/ai-delivery/requirement-breakdown/SKILL.md`
- Create: `/Users/charvin/Projects/Codex/.codex/skills/ai-delivery/requirement-breakdown/references/checklist.md`
- Create: `/Users/charvin/Projects/Codex/.codex/skills/ai-delivery/requirement-breakdown/references/subreq-readme-template.md`
- Modify: `/Users/charvin/Projects/Codex/scripts/validate-project-ai-delivery-skills.sh`

**Step 1: Write the skill contract test expectations**

The validator should assert that this skill explicitly covers:

- reading top-level requirement material
- generating `breakdown-summary.md`, `global-rules.md`, `dependency-graph.json`, and `requirement-slice.md`
- setting `split_ready` only when safe
- blocking on `blocked_requirement_conflict` and `blocked_missing_requirement`
- refusing to invent product truth

**Step 2: Write the `SKILL.md` and references**

The skill must direct the agent to:

- work inside `/Users/charvin/Projects/Codex/.ai-delivery/requirements/`
- reuse the shared templates and references
- log and transition status through the admin support surface when available
- still keep artifact outputs in the business project, not inside `ai-delivery-admin`

**Step 3: Run the skill validator**

Run:

```bash
zsh /Users/charvin/Projects/Codex/scripts/validate-project-ai-delivery-skills.sh
```

Expected: PASS

**Step 4: Commit**

```bash
git -C /Users/charvin/Projects/Codex add .codex/skills scripts
git -C /Users/charvin/Projects/Codex commit -m "feat: add project-local requirement breakdown skill"
```

### Task 4: Implement The Project-Local `ui-requirement-mapping` Skill Package

**Files:**
- Create: `/Users/charvin/Projects/Codex/.codex/skills/ai-delivery/ui-requirement-mapping/SKILL.md`
- Create: `/Users/charvin/Projects/Codex/.codex/skills/ai-delivery/ui-requirement-mapping/references/figma-fetch-order.md`
- Create: `/Users/charvin/Projects/Codex/.codex/skills/ai-delivery/ui-requirement-mapping/references/mapping-checklist.md`
- Modify: `/Users/charvin/Projects/Codex/scripts/validate-project-ai-delivery-skills.sh`

**Step 1: Extend the validator expectations**

The validator should assert that this skill explicitly covers:

- reading `requirement-slice.md`
- Figma retrieval order and screenshot requirement
- writing `figma-mapping.md` and `traceability.json`
- blocking on `blocked_missing_design` and `blocked_requirement_figma_conflict`
- explicit handling of companion UI and shared nodes

**Step 2: Write the skill package**

The `SKILL.md` must direct the agent to:

- consume project-local `.ai-delivery/` slices
- use cached Figma evidence when possible
- never treat `ai-delivery-admin` as the source of visual truth
- use admin support or MCP only for governed logging, state changes, and artifact updates

**Step 3: Re-run the validator**

Run:

```bash
zsh /Users/charvin/Projects/Codex/scripts/validate-project-ai-delivery-skills.sh
```

Expected: PASS

**Step 4: Commit**

```bash
git -C /Users/charvin/Projects/Codex add .codex/skills scripts
git -C /Users/charvin/Projects/Codex commit -m "feat: add project-local ui requirement mapping skill"
```

### Task 5: Implement The Project-Local `ui-interaction-design` Skill Package

**Files:**
- Create: `/Users/charvin/Projects/Codex/.codex/skills/ai-delivery/ui-interaction-design/SKILL.md`
- Create: `/Users/charvin/Projects/Codex/.codex/skills/ai-delivery/ui-interaction-design/references/allowed-assumptions.md`
- Create: `/Users/charvin/Projects/Codex/.codex/skills/ai-delivery/ui-interaction-design/references/state-checklist.md`
- Modify: `/Users/charvin/Projects/Codex/scripts/validate-project-ai-delivery-skills.sh`

**Step 1: Extend the validator expectations**

The validator should assert that this skill explicitly covers:

- reading `requirement-slice.md` and `figma-mapping.md`
- writing `interaction-design.md`
- recording `assumed_micro_interaction` only inside the allowed boundary
- blocking on `blocked_missing_design`, `blocked_requirement_figma_conflict`, and `blocked_missing_requirement`
- refusing to invent business flow or page structure

**Step 2: Write the skill package**

The `SKILL.md` must direct the agent to:

- keep interaction truth inside the business project's `.ai-delivery/requirements/...`
- distinguish source-backed facts from micro-interaction assumptions
- use the admin support surface for governed log or status operations when available
- never relocate the interaction contract into `ai-delivery-admin`

**Step 3: Re-run the validator and project-local shell test**

Run:

```bash
zsh /Users/charvin/Projects/Codex/scripts/validate-project-ai-delivery-skills.sh && \
zsh /Users/charvin/Projects/Codex/tests/ai-delivery-skills/validate-sources.test.sh
```

Expected: PASS

**Step 4: Commit**

```bash
git -C /Users/charvin/Projects/Codex add .codex/skills scripts tests/ai-delivery-skills
git -C /Users/charvin/Projects/Codex commit -m "feat: add project-local interaction design skill"
```

### Task 6: Add Project-Local Install Or Sync Scripts, Usage Docs, And Final Verification

**Files:**
- Create: `/Users/charvin/Projects/Codex/scripts/install-project-ai-delivery-skills.sh`
- Modify: `/Users/charvin/Projects/Codex/.codex/skills/ai-delivery/common/README.md`
- Create: `/Users/charvin/Projects/Codex/.codex/skills/README.md`

**Step 1: Write the project-local install or sync script**

The install script should make the three business-project skills available from the current Codex environment without moving their source of truth out of the repo.

**Step 2: Update the usage docs**

Document at least:

- where the three project-local skills live
- how to install or sync them into the local Codex environment
- that `ai-delivery-admin` owns the separate support skill and MCP server
- how project-local skills are expected to cooperate with governed admin support surfaces during execution

**Step 3: Run the full project-local verification suite**

Run:

```bash
zsh /Users/charvin/Projects/Codex/scripts/validate-project-ai-delivery-skills.sh && \
zsh /Users/charvin/Projects/Codex/tests/ai-delivery-skills/validate-sources.test.sh
```

Expected: all commands pass

**Step 4: Commit**

```bash
git -C /Users/charvin/Projects/Codex add .codex/skills scripts tests/ai-delivery-skills
git -C /Users/charvin/Projects/Codex commit -m "docs: finalize project-local ai-delivery skills"
```

## Handoff After Implementation

After this plan is implemented and verified:

- the business project owns the three project-local workflow skills under `/Users/charvin/Projects/Codex/.codex/skills/ai-delivery/`
- those skills can create and update `.ai-delivery/` artifacts during requirement development while keeping artifact truth in the business project
- governed logging, status mutation, blocker handling, and MCP operations remain the responsibility of the separate `ai-delivery-admin` execution track
- future feature-development sessions can use the project-local skills together with the admin support surfaces without changing the core architecture
- full end-to-end closure still depends on a later integration repair / full-chain verification track that reconciles bootstrap, blocked recovery, merge finalization, and Spec Kit bridge behavior across tracks

If future work needs to:

- redesign `.ai-delivery/` contracts
- move the three project-local skills into the admin project
- change the ownership boundary between project-local workflow skills and admin support surfaces

then that change must first be reconciled against `/Users/charvin/Projects/Codex/docs/plans/2026-04-04-ai-delivery-implementation-plan.md` before implementation proceeds.
