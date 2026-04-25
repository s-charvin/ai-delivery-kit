# Subagent Budget Policy

- Default to the main session.
- Allow subagents only for independent, frozen, reviewable work.
- Default concurrency: 1 active subagent.
- Temporary concurrency 2 only for independent slices with satisfied dependencies.
- Main session owns gate decisions, worktree creation order, merges, and blocker classification.
- Subagents may handle isolated slice `speckit-*`, isolated worktree implementation, review repair, or visual repair only.
- Never allow a subagent to advance `todo.md` or decide merge readiness.
- Run `prepare-speckit-context` in the main session before delegating official Spec Kit work so the subagent receives frozen `spec-kit-input.md`.
- Order slice execution from `delivery-slices/index.json`.
- A slice can only enter worktree execution after every `depends_on_slices` item is already `merged`.
- Do not pre-create worktrees for future slices whose dependencies are not yet merged.
- Merge and conflict resolution always return to the main session.
