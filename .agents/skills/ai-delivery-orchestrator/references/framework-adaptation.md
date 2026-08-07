# Framework Adaptation

The orchestrator is **framework-agnostic**: it owns state, gates, blockers, and handoffs, and emits **abstract stage actions** instead of third-party skill names. How an action is executed depends on which AI development framework the user has installed. Never require the user to install anything; adapt to what exists.

## Abstract action vocabulary

reconcile emits one of these actions per sub-requirement:

| Action | Meaning | Typical trigger status |
|--------|---------|------------------------|
| `requirement-breakdown` | Kit-owned skill: split the requirement | `draft` |
| `ui-truth-mapping` | Kit-owned skill: freeze UI contracts | `split_ready` (UI-bearing) |
| `design` | Explore and propose a design; needs user approval (CP-DESIGN) | `split_ready` (non-UI) / `acceptance_frozen` with `design_approved: false` |
| `spec` | Produce the sub-requirement specification | after `design_approved` |
| `plan` | Produce the technical plan | `spec_ready` |
| `tasks` | Produce the task breakdown | `plan_ready` |
| `implement` | Implement tasks (worktree + TDD + review discipline) | `tasks_ready` after CP-001 / `in_dev` |
| `finish` | Rebase-merge and close the slice | `visual_acceptance_passed` |

`requirement-breakdown` and `ui-truth-mapping` are kit skills and are invoked directly. All other actions are dispatched through the selected framework tier below.

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
3. `design` action: use whichever installed framework offers a design/brainstorming flow (superpowers brainstorming, ECC design agents); otherwise run the native design flow.
4. Nothing installed: use the **native tier** for every action.
5. Never mix two spec-producing frameworks on the same sub-requirement. The chosen tier for a sub-requirement is recorded once in `decisions.md` and stays stable across resumes.

## Action dispatch table

| Action | spec-kit | OpenSpec | superpowers | ECC | native |
|--------|----------|----------|-------------|-----|--------|
| `design` | — | — | brainstorming flow | design/review agents | native design flow |
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

Regardless of tier, every produced artifact must be recorded in the sub-requirement `traceability.json`:

- `spec_refs.tier`: `spec-kit` | `openspec` | `superpowers` | `ecc` | `native`
- `spec_refs.spec_path` / `plan_path` / `tasks_path`: concrete artifact paths
- `source_index.spec`: one entry per artifact with `ref_type` `spec` / `plan` / `tasks`

Governed truth (status, gates, contracts) always stays in `.ai-delivery`; framework artifacts are referenced, never moved.
