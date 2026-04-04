# AI Delivery System Master Plan

> **For Claude:** This is the architecture blueprint and governing master plan for the AI delivery system. Do not treat it as a step-by-step execution checklist. Before implementation begins, derive a dedicated execution plan from the appropriate execution track defined in this document.

**Goal:** Define the full architecture, boundaries, runtime rules, storage contracts, integration model, and extension strategy for the AI delivery system so that future implementation can proceed from a stable, shared blueprint rather than from ad hoc execution tasks.

**Architecture:** The system is organized around three coordinated layers: `Spec Kit` for spec-driven artifacts, `.ai-delivery/` inside each business project for workflow truth and runtime state, and a separate local `ai-delivery-admin` project for management, visualization, editing, and agent-facing control surfaces. Requirement remains the source of truth for functional meaning, Figma remains the source of truth for visual meaning, and any conflict between them must block automation rather than be silently resolved.

**Tech Stack:** Architecture-level plan spanning project-local hidden directories, structured Markdown and JSON artifacts, a local admin system built with `TypeScript`/`Node.js`/`React`/`zod`, Codex skills, MCP tools, filesystem adapters, and git/worktree-based development discipline.

---

## Plan Intent

This document is the governing master plan for the AI delivery system.

It exists to define:

- system boundaries
- storage boundaries
- domain entities
- state transitions
- runtime rules
- control surfaces
- extension points
- verification surfaces
- the execution-plan derivation model

It does **not** exist to tell an engineer which file to create first on day one.

Any real implementation must begin by deriving one of the execution plans defined later in this document.

## Scope And Non-Goals

### In Scope

This master plan governs:

- project-local hidden data storage in `.ai-delivery/`
- the relationship between `.ai-delivery/` and `.specify/`
- the separate `ai-delivery-admin` project
- workflow state transitions and blocker behavior
- requirement breakdown, Figma mapping, and interaction contract generation
- agent-facing MCP and skill integration
- observability, recovery, and extension design
- the rules for deriving future execution plans

### Out Of Scope

This master plan does not directly define:

- the exact first implementation milestone
- sprint ordering
- concrete file-by-file implementation sequencing
- feature-specific product logic outside the AI delivery system itself
- direct business feature development in the host product
- cloud deployment or multi-tenant SaaS architecture

## System Context

The system has three primary artifacts or runtime surfaces.

### 1. Business Project: `.specify/`

Role:

- stores `Spec Kit` native artifacts
- contains constitution, specs, plans, tasks, and related spec-driven assets
- remains under Spec Kit ownership and conventions

### 2. Business Project: `.ai-delivery/`

Role:

- stores workflow truth outside Spec Kit's native artifact model
- stores requirement packages, Figma evidence cache, runtime state, blockers, worktree state, logs, and traceability records
- acts as the project-local source of truth for the AI delivery workflow

### 3. Separate Local Project: `ai-delivery-admin`

Role:

- binds to one or more business projects
- reads `.specify/` and `.ai-delivery/`
- presents a Web console
- exposes local APIs, MCP tools, and supporting skills
- never owns product truth; it only reads, validates, edits, and manages governed artifacts

## Architecture Principles

The following principles are hard constraints.

### Dual Source Of Truth

- `Requirement` defines functional truth
- `Figma` defines visual truth
- conflicts must become blockers
- agents must not silently invent requirement meaning or missing UI

### Conflict Escalation

When evidence conflicts:

- automation must stop
- blocker records must be created
- the system must wait for explicit human resolution or documented decision input

### Worktree Discipline

- every sub-requirement must use its own worktree
- worktrees must be created from the designated main development branch
- later dependent worktrees cannot be created before dependencies reach `merged_main_dev`

### Merge Discipline

- sub-requirements must merge back to the designated main development branch before downstream dependents are unlocked
- merge conflicts are resolved during merge, not ignored in later branches

### Unified Logging

- every significant action must be written to the backend-managed log model
- this applies to the main session and all subagents
- “did work but did not log it” is considered invalid execution

### Management/Execution Separation

- business projects keep truth artifacts
- the separate admin project handles management and visibility
- agent control surfaces must go through governed MCP/API pathways when changing workflow state

### Controlled Inference Only

Allowed inference:

- micro-interaction defaults
- usability-preserving defaults that do not alter business meaning
- reuse of explicit existing system patterns when they do not create new semantics

Disallowed inference:

- new business branches
- missing product requirements
- missing visual states or components
- new fields, dialogs, or permission semantics

## Domain Model

The system is centered on the following core entities.

### Requirement

Represents the original product-level requirement package.

Key responsibilities:

- anchors the full scope
- owns raw requirement source material
- owns the top-level dependency graph root

### SubRequirement

Represents an independently traceable development slice.

Key responsibilities:

- defines in-scope and out-of-scope boundaries
- participates in dependency ordering
- is the unit of worktree allocation, state transition, implementation, merge, and logging

### Figma Evidence

Represents cached design truth.

Key responsibilities:

- stores Figma structure, nodes, screenshots, comments, and tokens
- supports Requirement <-> Figma mapping
- provides verifiable visual reference for high-fidelity implementation

### Interaction Contract

Represents executable interaction behavior derived from Requirement and Figma.

Key responsibilities:

- documents user actions and system responses
- defines loading/empty/error/success/disabled states
- marks assumed micro-interactions explicitly

### Traceability Record

Represents cross-artifact linkage.

Key responsibilities:

- links requirement refs to sub-requirements
- links sub-requirements to Figma nodes
- links interaction docs and Spec Kit artifacts back to source truth
- records conflicts and confidence

### Blocker

Represents a governed stop condition.

Key responsibilities:

- records blocking type and trigger
- indicates affected requirement/sub-requirement/artifact
- stores the pending decision or repair action

### Worktree Record

Represents a tracked implementation workspace.

Key responsibilities:

- maps sub-requirements to branch/worktree paths
- records base branch, creation time, and current status
- helps enforce dependency and merge discipline

### Session And Event

Represents execution context and audit history.

Key responsibilities:

- distinguish main-session vs subagent actions
- provide ordered event history
- support recovery and replay

### Spec Kit Artifact

Represents the formal spec-driven artifact layer.

Key responsibilities:

- stores spec, plan, task, and related documents
- acts as the implementation-facing contract once requirement mapping and interaction design are complete

## Storage Blueprint

### Top-Level Project Layout

```text
<project-root>/
├── .specify/
├── .ai-delivery/
└── docs/plans/
```

### `.ai-delivery/` Layout

```text
.ai-delivery/
├── requirements/
├── figma-cache/
├── runtime/
├── logs/
└── meta/
```

### `requirements/`

Purpose:

- store requirement packages
- store sub-requirement slices
- store interaction and traceability outputs
- store requirement-level dependency graphs and decisions

Recommended shape:

```text
.ai-delivery/requirements/<requirement-id>/
├── requirement.md
├── breakdown-summary.md
├── global-rules.md
├── dependency-graph.json
└── sub-requirements/
    └── <subreq-id>/
        ├── README.md
        ├── requirement-slice.md
        ├── figma-mapping.md
        ├── interaction-design.md
        ├── dependency.json
        ├── status.json
        ├── traceability.json
        └── decisions.md
```

### `figma-cache/`

Purpose:

- store raw Figma evidence
- reduce repeated MCP usage and external dependency cost
- support deterministic remapping and later audits

Recommended shape:

```text
.ai-delivery/figma-cache/<figma-file-id>/
├── structure.json
├── nodes/
├── screenshots/
├── comments/
└── tokens/
```

### `runtime/`

Purpose:

- store execution truth required for scheduling and governance

Recommended shape:

```text
.ai-delivery/runtime/
├── main-branch.json
├── dependency-graph.json
├── worktrees.json
├── task-board.json
├── blockers.json
└── merge-queue.json
```

### `logs/`

Purpose:

- store append-only execution history
- support recovery, audit, replay, and timeline visualization

Recommended shape:

```text
.ai-delivery/logs/
├── events.ndjson
├── sessions/
└── subagents/
```

### `meta/`

Purpose:

- store project-level policy and naming configuration

Recommended shape:

```text
.ai-delivery/meta/
├── project-binding.json
├── naming-rules.json
└── workflow-policy.json
```

### File Contract Rules

All structured files should carry:

- a schema or version field where applicable
- `updated_at`
- `updated_by` when editable through managed interfaces
- deterministic IDs where applicable

Naming conventions should be centralized in:

- `.ai-delivery/meta/naming-rules.json`

## Runtime Blueprint

### Primary Workflow

The AI delivery workflow proceeds through the following conceptual phases:

1. `Requirement Intake`
2. `Sub-Requirement Breakdown`
3. `Figma Mapping & Cache`
4. `Interaction Design`
5. `Spec Kit Phase`
6. `Development Dispatch`
7. `Merge Back To Main Dev`
8. `Done`

### Sub-Requirement State Machine

```text
draft
-> split_ready
-> figma_mapped
-> interaction_ready
-> spec_ready
-> planned
-> dependency_satisfied
-> worktree_created
-> in_progress
-> review_pending
-> merge_pending
-> merged_main_dev
-> done
```

