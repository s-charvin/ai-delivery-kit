# Framework Adaptation

The orchestrator is **framework-agnostic**: it owns state, gates, blockers, and handoffs, and emits **abstract stage actions** instead of third-party skill names. How an action is executed depends on which AI development framework the user has installed. Never require the user to install anything; adapt to what exists.

## Artifact containment protocol (REQUIRED)

The orchestrator owns artifact placement even when an external framework supplies the method. **External skills provide methods and execution discipline only; their default persistence locations are disabled.**

- Process/governance artifacts include design documents, specs, plans, tasks, todos, status, decisions, progress, review findings and fix briefs, verification evidence, reports, checklists, agent/session metadata, and framework state. Write them only to the canonical path resolved from `.ai-delivery/meta/project-binding.json`, normally under `.ai-delivery/requirements/<req-id>/sub-requirements/<SR-xxx>/`; requirement-wide status, todo, progress, and delivery reports stay at their declared requirement-level canonical paths.
- Writes outside `.ai-delivery/` are limited to production source, project-native tests, goldens or official previews, and runtime assets required by that production surface. Framework configuration that already exists may be read for detection or conventions, but must not be modified as action output.
- Before invoking any external skill, command, agent, or hook, resolve and pass an explicit output map for every artifact it may persist. This caller-provided map overrides paths such as `docs/superpowers/**`, `.superpowers/**`, `.specify/**`, or `openspec/**`.
- If a framework step cannot honor the canonical output map, do not invoke that persistence step. Apply its method in the current session and write the equivalent artifact directly to the canonical `.ai-delivery` path. Do not create an artifact elsewhere and move it afterward.
- Capture a status/content fingerprint ledger before dispatch and compare it after the action. Include every staged, unstaged, untracked, and deleted path reported by `git status --porcelain=v1 --untracked-files=all`, its porcelain status, and its working-tree SHA-256 or a deletion sentinel. In addition, capture an independent filesystem fingerprint for every declared external default output root, including ignored files; cover at least `docs/superpowers/`, `.superpowers/`, `.specify/`, and `openspec/`. Record each entry's relative path, type, and SHA-256 (or symlink target/deletion sentinel). Never rely on Git status alone for those roots. A new path, changed status, changed type, changed target, or changed content hash outside the allowed categories is a containment failure even when that path was already dirty or ignored at entry: record the exact path, set `blocked_verification_failure`, and do not advance the gate. Keep both entry ledgers in session rather than creating another repository artifact; do not delete or rewrite pre-existing user files while auditing.

These rules override conflicting persistence instructions in external skills. Existing `.specify/`, `openspec/`, `.superpowers/`, or `docs/superpowers/` trees are read-only inputs during an orchestrated action, never derived output views.

## Workspace selection (REQUIRED)

[Workspace and Worktree Policy](workspace-policy.md) is the single authority for all framework tiers. The current checkout is the default. Creating or reusing a worktree requires explicit confirmation for the current sub-requirement and the exact path must be `<project-root>/.worktrees/<req-id>-<sr-id>`. Checkpoints and legacy mandatory-isolation flags are not consent.

Before invoking an external skill, pass both the canonical artifact output map and the exact user-approved workspace. Framework instructions that auto-create, auto-reuse, or place a worktree outside the project are disabled. If the session is already in an external worktree, stop production edits and follow the policy's user decision gate.

## Abstract action vocabulary

reconcile emits one of these actions per sub-requirement:

| Action | Meaning | Typical trigger status |
|--------|---------|------------------------|
| `requirement-breakdown` | Kit-owned skill: split the requirement | `draft` |
| `ui-truth-mapping` | Kit-owned capability: controlled visual implementation in the user-approved workspace | `split_ready` when `ui_truth_mode=figma` or `runtime-baseline`, after CP-UI |
| `solution-design` | Explore and propose a solution design; approval depends on `design_mode` | `split_ready` or `acceptance_frozen` when `design_mode` is not `none` |
| `spec` | Produce the sub-requirement specification | after the `design_mode` gate is satisfied |
| `plan` | Produce the technical plan | `spec_ready` |
| `tasks` | Produce the task breakdown | `plan_ready` |
| `implement` | Implement remaining tasks (reuse the Stage 2 approved workspace for UI; TDD + review discipline) | `tasks_ready` after CP-001 / `in_dev` |
| `finish` | Rebase-merge and close the slice | `visual_acceptance_passed` |

`requirement-breakdown` and `ui-truth-mapping` are kit skills and are invoked directly when their capabilities are enabled; `ui-truth-mapping` is gated by CP-UI because it writes production code. `solution-design` is an orchestrator action whose approval behavior follows `design_mode`; all other actions are dispatched through the selected framework tier below.

## Step 0 — Environment self-check (once per run)

At the start of every run, check which frameworks are present and record the outcome in the sub-requirement `decisions.md` (or requirement-level notes when no sub-requirement exists yet):

