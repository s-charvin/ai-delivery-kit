# Framework Guide: Native Tier (built-in fallback)

Use this tier when **no** external framework (spec-kit / OpenSpec / superpowers / ECC) is installed. It is the quality floor of the orchestrator: lightweight artifacts inside the sub-requirement directory plus built-in discipline rules. Native-tier output must be just as traceable as framework-tier output.

All native artifacts live beside the slice: `.ai-delivery/requirements/<req-id>/sub-requirements/<subreq-id>/`.

## `design` action (native design flow)

Inline in the main session (no separate tool):

1. Read `requirement-slice.md`, frozen `ui-contract.html` (UI-bearing), API docs, dependency graph.
2. Produce: architecture sketch, component decomposition, data model, error/empty/loading plan, key trade-offs.
3. Append a compact summary to the subreq `notes` field and present it to the user.
4. CP-DESIGN: set `design_approved: true` only after explicit user approval.

## `spec` action — `spec.md`

Create `sub-requirements/<subreq-id>/spec.md` with exactly four sections:

```markdown
# <subreq-id> Spec

## Problem
<one paragraph: what is broken or missing>

## Goal
<observable outcome, phrased as acceptance-relevant behavior>

## Scope
- In scope: ...
- Out of scope: ...

## Acceptance Criteria
- [ ] testable criterion 1
- [ ] testable criterion 2
```

Audit against the frozen `ui-contract.html` states for UI-bearing slices, then set `spec_ready`.

## `plan` + `tasks` actions — `tasks.md`

The native tier folds plan and tasks into one file to stay lightweight. Create `sub-requirements/<subreq-id>/tasks.md`:

```markdown
# <subreq-id> Tasks

## Plan
<2-5 sentences: approach, key files/components, sequencing rationale>

## Tasks
- [ ] T1 <task> — files: <edit surface> — test: <test pointer or how to verify>
- [ ] T2 ...
```

Rules:

- One task = one implementable step with an explicit edit surface and a test pointer.
- Order tasks by dependency; shared components before consumers.
- Audit granularity and file scope before setting `tasks_ready`.

For the native tier, `spec_refs.plan_path` in `traceability.json` points at `tasks.md` as well (the Plan section is the plan artifact).

## `implement` action — built-in discipline

No subagent framework is required, but the discipline is non-negotiable:

1. **Isolate** — one branch per slice; use a worktree when the repo supports it.
2. **TDD first** — write a failing test for the task before production code; keep the loop red → green → refactor.
3. **Small steps** — one file at a time, small commits prefixed with the subreq id.
4. **Self-review loop** — after each task, re-read the diff against the task's acceptance notes; first failure → auto-fix before escalating to the user.
5. **Verify before completion** — run project static analysis and the full test suite; never claim a task done without evidence.

## `finish` action — built-in merge checklist

1. Full analyze + full test pass clean.
2. Visual acceptance evidence written (UI only): `visual-acceptance.md` or `visual-acceptance/*.png`.
3. Rebase onto the development branch (no merge commits); resolve conflicts, re-run tests.
4. Open/merge the PR, then set `merged`.

## Traceability recording

In the sub-requirement `traceability.json`:

- `spec_refs.tier`: `"native"`
- `spec_refs.spec_path`: `sub-requirements/<subreq-id>/spec.md` (repo-root-relative path in practice)
- `spec_refs.plan_path` / `tasks_path`: `sub-requirements/<subreq-id>/tasks.md`
- `source_index.spec`: entries with `ref_type` `spec` / `tasks`

## Boundaries

- Native artifacts never leave the sub-requirement directory; do not invent repo-wide `specs/` trees.
- If the user later installs a framework, new sub-requirements may switch tiers (recorded in `decisions.md`); already-advanced sub-requirements keep their original tier.
