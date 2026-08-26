# Workspace and Worktree Policy

This policy is the single authority for workspace selection in Stage 2, Stage 4, and every execution framework. **Worktrees are optional.** The default workspace is the current checkout.

## Consent boundary

- Creating **or reusing** a worktree requires explicit user confirmation for the current sub-requirement. Prior preferences, a recorded worktree, framework defaults, dirty files, time pressure, CP-UI, and CP-001 do not authorize a worktree. CP-UI and CP-001 do not authorize a worktree.
- Before asking, show the exact proposed path, branch, and any required `/.worktrees/` ignore change. The only allowed worktree path is `<project-root>/.worktrees/<req-id>-<sr-id>`.
- If the user declines, use the current checkout. Preserve unrelated user changes and stop only for a concrete file conflict or another real blocker.
- Record the approved choice and path in the current sub-requirement's canonical `decisions` or `progress` artifact. That approval remains valid for later stages of the same sub-requirement only; it never authorizes another slice.
- Treat legacy `require_isolated_worktree` values as deprecated input and ignore legacy `require_isolated_worktree` as consent or a mandate.

## Project-local constraint

Resolve the project root from Git's common directory, not from an external linked worktree's checkout path. An approved worktree must equal the resolved `<project-root>/.worktrees/<req-id>-<sr-id>` path; another name under `.worktrees/` is not valid. `/private/tmp`, `/tmp`, platform-managed worktree roots, sibling repositories, home-directory worktree roots, and every other external location are forbidden.

Native or external worktree tools may run only when they must accept the exact project-local path. If a tool chooses its own location or only offers an external path, skip that tool. After user confirmation, use a controlled `git worktree add <exact-project-local-path> <branch>` flow instead; never create externally and move afterward.

Before creating the first project-local worktree, keep `.worktrees/` out of the primary checkout's status. Prefer an existing project convention. If a `/.worktrees/` `.gitignore` change is required, include that exact change in the worktree confirmation; do not modify ignore rules silently.

## Existing external worktree

At action entry, compare the current checkout with the project root derived from Git's common directory. If the session is already running in `/private/tmp/...` or any other external worktree, stop production edits and ask the user whether to switch to:

1. the project's current checkout; or
2. the exact project-local path `<project-root>/.worktrees/<req-id>-<sr-id>`.

Do not continue production edits until the user answers. Leave the external worktree unchanged. Switching workspaces does not authorize migrating, recreating, or deleting the external worktree, and external reuse remains forbidden. Any migration, recreation, cleanup, or deletion requires a separate explicit confirmation that names the exact action and target. Read-only inspection and canonical `.ai-delivery` status reporting remain allowed.

## Framework override

Pass this policy and the exact approved workspace to every external skill before invocation. External defaults such as mandatory isolation, native-tool-first placement, automatic reuse, or temp-directory fallback are disabled. `using-git-worktrees` supplies mechanics only; it does not choose whether a worktree exists or where it lives.

Stage 2 and Stage 4 reuse the same **user-approved workspace**, which may be the current checkout or the approved project-local worktree. A framework must never create a second workspace for the slice.