| Framework | Detection signs |
|-----------|-----------------|
| spec-kit | `.specify/` directory at repo root, or `specify` CLI on PATH |
| OpenSpec | `openspec/` directory at repo root, or `openspec` CLI on PATH |
| superpowers | superpowers skills under user skill dirs (`~/.claude/skills`, `~/.agents/skills`, or the repo skill tree) |
| ECC | ECC plugin/command markers (e.g. `/ecc:*` commands registered in the IDE) |

Do **not** install anything. Detection is read-only; if detection is ambiguous, ask the user once and record the answer.

## Tier selection rules

When several frameworks are present, take the best of each:

1. Spec-producing actions (`spec`, `plan`, `tasks`): prefer **spec-kit**, then **OpenSpec**, then native.
2. Execution-discipline actions (`implement`, `finish`): prefer **superpowers**, then **ECC**, then native.
3. `solution-design` action: use whichever installed framework offers a design/brainstorming flow (superpowers brainstorming, ECC design agents); otherwise run the native solution-design flow.
4. Nothing installed: use the **native tier** for every action.
5. Never mix two spec-producing frameworks on the same sub-requirement. The chosen tier for a sub-requirement is recorded once in `decisions.md` and stays stable across resumes.

## Action dispatch table

| Action | spec-kit | OpenSpec | superpowers | ECC | native |
|--------|----------|----------|-------------|-----|--------|
| `solution-design` | — | — | brainstorming flow | design/review agents | native solution-design flow |
| `spec` | [frameworks/spec-kit.md](frameworks/spec-kit.md) | [frameworks/openspec.md](frameworks/openspec.md) | — | — | [frameworks/native.md](frameworks/native.md) |
| `plan` | [frameworks/spec-kit.md](frameworks/spec-kit.md) | [frameworks/openspec.md](frameworks/openspec.md) | — | — | [frameworks/native.md](frameworks/native.md) |
| `tasks` | [frameworks/spec-kit.md](frameworks/spec-kit.md) | [frameworks/openspec.md](frameworks/openspec.md) | — | — | [frameworks/native.md](frameworks/native.md) |
| `implement` | — | — | [frameworks/superpowers.md](frameworks/superpowers.md) | [frameworks/ecc.md](frameworks/ecc.md) | [frameworks/native.md](frameworks/native.md) |
| `finish` | — | — | [frameworks/superpowers.md](frameworks/superpowers.md) | [frameworks/ecc.md](frameworks/ecc.md) | [frameworks/native.md](frameworks/native.md) |

A `—` cell means that framework does not cover the action; fall through to the next preferred tier or native.

## Loop paradigm

Every stage is a closed loop:

```
entry condition (status + guards) → action (framework tier) → verification gate → advance status / retry / blocker
```

reconcile is the evaluate step: it re-reads governed truth, checks guards, and emits the next action. An action that fails its gate never advances the status machine — it retries within the loop or opens the narrowest blocker.

## Traceability

Regardless of tier, every produced artifact must be recorded in the sub-requirement `traceability.json`. The **canonical artifact always uses the current binding's resolved path under `.ai-delivery/`**; the default layout places sub-requirement artifacts under `.ai-delivery/requirements/<req-id>/sub-requirements/<SR-xxx>/` (see `docs/artifact-layout.md` for the full contract). Framework names record which method was used; they do not authorize a second persisted copy.

Extended `spec_refs` schema (one entry per produced artifact). The example uses the default layout; `canonical_path` must use the repo-relative path resolved from the current binding's `spec` layout key:

```json
{
  "spec_refs": {
    "tier": "spec-kit",
    "artifacts": [
      {
        "kind": "spec",
        "canonical_path": ".ai-delivery/requirements/<req-id>/sub-requirements/<SR-xxx>/spec/spec.md",
        "derived_paths": [],
        "content_sha256": "<sha256 of canonical content>",
        "sync_state": "synced"
      }
    ]
  }
}
```

Canonical path fields:

- `spec_refs.tier`: `spec-kit` | `openspec` | `superpowers` | `ecc` | `native`
- `spec_refs.artifacts[].kind`: exactly one complete entry for each of `spec`, `plan`, and `tasks`
- `spec_refs.artifacts[].canonical_path`: repo-relative path resolved from the corresponding `sub_requirement_artifacts` layout key
- `spec_refs.artifacts[].derived_paths`: empty for every tier; retained only for schema compatibility
- `spec_refs.artifacts[].content_sha256`: current canonical content hash
- `spec_refs.artifacts[].sync_state`: `synced` after the canonical path and hash are current
- `spec_refs.spec_path` / `plan_path` / `tasks_path`: legacy read compatibility only; never emit or combine them with `artifacts[]`
- `source_index.spec`: one entry per artifact with `ref_type` `spec` / `plan` / `tasks`

Governed truth and every process artifact stay in `.ai-delivery`; only production source, project-native tests, goldens/previews, and runtime assets may be written in the host tree.
