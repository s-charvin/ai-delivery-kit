# Stage 4: Implementation

## When to run

Each sub-requirement at `tasks_ready` after CP-001 user confirmation. See [stage-4-sdd-bridge.md](stage-4-sdd-bridge.md) for SDD mapping and progress ledger rules.

**Do not dispatch before CP-001 is confirmed.**

## Slice execution order

From `section-map.json`: `shared-shell` → `page` → `modal` (each modal after its trigger page). A unit starts only when structural dependencies are `merged`.

## Subagent policy

```
Slice tasks independent AND non-overlapping files?
  → NO (default): subagent-driven-development — one implementer per task, sequential, dual review
  → YES (rare): dispatching-parallel-agents only for independent test/bug domains
Never: two implementers parallel-editing the same slice file set
```

Gate / blocker / status / merge decisions stay in the main session always.

## Implementation chain (per slice)

1. **`using-git-worktrees`** — one worktree per slice.
2. **`subagent-driven-development`** (default) — each task in a fresh subagent; TDD via `test-driven-development` inside each subagent.
3. **`requesting-code-review`** — first failure → auto-fix loop before user escalation.
4. **Visual acceptance** (UI only) — screenshot vs YAML contract states; auto-fix on first failure.
5. **`verification-before-completion`** — integration checks before merge.
6. **Full analyze + full test** — project static analysis and test suite must pass clean.
7. **`finishing-a-development-branch`** — structured merge options; rebase onto development branch (no merge commits).

## Status updates

- `in_dev` when implementation starts.
- `visual_acceptance_passed` after screenshot matches YAML (UI only). Write `visual-acceptance.md` or `visual-acceptance/*.png` before promoting this status.
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

Slice complete → `finishing-a-development-branch` → `merged`. See [handoff-table.md](handoff-table.md).

## Finishing / PR

After `finishing-a-development-branch`:

| Environment | Recommended next step |
|-------------|----------------------|
| Cursor | `cursor:babysit` — triage PR comments, fix CI, keep merge-ready |
| Cursor (multi-slice) | Optional `cursor:split-to-prs` to split parallel slices into reviewable PRs |
| Claude / Codex / manual | Open PR, watch CI, address review comments, re-run project validators until green |

Babysit and split-to-prs are handoff recommendations, not hard gates.
