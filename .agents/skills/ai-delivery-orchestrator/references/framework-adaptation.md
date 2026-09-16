# Framework Adaptation

The orchestrator owns state, gates, blockers, handoffs, and persisted artifact
shape. Installed frameworks contribute reasoning or execution discipline; they
do not add workflow stages or required documents.

## Artifact containment protocol (required)

- Process/governance artifacts belong only at canonical paths resolved from
  `.ai-delivery/meta/project-binding.json`. The sole Stage 3 contract is the
  sub-requirement `design.md`; optional recovery state belongs in `progress.md`.
- Outside `.ai-delivery/`, writes are limited to production source,
  project-native tests, goldens/official previews, and runtime assets.
- Before invoking an external skill, command, agent, or hook, pass the exact
  canonical output map and approved workspace. Defaults such as
  `docs/superpowers/**`, `.superpowers/**`, `.specify/**`, and `openspec/**` are
  disabled.
- If a step cannot honor the map, do not run its persistence phase. Apply the
  useful method in-session and write the canonical artifact directly. Never
  create an external process artifact and move it afterward.
- Fingerprint Git-visible changes and every external default output root before
  and after dispatch, including ignored files, types, symlink targets, and
  SHA-256 values. Any new or changed process artifact outside `.ai-delivery/`
  opens `blocked_verification_failure`; do not delete or rewrite pre-existing
  user files while auditing.

Existing framework trees are read-only inputs during orchestrated work.

## Workspace selection (required)

[Workspace and Worktree Policy](workspace-policy.md) is authoritative. The
current checkout is the default. Creating or reusing a worktree requires
explicit confirmation for the current slice and the exact path
`<project-root>/.worktrees/<req-id>-<sr-id>`. No workflow checkpoint or
framework default provides that consent.

## Abstract actions

| Action | Meaning | Trigger |
|--------|---------|---------|
| `requirement-breakdown` | Kit-owned requirement slicing | `draft` |
| `ui-truth-mapping` | Kit-owned controlled visual implementation | eligible `split_ready` slice after CP-UI |
| `solution-design` | Produce and review the single `design.md` contract | `split_ready` or `acceptance_frozen` |
| `implement` | Execute the current contract with TDD and review | dependency-ready `design_ready` or `in_dev` |
| `finish` | Verify, integrate, and close the slice | implementation/acceptance complete |
| `archive` | Converge completed status in place | all applicable slices `merged` |

Do not emit `spec`, `plan`, or `tasks` actions. CP-DESIGN is used only when
`user_decision_required=true`; the resulting approval also authorizes
implementation inside that scope.

## Environment self-check

Once per run, detect installed frameworks without installing or changing them,
and record the selected methods in `decisions.md`:

| Framework | Detection signs | Useful role |
|-----------|-----------------|-------------|
| spec-kit | `.specify/` or `specify` CLI | optional requirement/design reasoning |
| OpenSpec | `openspec/` or `openspec` CLI | optional brownfield delta reasoning |
| superpowers | skills in a user or repository skill tree | design, TDD, review, finish discipline |
| ECC | registered ECC commands/agents | design, execution, and review discipline |
| native | always available | complete fallback |

When detection is ambiguous, use the native tier unless the distinction would
materially change behavior; then ask once and record the answer.

## Tier selection and dispatch

| Action | Preferred method |
|--------|------------------|
| `solution-design` | superpowers or ECC design reasoning; spec-kit/OpenSpec reasoning may supplement the same `design.md`; otherwise native |
| `implement` | superpowers, then ECC, then native |
| `finish` | superpowers, then ECC, then native |

Spec Kit and OpenSpec must not run their artifact-producing feature/change
pipelines. Their analysis may help shape `design.md`, but `.specify/**`,
`openspec/**`, and separate spec/plan/task outputs remain unchanged.

## Closed loop

```text
entry guards → framework method → contract/verification gate → advance, retry, or block
```

Reconcile re-reads governed truth and emits the next abstract action. A failed
gate does not advance status.

## Traceability

Record the canonical `design.md` path, current SHA-256, source relationships,
and selected reasoning method under the existing `traceability.json`
`source_index.design` contract. Do not emit `spec_refs` or `kind=spec|plan|tasks`
for schema 2.0. Historical `spec_refs` may be read only for legacy
`merged`/`archived` records.
