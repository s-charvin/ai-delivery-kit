# Framework Guide: superpowers

Use this tier for `solution-design` / `implement` / `finish` actions when the superpowers skill pack is installed. superpowers provides execution-discipline skills; the orchestrator supplies the state machine around them.

## Detection signs

superpowers skills present in any user skill directory:

- `~/.claude/skills/superpowers`, `~/.agents/skills/superpowers`, or the repo skill tree contains superpowers skills (e.g. `using-git-worktrees`, `test-driven-development`).

Never clone or symlink superpowers yourself.

## Covered actions

| Action | superpowers skill(s) |
|--------|----------------------|
| `solution-design` | brainstorming flow (solution-design exploration; CP-DESIGN only for `design_mode=full`) |
| `implement` | `using-git-worktrees`, `subagent-driven-development`, `test-driven-development`, `requesting-code-review`, `verification-before-completion` |
| `finish` | `finishing-a-development-branch` |

## `solution-design` usage advice

- Feed the brainstorming flow: `requirement-slice.md`, each enabled UI truth unit's host component + `ui-truth-index.json`, API docs, and the dependency graph.
- Produce architecture, component decomposition, a state/transition model, scenario ID references, and key trade-offs. Runtime Coverage remains in the UI truth index.
- Store the canonical solution design in subreq `design.md` and keep only a pointer in `notes`; set `design_approved: true` after the required review (`design_mode=light` after AI self-review, `design_mode=full` only after explicit user approval). Keep it `false` for `design_mode=none`. Do not write solution-design docs into framework-owned directories.

## `implement` usage advice (per slice)

1. `using-git-worktrees` — locate and resume the Stage 2 worktree for UI slices; create one worktree per slice only when no recorded slice worktree exists.
2. `subagent-driven-development` (default) — one implementer subagent per task, sequential; TDD inside each subagent via `test-driven-development`. Use parallel dispatch only for independent, non-overlapping test/bug domains; never two implementers on the same slice file set.
3. `requesting-code-review` drives the [Review loop](../stage-implementation.md#review-loop-task-level-closed-loop): the reviewer is always a fresh-context subagent; findings go back to the implementer as a fix brief and the review repeats until clean or the `review_loop.max_rounds` budget is exhausted, then escalate to the user.
4. Visual/runtime acceptance (`ui_truth_mode=figma` or `runtime-baseline` only) — execute every v2 profile/state/scenario entry, compare visual evidence against the confirmed preview, verify behavior with project-native tools, and write `visual-acceptance.json`; failures re-enter the same review loop.
5. `verification-before-completion` — integration checks before merge.
6. Full analyze + full test must pass clean before `finish`.

Edit one file at a time during implementation.

## `finish` usage advice

- `finishing-a-development-branch` — structured merge options; rebase onto the development branch (no merge commits).
- Set `merged` only after the rebase succeeds and all gates hold.
- Before `merged`, write `verification.md` in the user's current conversation language. Preserve the three `ai-delivery-verification:*` markers from `templates/verification-template.md`; the status validator rejects `merged` without them.

## Traceability recording

superpowers produces no spec artifacts of its own; `spec_refs.tier` keeps the spec-producing tier (spec-kit / openspec / native). Record worktree branch names and review outcomes in the subreq `notes` or `progress.md`.

## Boundaries

- Gate / blocker / status / merge decisions always stay in the main orchestrator session; superpowers skills run inside the dispatched work.
- Do not invoke the brainstorming flow as a substitute for the Stage 1 light audit.
