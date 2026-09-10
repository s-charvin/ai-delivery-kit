# Stage 4: Implementation Bridge

Maps orchestrator Stage 4 (`implement` action) to task-level execution and `.ai-delivery` progress artifacts. Concrete execution style follows the selected tier — [frameworks/superpowers.md](frameworks/superpowers.md) (subagent-driven), [frameworks/ecc.md](frameworks/ecc.md) (agent-driven), or [frameworks/native.md](frameworks/native.md) (inline discipline).

## When to run

After CP-001 user confirmation, when reconcile emits `RUNTIME_MODE=confirm_to_dev` and `NEXT_ACTION=implement`.

**Do not dispatch implementation work before CP-001 is confirmed.**

For `ui_truth_mode=figma` or `runtime-baseline`, resume the user-approved workspace recorded by Stage 2. Do not run `using-git-worktrees` to create a second workspace for the same slice. `none` and `existing` slices follow [workspace-policy.md](workspace-policy.md), defaulting to the current checkout.

## tasks.md → task brief

For each task row in `tasks.md`:

| tasks.md field | Execution mapping |
|----------------|-------------------|
| Task title / ID | Implementer prompt headline |
| Scope / files | Allowed edit surface for one-file-at-a-time rule |
| Dependencies | Sequential order across tasks |
| Acceptance notes | TDD success criteria |

One execution cycle per task: fresh context (subagent when the tier supports it) → implement → review → mark task done in ledger.

When a review or implementation cycle produces a reusable problem, record it in
the requirement-level `retrospective.md` before starting the next attempted
solution, then tell the user what was recorded. Follow
[retrospective-guidance.md](retrospective-guidance.md). The ledger is required
before archive, although it may contain no problem rows; this does not add an
implementation-stage gate.

## progress.md ↔ ledger

Append to `.ai-delivery/requirements/<req-id>/progress.md`:

- completed task IDs from `tasks.md`
- implementer session notes (blockers, deferred integration)
- review outcomes

`progress.md` is a compaction aid only. On resume, reconcile from `status.json` and on-disk artifacts — never promote gates from progress alone.

## Dual-stage review

Both stages run through the [Review loop](stage-implementation.md#review-loop-task-level-closed-loop): implement → fresh-context review → findings become a fix brief → re-review, until clean or the `review_loop.max_rounds` budget is exhausted (then escalate to the user; never auto-merge).

1. **Per-task review** — after each task; append every round's findings and fix summary to `progress.md`.
2. **Pre-merge review** — full slice review after all tasks; then visual acceptance when the UI truth capability is enabled and the verification step.

## Visual acceptance evidence (UI truth capability)

Before setting `visual_acceptance_passed`, instantiate `templates/visual-acceptance-template.json` as `sub-requirements/<subreq-id>/visual-acceptance.json`. Preserve machine keys/enums and write summaries/notes in the user's current conversation language.

The schema v2 artifact must bind the current v3 `ui-truth-index.json` SHA-256 and contain exactly one result for every indexed scenario id. `passed` evidence follows the frozen `evidence_scope` as well as `review_mode`:

- `component-only` accepts the indexed frozen preview for visual review and a component test or explicit manual behavior review when behavior is required. It must not include `runtime-capture` or claim host composition passed.
- `host-static` and `host-runtime` require `runtime-capture`: screenshot path/hash, producing test path/hash, geometry/landmark assertion report path/hash, command, reviewer binding to the capture hash, and host provenance matching `host_binding`.

Runtime screenshot paths must be inside the indexed project-native test evidence root and must stay outside `.ai-delivery/`. A `manual` summary that names or mentions a screenshot file is still only text; it cannot replace `runtime-capture`. `waived` requires user identity, timestamp, and reason. Every file path is repo-relative and hash-verified.

A no-golden waiver applies only to the corresponding component preview. It does not automatically require or waive host capture. A motion waiver applies only to motion acceptance and does not alter static component or host evidence scope.

For UI truth slices, the artifact must also contain `motion_acceptance` with exactly one row for every indexed `unit_id`. The row's `result` is `passed` or `waived`; a static unit must be `passed` with explicit `test` or `manual` evidence and can never be waived. An animated unit with an indexed motion preview must include matching `motion` evidence (path and SHA-256); when no deterministic motion preview was available, `passed` requires independent Stage 4 runtime `test` or `manual` evidence, and `waived` requires the user's identity, timestamp, and reason. Static golden evidence never substitutes for this per-unit motion acceptance.

When a stable Figma reference bitmap exists, image-diff evidence records reference/candidate/diff paths and hashes, metric, threshold, actual result, command, and summary. When no stable bitmap exists, use exact design-value mapping, deterministic preview, and user confirmation; do not claim automated pixel equivalence.

## Status chain

```
tasks_ready → (CP-001) → in_dev → visual_acceptance_passed (UI truth capability) → merged
```

`ui_truth_mode=none` and `existing` subreqs skip `visual_acceptance_passed`; existing UI changes use ordinary behavior and semantic evidence.

## Handoff after slice

See [stage-implementation.md](stage-implementation.md) for PR / babysit finishing steps.