### Blocking States

```text
blocked_requirement_conflict
blocked_figma_conflict
blocked_requirement_figma_conflict
blocked_dependency
blocked_missing_design
blocked_missing_requirement
blocked_merge_conflict
blocked_verification_failure
```

### Dependency Rules

- a sub-requirement may only become `dependency_satisfied` when all upstream dependencies are `merged_main_dev`
- dependency graphs must be acyclic
- shared foundations and cross-feature infrastructure must be available before dependent feature modules are unlocked

### Worktree Rules

- one sub-requirement maps to one worktree
- each worktree is created from the designated main development branch
- future dependent worktrees cannot be created early to “get ahead” of dependency order

### Parallel Execution Rules

Parallel execution is allowed only when:

- multiple sub-requirements are already `dependency_satisfied`
- they belong to the same currently unlocked dependency wave
- they do not have overlapping write sets or otherwise conflicting implementation surfaces

### Merge Rules

- completed work must merge back into the designated main development branch first
- merge is the event that unlocks dependent nodes
- merge conflict resolution is part of the merge phase, not deferred debt

### Blocker Lifecycle

A blocker should move through:

1. `created`
2. `triaged`
3. `decision_requested`
4. `resolved`
5. `closed`

No blocked sub-requirement may advance until its blocker is resolved or explicitly overridden by documented governance.

## Admin System Blueprint

The local admin system is a separate project and should be organized into clearly bounded layers.

### Recommended Layout

```text
<ai-delivery-admin>/
├── server/
├── web/
├── mcp-server/
├── skills/
├── adapters/
├── shared/
└── tests/
```

### Layer Responsibilities

#### `adapters/`

- parse `.specify/` and `.ai-delivery/`
- validate versions and schema expectations
- return normalized domain objects

#### `shared/`

- define common types and schema validators
- serve as the contract boundary between adapters, server, web, and MCP

#### `server/`

- expose local APIs
- enforce state-transition rules
- validate write requests
- manage project binding and artifact updates

#### `web/`

- visualize project overview, requirement tree, execution board, logs, blockers, and artifact editing surfaces

#### `mcp-server/`

- expose agent-facing tools over the governed local system
- prevent agents from bypassing managed validations

#### `skills/`

- store supporting skill packages and references tied to the admin system

### Core UI Views

The admin console should eventually provide:

- `Project Dashboard`
- `Requirement Explorer`
- `Traceability View`
- `Execution Board`
- `Logs Timeline`
- `Artifact Editor`
- `Blocker Center`

## Skill System Blueprint

The system includes three custom skills.

### 1. `requirement-breakdown`

Purpose:

- convert raw product requirement input into sub-requirement packages and dependency graphs

Consumes:

- top-level requirement materials

Produces:

- `requirement-slice.md`
- dependency artifacts
- `split_ready` state outputs

### 2. `ui-requirement-mapping`

Purpose:

- bind sub-requirements to Figma evidence and cached design truth

Consumes:

- requirement slices
- Figma links and cache

Produces:

- `figma-mapping.md`
- `traceability.json`
- `figma_mapped` state outputs

### 3. `ui-interaction-design`

Purpose:

- derive governed interaction contracts from Requirement and Figma evidence

Consumes:

- requirement slice
- figma mapping
- Figma interaction annotations where available

Produces:

- `interaction-design.md`
- explicit micro-interaction assumptions
- `interaction_ready` state outputs

### Shared Skill Rules

All skills must:

- respect dual source truth boundaries
- refuse silent invention of business or visual meaning
- emit blockers for unsupported gaps or conflicts
- write progress and status through governed backend pathways
- produce output directly into `.ai-delivery/`

## MCP Blueprint

### Purpose

MCP exists to provide a controlled AI-facing interface over the admin system.

### High-Level Tool Categories

#### Project Binding And Overview

- `bind_project`
- `get_project_overview`
- `list_requirements`
- `list_sub_requirements`
- `get_sub_requirement_detail`

#### Workflow Control

- `transition_sub_requirement_status`
- `check_dependency_ready`
- `reserve_worktree_slot`
- `record_worktree_created`
- `record_commit`
- `record_merge_result`

#### Artifact Management

- `upsert_artifact`
- `read_traceability`
- `list_blockers`

#### Logging

- `append_execution_log`

### MCP Rules

MCP writes must:

- validate state transitions
- validate dependency readiness
- validate naming rules such as commit prefix requirements
- reject illegal or stale writes
- record failures as managed events when appropriate

### Idempotency And Versioning

Where possible, MCP operations should be:

