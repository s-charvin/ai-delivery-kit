# AI Delivery Orchestrator-First Entry Design

Date: 2026-04-26
Status: ready-for-user-review

## Goal

Reframe `ai-delivery-kit` around a clean two-layer entry model:

- `ai-delivery init` handles repository onboarding only
- `ai-delivery-orchestrator` handles requirement orchestration by default

The product outcome is lower human ceremony. Users should no longer need to manually provide workflow-shaping identifiers such as `requirement_id`, `subreq_id`, `project_id`, or `main-branch` during normal operation. AI should infer, create, or select them, while humans only review key routing decisions and clear blockers.

## Problem Statement

The current experience mixes repository onboarding with requirement execution. That creates the wrong mental model:

- `ai-delivery init` appears to be the start of the delivery chain instead of a repo bootstrapper
- the user-facing docs teach manual chaining of low-level workflow stages even though `ai-delivery-orchestrator` already exists
- internal contract fields such as `requirement_id`, `subreq_id`, and `main-branch` leak into the public path
- README and the onboarding guide duplicate and partially diverge

The result is unnecessary operator work. The human is acting like a dispatcher instead of a reviewer.

## Scope

This design covers:

- public entry-point boundaries
- orchestrator-first requirement flow
- automatic requirement identity creation and selection
- automatic branch and project identity derivation during repo onboarding
- documentation consolidation into `README.md`
- validation and bootstrap contract changes required by the new entry model

This design does not cover:

- redesigning the governed requirement artifact shapes
- replacing the downstream skills inside the orchestration chain
- changing `ai-delivery-admin` responsibilities
- preserving the old manual path for compatibility

## Core Decision

Adopt an Orchestrator-First model.

### Public entry boundaries

- `ai-delivery init <repo-path>` is the repository onboarding command
- `ai-delivery-orchestrator` is the default entry for new requirements, resume, and blocker recovery
- direct use of lower-level skills remains supported only when their stated preconditions are already satisfied

### Explicit non-goal

Do not keep the old public workflow just because it already exists. If a manual parameter or manual stage hop is only there for historical reasons, remove it from the default path.

## User Experience Model

### Repository onboarding

The repo onboarding path stays intentionally narrow:

1. Install or temporarily bootstrap `ai-delivery`
2. Run `ai-delivery init <repo-path>`
3. Let the CLI:
   - detect the git root
   - derive the project identity from the repository name
   - detect the main branch automatically
   - install or guide missing prerequisites
   - seed `.ai-delivery`, `.agents/skills`, and `.specify` support surfaces

The public onboarding path should no longer require `--project-id` or `--main-branch`.

### Requirement execution

Once the repository is onboarded, the user should talk to the AI in natural language, for example:

- “这是需求文档，这是 Figma，这是接口，开始推进”
- “继续这个需求”
- “这个 blocker 我处理好了，继续”

The user should not be asked to manually decide which underlying workflow skill to call first under normal conditions.

## Automatic Repository Identity

### Project identity

`project_id` should be derived automatically from the repository root name using the existing slug rules. This remains an internal governed value, not a public onboarding parameter.

### Main branch

`main-branch` should be detected automatically during `ai-delivery init` and persisted to `.ai-delivery/runtime/main-branch.json`.

Recommended detection order:

1. remote default branch from `origin/HEAD` when available
2. current checked-out branch when it is a normal local branch
3. fallback to `main`

The chosen branch should be reported to the user in the init summary, but not requested as a normal prompt input.

## Automatic Requirement Routing

`ai-delivery-orchestrator` becomes responsible for deciding whether the user intent should continue an existing requirement or create a new one.

### Inputs

The orchestrator may use:

- the natural-language user request
- explicit file paths the user provides
- URLs such as Figma or API contract locations
- existing `.ai-delivery/requirements/*` packages
- existing `todo.md`, `status.json`, and `traceability.json` artifacts

### Matching behavior

When the user starts or resumes work, the orchestrator should:

1. inspect existing requirement packages
2. compare the new request against existing requirement truth and runtime state
3. choose one recommended routing conclusion:
   - `continue req-xxx`
   - or `create req-yyy`
4. stop and ask for human confirmation before taking either path

The review interaction should stay lightweight. The AI gives only one recommendation, and the human either confirms it or overrides it.

### Recommendation rules

- Prefer `continue req-xxx` when the supplied requirement material clearly maps to an active or partially completed package
- Prefer `create req-yyy` when the material represents a distinct business objective, a clearly separate scope, or a conflict with an existing package boundary
- If evidence is weak or conflicting, bias toward asking for confirmation earlier rather than making the routing decision implicitly

## Automatic Requirement Creation

