# Framework Guide: Native Tier (built-in fallback)

Use this tier when **no** external framework (spec-kit / OpenSpec / superpowers / ECC) is installed. It is the quality floor of the orchestrator: lightweight artifacts inside the sub-requirement directory plus built-in discipline rules. Native-tier output must be just as traceable as framework-tier output.

Native process/governance artifacts use the current binding's canonical `.ai-delivery` paths. The default layout places sub-requirement artifacts beside the slice under `.ai-delivery/requirements/<req-id>/sub-requirements/<subreq-id>/`.

## Artifact containment

- All process/governance artifacts use the canonical paths declared by `.ai-delivery/meta/project-binding.json`; requirement-wide status, todo, progress, and delivery reports remain at their declared requirement-level paths.
- Host-tree writes are limited to production source, project-native tests, goldens/official previews, and runtime assets. Do not create repository-root design, plan, review, report, checklist, or session files.
- Run the artifact-boundary audit from [../framework-adaptation.md](../framework-adaptation.md) before advancing any gate. Any new or modified process/governance artifact outside `.ai-delivery/` sets `blocked_verification_failure`.
- Resolve the execution workspace through [../workspace-policy.md](../workspace-policy.md). The native tier cannot infer worktree consent from isolation preferences or checkpoints.

Before the spec pipeline, resolve the binding layout keys `spec`, `plan`, and `tasks`. The filenames below are default-layout examples only.

## `solution-design` action (native solution-design flow)

Inline in the main session (no separate tool):

1. Read `requirement-slice.md`, the enabled UI truth artifact when present, API docs, and the dependency graph.
2. Produce: architecture sketch, component decomposition, data/state-transition model, scenario ID references, and key trade-offs. Runtime Coverage details remain in `contracts/ui-truth-index.json`.
3. Write the solution design to the path resolved from layout key `solution_design` (default `design.md`) and present a compact summary to the user. Keep the `notes` field for short status markers only.
4. Set `design_approved: true` after the required review: `design_mode=full` only after explicit user approval through CP-DESIGN; `design_mode=light` after the short design and AI self-review without CP-DESIGN. Keep it `false` for `design_mode=none`.

## `spec` action

Create the artifact resolved from layout key `spec` with exactly four sections:

```markdown
# <subreq-id> Spec

## Problem
<one paragraph: what is broken or missing>

## Goal
<observable outcome, phrased as acceptance-relevant behavior>

## Scope
- In scope: ...
- Out of scope: ...

## Acceptance Criteria
- [ ] testable criterion 1
- [ ] testable criterion 2
```

Audit against every frozen unit/scenario id and preserve its evidence origin for UI truth slices, then set `spec_ready`.

## `plan` action

Create the artifact resolved from layout key `plan` with a `## Plan` section:

```markdown
# <subreq-id> Plan

## Plan
<2-5 sentences: approach, key files/components, sequencing rationale>
```

## `tasks` action

Create the artifact resolved from layout key `tasks` with a `## Tasks` section:

```markdown
# <subreq-id> Tasks

## Tasks
- [ ] T1 <task> — files: <edit surface> — test: <test pointer or how to verify>
- [ ] T2 ...
```

Rules:

- One task = one implementable step with an explicit edit surface and a test pointer.
- Order tasks by dependency; shared components before consumers.
- Audit granularity and file scope before setting `tasks_ready`.

The native tier keeps the artifacts resolved from `plan` and `tasks` separate so the archive's three-piece set stays consistent across all tiers.

## `implement` action — built-in discipline

No subagent framework is required, but the discipline is non-negotiable:

1. **Resolve workspace** — use the current checkout by default and reuse the Stage 2 user-approved workspace for UI slices. Creating or reusing a worktree requires explicit confirmation for this sub-requirement and the exact project-local path; external paths and automatic tool placement are forbidden.
2. **TDD first** — write a failing test for the task before production code; keep the loop red → green → refactor.
3. **Small steps** — one file at a time, small commits prefixed with the subreq id.
4. **Review loop** — after each task, run review as a separate pass through the [Review loop](../stage-implementation.md#review-loop-task-level-closed-loop): re-read the diff against the task's acceptance notes and the spec's acceptance criteria as if reviewing someone else's work; findings become a fix list, then fix and re-review until clean or the `review_loop.max_rounds` budget (default 3) is exhausted — then escalate to the user, never auto-merge.
5. **Verify before completion** — run project static analysis and the full test suite; never claim a task done without evidence.

## `finish` action — built-in merge checklist

1. Full analyze + full test pass clean.
2. Structured visual/runtime acceptance written (`ui_truth_mode=figma` or `runtime-baseline` only): the artifact resolved from layout key `visual_acceptance` binds the current v2 index and passes or explicitly waives every scenario with mode-appropriate evidence.
3. Rebase onto the development branch (no merge commits); resolve conflicts, re-run tests.
4. Open/merge the PR, then set `merged` only after the artifact resolved from layout key `verification` is written in the user's current conversation language and signed. Preserve the three `ai-delivery-verification:*` markers from `templates/verification-template.md`; the status validator rejects `merged` without them.

## Traceability recording

Use only the canonical `artifacts[]` shape in the sub-requirement `traceability.json`. Add one complete object for each `kind` (`spec`, `plan`, `tasks`):

```json
{
  "spec_refs": {
    "tier": "native",
    "artifacts": [
      {
        "kind": "spec",
        "canonical_path": "<repo-relative path resolved from layout key spec>",
        "derived_paths": [],
        "content_sha256": "<sha256 of canonical content>",
        "sync_state": "synced"
      }
    ]
  }
}
```

Also add one `source_index.spec` entry per artifact with `ref_type` `spec` / `plan` / `tasks`. Do not emit or mix in legacy per-kind path fields.

## Boundaries

- Native process/governance artifacts never leave canonical `.ai-delivery` paths; do not invent repo-wide `specs/` trees.
- If the user later installs a framework, new sub-requirements may switch tiers (recorded in `decisions.md`); already-advanced sub-requirements keep their original tier.
