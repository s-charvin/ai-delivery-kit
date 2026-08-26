# Framework Adaptation

The orchestrator is **framework-agnostic**: it owns state, gates, blockers, and handoffs, and emits **abstract stage actions** instead of third-party skill names. How an action is executed depends on which AI development framework the user has installed. Never require the user to install anything; adapt to what exists.

## Abstract action vocabulary

reconcile emits one of these actions per sub-requirement:

| Action | Meaning | Typical trigger status |
|--------|---------|------------------------|
| `requirement-breakdown` | Kit-owned skill: split the requirement | `draft` |
| `ui-truth-mapping` | Kit-owned capability: controlled visual implementation in the slice worktree | `split_ready` when `ui_truth_mode=figma` or `runtime-baseline`, after CP-UI |
| `solution-design` | Explore and propose a solution design; approval depends on `design_mode` | `split_ready` or `acceptance_frozen` when `design_mode` is not `none` |
| `spec` | Produce the sub-requirement specification | after the `design_mode` gate is satisfied |
| `plan` | Produce the technical plan | `spec_ready` |
| `tasks` | Produce the task breakdown | `plan_ready` |
| `implement` | Implement remaining tasks (reuse Stage 2 worktree for UI; TDD + review discipline) | `tasks_ready` after CP-001 / `in_dev` |
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

Regardless of tier, every produced artifact must be recorded in the sub-requirement `traceability.json`. The **canonical artifact always lives under `.ai-delivery/requirements/<req-id>/sub-requirements/<SR-xxx>/`** (see `docs/artifact-layout.md` for the full contract). Framework directories (`.specify/`, `openspec/`) are **derived/synced views only** — framework tooling writes there first, then the action copies the result back to the canonical path and records its hash.

Extended `spec_refs` schema (one entry per produced artifact):

```json
{
  "kind": "spec",
  "tier": "spec-kit",
  "canonical_path": "sub-requirements/<SR-xxx>/spec/spec.md",
  "derived_paths": ["<framework-dir>/.../spec.md"],
  "content_sha256": "<sha256 of canonical content>",
  "sync_state": "synced"
}
```

Canonical path fields:

- `spec_refs.tier`: `spec-kit` | `openspec` | `superpowers` | `ecc` | `native`
- `spec_refs.spec_path` / `plan_path` / `tasks_path`: canonical paths under `spec/` (`spec/spec.md`, `spec/plan.md`, `spec/tasks.md`)
- `spec_refs.derived_paths`: framework-dir copies (empty for native)
- `source_index.spec`: one entry per artifact with `ref_type` `spec` / `plan` / `tasks`

Governed truth (status, gates, contracts) always stays in `.ai-delivery`; framework artifacts are referenced, never moved, and never treated as the source of truth.
