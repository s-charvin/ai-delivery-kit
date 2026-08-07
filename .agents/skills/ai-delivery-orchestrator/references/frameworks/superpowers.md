# Framework Guide: superpowers

Use this tier for `design` / `implement` / `finish` actions when the superpowers skill pack is installed. superpowers provides execution-discipline skills; the orchestrator supplies the state machine around them.

## Detection signs

superpowers skills present in any user skill directory:

- `~/.claude/skills/superpowers`, `~/.agents/skills/superpowers`, or the repo skill tree contains superpowers skills (e.g. `using-git-worktrees`, `test-driven-development`).

Never clone or symlink superpowers yourself.

## Covered actions

| Action | superpowers skill(s) |
|--------|----------------------|
| `design` | brainstorming flow (design exploration before CP-DESIGN) |
| `implement` | `using-git-worktrees`, `subagent-driven-development`, `test-driven-development`, `requesting-code-review`, `verification-before-completion` |
| `finish` | `finishing-a-development-branch` |

## `design` usage advice

- Feed the brainstorming flow: `requirement-slice.md`, each unit's `ui-contract.html` (UI-bearing), API docs, dependency graph.
- Produce architecture, component decomposition, data model sketch, error/empty/loading plan, key trade-offs.
- Store the summary in subreq `notes`; set `design_approved: true` only after explicit user approval. Do not write design docs into framework-owned directories.

## `implement` usage advice (per slice)

1. `using-git-worktrees` — one worktree per slice.
2. `subagent-driven-development` (default) — one implementer subagent per task, sequential; TDD inside each subagent via `test-driven-development`. Use parallel dispatch only for independent, non-overlapping test/bug domains; never two implementers on the same slice file set.
3. `requesting-code-review` drives the [Review loop](../stage-implementation.md#review-loop-task-level-closed-loop): the reviewer is always a fresh-context subagent; findings go back to the implementer as a fix brief and the review repeats until clean or the `review_loop.max_rounds` budget is exhausted, then escalate to the user.
4. Visual acceptance (UI only) — compare against the reviewed `ui-contract.html` states; failures re-enter the same review loop.
5. `verification-before-completion` — integration checks before merge.
6. Full analyze + full test must pass clean before `finish`.

Edit one file at a time during implementation.

## `finish` usage advice

- `finishing-a-development-branch` — structured merge options; rebase onto the development branch (no merge commits).
- Set `merged` only after the rebase succeeds and all gates hold.

## Traceability recording

superpowers produces no spec artifacts of its own; `spec_refs.tier` keeps the spec-producing tier (spec-kit / openspec / native). Record worktree branch names and review outcomes in the subreq `notes` or `progress.md`.

## Boundaries

- Gate / blocker / status / merge decisions always stay in the main orchestrator session; superpowers skills run inside the dispatched work.
- Do not invoke the brainstorming flow as a substitute for the Stage 1 light audit.