- idempotent for repeated identical write attempts
- guarded by explicit version or freshness checks
- auditable through `events.ndjson`

## Observability And Recovery

### Unified Event Model

The system should use one event model for both main-session and subagent execution.

Suggested fields:

- `event_id`
- `timestamp`
- `project_id`
- `requirement_id`
- `subreq_id`
- `session_id`
- `session_type`
- `event_type`
- `status_before`
- `status_after`
- `message`
- `metadata`

### Session Distinction

Use `session_type` to distinguish:

- `main_session`
- `subagent`

### Recovery Rules

The system should support:

- replaying event history
- reconstructing latest sub-requirement state
- detecting unfinished or inconsistent transitions
- resuming work after disconnects using logs and state snapshots

### Logging Failure Policy

If execution logging fails:

- the current action is not considered validly completed
- downstream automation should not assume the action succeeded

## Extension Points

The architecture should remain extensible in the following areas.

### New Skills

Additional skills can be introduced if they:

- consume governed artifacts
- produce governed artifacts
- respect blocker and dual-truth rules
- integrate through the same logging and status pathways

### New MCP Tools

New tools can be introduced if they:

- sit behind the same validation model
- do not bypass artifact governance
- preserve auditability and version control

### New Artifact Types

New files can be added under `.ai-delivery/` if they:

- have clear ownership
- define schema/version behavior where needed
- fit one of the existing top-level domains or justify a new one

### New Runtime States

New states may be added to the workflow if:

- they represent a real governance boundary
- they preserve backward interpretability
- they are documented in both runtime rules and admin validation logic

## Verification Strategy

This master plan defines verification surfaces, not exact execution commands.

### Contract Verification

Verify:

- file schemas
- required fields
- version fields
- deterministic IDs and naming contracts

### State Transition Verification

Verify:

- allowed transitions
- blocked transitions
- dependency-gated transitions
- merge-unlock semantics

### Concurrency Verification

Verify:

- concurrent artifact edits
- version mismatch handling
- subagent log interleaving
- stale write rejection

### Traceability Verification

Verify:

- Requirement -> SubRequirement links
- SubRequirement -> Figma links
- Interaction -> Requirement/Figma provenance
- Spec Kit artifact linkage back to upstream truth

### Recovery Verification

Verify:

- event replay correctness
- resumption after disconnect
- blocker persistence and closure
- reconstruction of latest execution state from artifacts and logs

## Derived Execution Plans

This master plan intentionally does not serve as an execution checklist.

Before implementation begins, one of the following execution plans must be derived.

### 1. Project Data Layer Execution Plan

Responsibilities:

- create and validate `.ai-delivery/` directory contracts
- define JSON/Markdown contract structures and sample artifacts
- implement data validation scripts or contract tests

Must not own:

- admin web
- MCP server implementation
- custom skill implementation

Outputs:

- hidden directory skeleton
- sample requirement packages
- schema examples
- contract validation support

### 2. `ai-delivery-admin` Execution Plan

Responsibilities:

- build the separate admin project
- implement `adapters / server / web / shared`
- implement project binding, reads, writes, views, blocker handling, and timeline surfaces

Must not own:

- the root definition of project-local workflow truth
- skill workflow semantics
- host-project business logic

Outputs:

- local admin app
- local APIs
- adapter implementation
- web console surfaces

### 3. `skills & mcp` Execution Plan

Responsibilities:

- implement the three custom skills
- implement agent-facing MCP tools
- translate architecture constraints into executable agent rules

Must not own:

- admin web implementation
- root `.ai-delivery/` contract design
- general-purpose product development outside the AI delivery system

Outputs:

- three skill packages
- MCP tool implementations
- references and validation tests for agent workflows

### Execution Plan Derivation Rules

Every derived execution plan must:

- declare its ownership boundary
- reference this master plan as governing truth
- avoid redefining another track's source-of-truth contracts
- escalate to master-plan revision if it needs to cross its assigned boundary

## Open Decisions

The following decisions can remain open without invalidating the master architecture.

- exact local stack choices inside `ai-delivery-admin` so long as the layering and boundaries remain intact
- exact schema representation for version fields so long as versioning is explicit and enforceable
- whether lightweight local persistence beyond filesystem indexes is needed inside the admin project
- exact UI visual language of the admin console
- whether future additional skills should live inside the admin project or a separate shared skills repository

## Outcome

With this document in place:

- the system architecture is stable before coding begins
- execution-order debates are deferred to derived execution plans
- future implementation tracks have clear ownership boundaries
- extension can proceed without repeatedly rewriting the system's governing truth
