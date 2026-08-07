# Stage 4: Implementation

## When to run

Each sub-requirement at `tasks_ready` after CP-001 user confirmation (reconcile emits `implement`). See [stage-4-sdd-bridge.md](stage-4-sdd-bridge.md) for task-brief mapping and progress ledger rules.

**Do not dispatch before CP-001 is confirmed.**

## Slice execution order

Derived from each unit's embedded `meta.unit.type` and `meta.unit.dependencies`: `shared-component` → `page` / `component` → `modal` (each modal after its trigger page). A unit starts only when the units listed in its `meta.unit.dependencies` are `merged`.

For UI-bearing slices, implement against an already-frozen `ui-contract.html` that is browser-previewable (hydrated default + state switcher) and requirement-scope aligned. Run `figma-design-to-code` only in this stage (or later visual fix loops), never as a Stage 2 contract author — the frozen contract is the visual source of truth.

## Execution discipline (abstract chain)

The `implement` action always follows this chain, regardless of framework tier:

1. **Isolate** — one worktree/branch per slice.
2. **Task loop** — one implementer per task, sequential by default; TDD inside each task (red → green → refactor).
3. **Per-task review** — first failure → auto-fix loop before user escalation.
4. **Visual acceptance** (UI only) — compare implementation against the reviewed `ui-contract.html` states; auto-fix on first failure.
5. **Verification** — integration checks before merge.
6. **Full analyze + full test** — project static analysis and test suite must pass clean.

How each step is executed depends on the tier (superpowers skills, ECC agents, or native discipline): see [frameworks/superpowers.md](frameworks/superpowers.md), [frameworks/ecc.md](frameworks/ecc.md), [frameworks/native.md](frameworks/native.md).

## Subagent policy

```
Slice tasks independent AND non-overlapping files?
  → NO (default): one implementer per task, sequential, dual review
  → YES (rare): parallel dispatch only for independent test/bug domains
Never: two implementers parallel-editing the same slice file set
```

Gate / blocker / status / merge decisions stay in the main session always.

## Status updates

- `in_dev` when implementation starts.
- `visual_acceptance_passed` after the screenshot matches the reviewed `ui-contract.html` (UI only). Write `visual-acceptance.md` or `visual-acceptance/*.png` before promoting this status.
- `merged` after successful rebase.

## Progress ledger (optional)

Append completed tasks to `.ai-delivery/requirements/<req-id>/progress.md` to survive context compaction. Do not treat progress.md as source of truth — reconcile from artifacts and `status.json`.

## Blockers

| Trigger | Blocker |
|---------|---------|
| Upstream slice not merged | `blocked_dependency_slice` |
| Rebase failed | `blocked_merge_conflict` |
| Tests/review/visual failed after auto-fix | `blocked_verification_failure` |

## Next handoff

Slice complete → `finish` action → `merged`. See [handoff-table.md](handoff-table.md).

## Finishing / PR

After the `finish` action (rebase-merge):

| Environment | Recommended next step |
|-------------|----------------------|
| Cursor | `cursor:babysit` — triage PR comments, fix CI, keep merge-ready |
| Cursor (multi-slice) | Optional `cursor:split-to-prs` to split parallel slices into reviewable PRs |
| Claude / Codex / manual | Open PR, watch CI, address review comments, re-run project validators until green |

Babysit and split-to-prs are handoff recommendations, not hard gates.
