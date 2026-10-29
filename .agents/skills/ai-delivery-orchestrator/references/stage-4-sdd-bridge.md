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

Run focused TDD inside each unit; one implementer may complete consecutive units
within a coherent batch before independent review. A batch follows one observable
behavior or existing state owner and includes a complete, compilable call path
with its applicable tests. Do not collect unrelated work indefinitely. Review
high-risk ownership or persistence boundaries before dependent implementation.
When a reusable failure appears, update the requirement-level
`retrospective.md` before another solution attempt and report the `RET-###` ID.

<a id="ownership-preserving-execution-brief"></a>
## Ownership-preserving execution brief

For changes to existing code, inspect its governing repository instructions
and the real call path before choosing task boundaries or a test shape. The
parent's brief carries these four compact entries; reuse references rather
than copying whole specifications:

| Entry | Required content |
|-------|------------------|
| Constraints | Applicable repository instruction paths and the specific rules this unit must preserve; distinguish source requirements from implementation suggestions. |
| Existing authority | Concrete state/resource owner, entry and terminal transitions, and existing guards to reuse. Investigate unknown ownership before delegating edits. |
| Change boundary | Observable change, owned edits, shared dependencies, and the rationale for any proposed abstraction, state, or authority. |
| Verification | Required behavior and forbidden effects, then the lowest suitable existing test layer plus integration evidence at shared boundaries. |

Requirements, documents, task assignments, and file ownership are tracking or
execution boundaries; they do not establish independent production owners.
Changes that share a lifecycle, mutable authority, or terminal guard stay with
one coherent implementer or run sequentially against the same owner. Different
files alone do not make them independent; read-only investigation may proceed
in parallel.

The implementer reads the applicable repository instructions directly and
checks the brief against them. A delegated brief or framework preference does
not waive user or repository constraints. Correct a technical task split within
the authorized scope and tell the parent; surface a conflict that needs a user
decision before dependent edits.

Choose tests after confirming production ownership. Independent or pure-logic
tests cover genuine existing logic; requesting them does not justify extracting
a production lifecycle solely to make it testable. Identifiers and timestamps
may be additional context without becoming another authority for readiness,
completion, validity, or deduplication. New lifecycle state or authority needs
a distinct semantic fact not already expressed or derived by the existing
owner. Stateless extraction may serve reuse, clarity, or a real dependency
boundary while preserving that authority; a separate task or easier test alone
is insufficient. If the suitable host test is slower,
use it or record the real verification gap instead of changing the architecture
to satisfy the brief.

The return summary identifies reused guards and explains any added state or
abstraction; final integration review checks them against the combined call
path, not only each unit's passing tests. Keep this in the transient brief and
existing review evidence; do not add a new artifact or approval gate.

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
budget is exhausted. Review the integrated batch, including shared boundaries,
not each mechanical unit followed by a duplicate full-slice pass. Multiple batches
still require a final integration check of their combined call path; reuse valid
review coverage and inspect only new interactions. Complete required visual/motion
acceptance and final verification using the evidence-reuse rules in that guide.

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
