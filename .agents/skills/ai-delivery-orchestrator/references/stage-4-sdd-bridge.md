# Stage 4: Implementation Bridge

Maps the `implement` action to bounded execution and `.ai-delivery` progress
evidence. Concrete execution discipline follows the selected framework tier.

## When to run

Run when reconcile emits `NEXT_ACTION=implement` for a dependency-ready
`design_ready` or `in_dev` slice. A valid design review is the authorization for
work inside that scope; there is no separate development checkpoint.

For `figma` or `runtime-baseline`, resume the exact workspace approved in Stage
2. Do not create a second workspace. Other modes follow
[workspace-policy.md](workspace-policy.md), defaulting to the current checkout.

## Design contract to execution brief

Derive the next smallest coherent execution unit from current evidence:

| Source | Execution use |
|--------|---------------|
| `design.md` scope and `B-###` behavior | Allowed behavior and bounded objective |
| `AC-###` and traceability | TDD and acceptance criteria |
| dependency graph and project architecture | Safe ordering and edit ownership |
| current code and tests | Concrete files and verification commands |
| UI truth scenarios, when enabled | Visual, interaction, motion, asset, and runtime evidence |
| `progress.md`, when present | Already completed work, pending work, blockers, and last verification result |

The brief is transient execution context, not a new governed artifact. Do not
persist `spec.md`, `plan.md`, or `tasks.md`, and do not copy file-level steps
into `design.md`.

Each execution unit closes through TDD and fresh-context review before the next
unit. When a reusable failure appears, update the requirement-level
`retrospective.md` before another solution attempt and report the `RET-###` ID.

## Optional progress ledger

Use `.ai-delivery/requirements/<req-id>/progress.md` only when work must survive
compaction, handoff, or another session. Keep four concise sections:

- completed work and linked behavior/acceptance IDs;
- pending work;
- blockers and their scope;
- verification commands, results, and review outcomes.

`progress.md` is a recovery aid. Reconcile from `status.json`, `design.md`,
dependencies, and governed evidence; never promote a gate from progress alone.

## Review and acceptance

Run the closed review loop in
[stage-implementation.md](stage-implementation.md#review-loop-closed-loop):
implement → fresh-context review → fix → re-review until clean or the configured
budget is exhausted. Then run the full slice review, required visual/motion
acceptance, and final verification.

For enabled UI truth, instantiate `templates/visual-acceptance-template.json` as
`visual-acceptance.json`. Preserve its machine keys/enums and localize summaries.
Schema v2 must bind the current v3 index and contain exactly one result for every indexed scenario id at its frozen
`evidence_scope`:

- `component-only` uses the frozen real-component preview plus applicable
  component behavior evidence and never claims host composition;
- `host-static` and `host-runtime` require hash-bound runtime capture, producing
  test, geometry/landmark assertions, command, reviewer binding, and matching
  host provenance;
- every indexed unit has independent motion acceptance. Static golden evidence
  never substitutes for motion acceptance.

Runtime screenshots remain under the indexed project-native evidence root
outside `.ai-delivery/`. Waivers require user identity, timestamp, and reason.

## Status chain

```text
design_ready → in_dev → [visual_acceptance_passed] → merged
```

`ui_truth_mode=none` and `existing` skip `visual_acceptance_passed`; existing UI
changes use ordinary behavior and semantic evidence.
