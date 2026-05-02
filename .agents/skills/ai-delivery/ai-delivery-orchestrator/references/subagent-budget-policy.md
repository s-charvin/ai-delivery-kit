# Subagent Budget Policy

- Default to the main session.
- Subagents are allowed only in Stage 2 development after one concrete `SR-*` has already entered implementation.
- Do not use subagents in routing, reconcile, requirement breakdown, mapping, acceptance freeze, interaction design, Spec Kit generation, or gate decisions.
- Scope every delegated task to the currently active `SR-*` only.
- Do not treat delivery slices or implementation tasks inside one `SR-*` as a deeper governed child requirement tier.
- Allow subagents only for independent, frozen, reviewable implementation, review-repair, or visual-repair work inside that active `SR-*`.
- Only use subagents when at least two independent runnable implementation tasks can proceed in parallel after dependency review.
- If fewer than two independent runnable implementation tasks exist, keep the work in the main session.
- Allow at most 2 active subagents when the parallelism threshold is satisfied.
- Main session owns dependency review, gate decisions, worktree creation order, merges, and blocker classification.
- Never allow a subagent to advance `todo.md` or decide merge readiness.
- Never allow a subagent to spawn a deeper subagent tree beneath the same `SR-*`.
- Order slice execution from `delivery-slices/index.json`.
- A slice can only enter worktree execution after every `depends_on_slices` item is already `merged`.
- Do not pre-create worktrees for future slices whose dependencies are not yet merged.
- If delegated work creates worktrees, complete coding first, then have the main session rebase each finished worktree branch onto the current development branch and reintegrate them one by one in dependency order.
- Keep history linear during reintegration; do not use merge commits for delegated worktree branches.
- Merge and conflict resolution always return to the main session.
