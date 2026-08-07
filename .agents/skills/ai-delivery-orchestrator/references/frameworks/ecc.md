# Framework Guide: ECC

Use this tier for `design` / `implement` / `finish` actions when ECC (Everything Claude Code) is installed. ECC is a full harness bundle — agents, skills, rules, hooks, and slash commands — so it mainly strengthens design review and implementation discipline.

## Detection signs

- ECC plugin/command markers registered in the IDE (e.g. `/ecc:*` commands available), or
- ECC-provided agents/rules under the project or user agent configuration.

ECC evolves quickly. Before first use in a run, list the locally available ECC commands/agents once and record the mapping you will use in the sub-requirement `decisions.md`; do not assume command names that are not actually registered.

## Covered actions

| Action | ECC usage |
|--------|-----------|
| `design` | ECC planning/architecture agents or plan commands — seed with `requirement-slice.md`, frozen `ui-contract.html` (UI-bearing), API docs |
| `implement` | ECC task-execution agents with its rules/hooks enforcing conventions; treat its review agents as the per-task review step |
| `finish` | ECC review/verification commands before rebase-merge |

## Usage advice

- Keep the orchestrator loop intact: ECC commands serve a single abstract action each; status transitions, gates, and blockers stay in the main session.
- Prefer ECC's review agents for the per-task [Review loop](../stage-implementation.md#review-loop-task-level-closed-loop): implement → ECC review agent → findings back to the implementer → re-review, until clean or the `review_loop.max_rounds` budget is exhausted (then escalate to the user; never auto-merge).
- If ECC hooks enforce formatting/lint rules, let them run; a hook failure is a verification failure (`blocked_verification_failure` after a review-loop fix round), not a reason to bypass the hook.
- When ECC and another framework are both installed, ECC typically pairs well with a spec-producing tier (spec-kit/OpenSpec): ECC for design/implement/finish, the spec tier for `spec`/`plan`/`tasks`.

## Traceability recording

ECC produces no spec artifacts of its own; `spec_refs.tier` keeps the spec-producing tier. Record the ECC commands/agents actually used in `decisions.md` so a later session can resume with the same mapping.

## Boundaries

- Never install or configure ECC yourself.
- Do not let ECC agents decide gate/status/merge outcomes; they only execute the dispatched action.