When the orchestrator recommends a new requirement and the human confirms it, the orchestrator should create the requirement package without asking the user for manual IDs.

### Requirement id generation

The new `requirement_id` should be derived from the strongest available title source in this order:

1. explicit requirement document title
2. requirement file name
3. concise AI-generated title distilled from the approved prompt

The id should be slugified and collision-safe. If the preferred id already exists, append a deterministic suffix such as `-2`, `-3`, and so on.

### Sub-requirement ids

`subreq_id` remains governed by the requirement-breakdown stage and naming rules. The user should never provide it manually in the default path.

## Orchestrator Responsibilities

The orchestrator should become the default requirement dispatcher, not just a thin reminder layer.

It should:

- resolve runtime mode from governed state
- select or create the requirement package
- gather the relevant materials
- call the downstream workflow skills in the correct order
- pause only at explicit human review points and governed blocker checkpoints
- preserve `.ai-delivery` as the only workflow truth store

It should not:

- require the human to hand-pick a low-level skill first during the normal path
- expose internal identity fields as part of the public request contract
- turn README into a low-level operator runbook

## Direct Skill Usage Policy

The orchestrator is the default path, not the only path.

Lower-level skills such as `requirement-breakdown`, `api-contract-mapping`, `ui-requirement-mapping`, `ui-acceptance-contract`, and `ui-interaction-design` may still be invoked directly in special cases when their preconditions are already satisfied.

This support should be documented as an exception path:

- for surgical recovery
- for controlled re-entry into a later stage
- for expert use when the caller already has the correct governed inputs in place

These skills should continue to enforce their own boundaries and should not be documented as the normal starting path for new work.

## Documentation Model

`README.md` becomes the only public onboarding and workflow overview document in this repository.

### README responsibilities

README should explain:

- what `ai-delivery-kit` is
- how to install or bootstrap `ai-delivery`
- how to run `ai-delivery init <repo-path>`
- that `ai-delivery-orchestrator` is the default entry for new requirements
- how the AI automatically decides whether to continue or create a requirement
- where human review is still expected
- which lower-level skills can still be used directly in exceptional cases
- how release publishing works at a high level

### Guide removal

The following file should be removed from the public contract:

- `.ai-delivery/docs/guides/ai-delivery-any-repo-onboarding.md`

That means:

- do not ship it as a managed bootstrap asset
- do not validate it as part of the managed contract
- do not split canonical instructions across README and the guide

## Bootstrap And Validation Impact

The orchestrator-first design requires contract cleanup, not only wording cleanup.

### Bootstrap changes

- stop seeding the onboarding guide into target repositories
- stop treating the guide as a required managed artifact
- keep seeding the governed skills, validators, tests, and runtime/meta files

### Validation changes

The validator should be updated to assert the new contract:

- README contains the canonical onboarding instructions
- README describes `ai-delivery-orchestrator` as the default requirement entry
- README does not present manual `requirement_id`, `subreq_id`, or `main-branch` handling as the normal path
- the managed onboarding guide is absent from the contract

### Public script changes

The install and bootstrap public examples should reflect the reduced-parameter model:

- install path leads to `ai-delivery init <repo-path>`
- bootstrap path leads to `bootstrap-ai-delivery.sh <repo-path>` or the PowerShell equivalent

If advanced overrides still exist for internal use, they should not be the main README path.

## Human Gate Policy

The human should remain in the loop only at the points where judgment is genuinely valuable.

The required review points are:

- routing confirmation when the orchestrator recommends continuing an existing requirement or creating a new one
- checkpoint confirmation such as `tasks_ready_user_confirmation`
- blocker resolution and unblock approval when governed truth is incomplete or conflicting

Everything else should default to AI-driven progression through the orchestrated chain.

## Migration Direction

No compatibility-first design is required here.

Implementation should prefer the cleaner end state even when it removes or demotes previous public patterns. Existing internal capabilities may remain available, but the public contract, README narrative, bootstrap assets, and validation logic should all converge on the orchestrator-first model.

## Acceptance Criteria

This design is complete when the repository supports the following experience:

1. A user can onboard a repo with `ai-delivery init <repo-path>` without supplying `project_id` or `main-branch`
2. The init flow auto-detects and persists the main branch
3. README is the only public onboarding and workflow overview doc
4. The onboarding guide is removed from the managed asset contract
5. README presents `ai-delivery-orchestrator` as the default entry for new requirements
6. The normal user path no longer tells the human to manually choose `requirement_id`, `subreq_id`, or low-level workflow skills
7. The orchestrator routing model explicitly pauses for human confirmation before deciding to continue an existing requirement or create a new one
8. Lower-level skills remain usable directly when their prerequisites are satisfied, but they are documented as exception paths rather than the primary path
