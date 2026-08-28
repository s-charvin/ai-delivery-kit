# Scenario Guidance

This is an optional, trigger-based catalog of change-analysis guidance. It
supplements the host workflow's ordinary delivery rules; it does not define or
replace that workflow.
Select a scenario only when its own trigger matches the requirement. If no
scenario fits, use the ordinary requirement and review rules rather than
inventing one. Optional means the catalog is a reference when a known change
situation applies, not a mandatory delivery activity.
Scenario guidance is an analysis lens, not a new work item or lifecycle rule:
selecting it does not add workflow steps, gates, routes, control states, or
approval requirements.
Scenario IDs describe change situations, not delivery phases or implementation
sequence; do not infer ordering or a new phase from an ID.

## How to apply

1. Compare the requirement with the registry triggers and select only matching
   scenario IDs.
2. A requirement may combine
   scenarios when each trigger and boundary is explicit.
3. Apply each selected scenario only to the surfaces affected by the
   requirement, and stop at its stated boundaries.
4. Put any resulting decision and evidence in the host workflow's existing
   record or current action report. Do not create a stage, artifact type, or
   cross-action maintenance obligation for scenario guidance.

## Recommended decision record

When a selected scenario produces a material decision, use this recommended
compact shape in the host workflow's existing decision, note, or current action
report. Headings may be localized. Do not create a new lifecycle artifact just
for this guidance:

- selected scenario ID and the requirement evidence that triggered it;
- the affected surfaces, decisions, boundaries, owners, and explicit non-goals;
- positive and negative acceptance evidence required by the selected scenario;
- unresolved facts, the decision owner, and the boundary at which work stops.

This note is not a replacement for the host workflow's own records and does not
require downstream artifacts to maintain a link or content hash. When the host
has no durable record for the current action, report the decision in that
action's output and continue; do not create a parallel workflow model.

## Scenario registry

| ID | Trigger | Primary question |
|----|---------|------------------|
| `existing-function-semantic-replacement` | An existing capability is being restructured, redesigned, or given a new business meaning | Which old semantics are preserved, adapted, migrated, or retired? |

Future scenarios should use the same base shape: a trigger, a decision model,
affected surfaces or applicability, boundaries, evidence expectations, and
explicit non-goals. Scenario-specific subsections are optional.
Each entry must have a stable, unique scenario ID and a matching section in
every maintained language copy. Additive entries are preferred; changing the
meaning of an existing ID requires an explicit version or migration note.

## `existing-function-semantic-replacement`

### Trigger

An existing capability is being restructured, redesigned, or given a new
business meaning, and at least one observable boundary may change.

Do not select this scenario for a greenfield capability with no prior behavior,
or for a purely mechanical change whose externally observable contract and
boundaries are demonstrably unchanged.

### Decision model

Choose the narrowest truthful classification:

- `preserve`: implementation may change while external behavior remains the
  same.
- `extend`: the old behavior remains valid and the requirement adds behavior.
- `compatible_replacement`: implementation and internal model change while the
  external contract remains intentionally compatible.
- `breaking_replacement`: the old business meaning, flow, or contract is
  intentionally replaced.
- `unknown`: the requirement does not establish whether old behavior remains.
- `mixed`: different surfaces have explicitly different relationships; each
  surface still needs its own classification and boundary.

Do not silently turn `unknown` into compatibility. A `breaking_replacement`
requires an explicit retirement boundary; a compatible replacement requires a
defined migration or compatibility boundary.

Classification may be summarized at the capability level, while the
old-to-target relationship and the delivery action are recorded independently
for each inventoried surface. One replacement may therefore preserve a utility,
adapt a state mapper, and retire an old entry point without implying that the
whole capability is compatible.

### Inventory

Capture a compact old-to-new behavior diff and a legacy inventory. At minimum,
inventory these surfaces when applicable:

- entry points, routes, deep links, commands, and event replays;
- state, transition, recovery, retry, and concurrency behavior;
- persistence, cache, snapshots, credentials, and invalidation rules;
- protocol adapters, payloads, response mapping, and error handling;
- analytics, notifications, side effects, feature flags, and background work;
- visible surfaces whose interaction or meaning may have changed.

Attach baseline evidence to each applicable surface: a requirement or design
source, an existing test, or observed behavior. Existing tests and generated references
prove only the old implementation; they are not automatic evidence for the
target contract.

For every inventoried surface, use a reuse matrix with separate fields:

- **relationship**: `preserve`, `extend`, `compatible_replacement`,
  `breaking_replacement`, or `unknown`;
- **action**: `preserve`, `adapt`, `migrate`, `retire`, or `unknown`;
- old contract, target contract, owner, and positive and negative acceptance
  evidence.

For a persisted surface, also state whether old data is read, written, migrated,
cleared, or ignored; its version or namespace boundary; the applicable identity
scope; and behavior after restart, crash, rollback, or partial rollout. If a
field is not applicable, record the reason rather than silently omitting it.

Record these facts in the host workflow's existing record or current action
report. Do not copy competing versions into derived documents.

### Boundaries

Do:

- establish the old observable contract before inspecting candidate code for
  reuse;
- verify each reused surface against the target contract and name its owner;
- record a handoff or dependency when an affected surface belongs to another
  owner, and keep implementation within the authorized boundary;
- define migration, rollout, rollback, and invalidation boundaries when
  persistence, authorization, or external effects are involved;
- retire or isolate old paths when the replacement is breaking, then test that
  they are no longer reachable;
- treat visible target surfaces as part of the target contract: implement them
  with real host-stack controls and evidence-backed resources, and record
  static visual confirmation separately from motion confirmation (or an
  explicit no-motion decision);
- preserve the target's real data semantics: absent or unavailable values render
  the intentional empty/omitted state, while deterministic fixtures remain
  confined to the test harness;
- keep the scenario decision and evidence in the host's existing record or
  current action report.

Do not:

- preserve behavior solely for compile compatibility;
- keep old UI semantics, state mappings, entry points, or wiring solely to
  keep a breaking replacement compiling before its owning replacement surface
  is ready;
- treat file location, naming, shared cache keys, or existing screens as proof
  of semantic compatibility;
- add fallback mappings, payload fields, persistence, or side effects outside
  the target contract or an explicitly approved compatibility boundary;
- use an external widget slot, dummy/fixture visual, generic icon, painted
  input shell, or other placeholder to make an in-scope replacement appear
  complete. When a required visual resource is unavailable, stop and ask the
  user to choose empty rendering, defer, or block;
- inject fabricated/default data into production UI when the real value is
  absent; record the empty/omitted behavior or ask for an explicit disposition;
- alter the host workflow's routing or lifecycle merely because this guidance
  was selected, or widen the requirement;
- turn a scenario selection into a repository-wide legacy audit when unrelated
  surfaces are outside the requirement;
- implement another owner's surface merely to make the scenario appear
  complete; record the dependency and stop at the boundary instead;
- guess missing protocol, authorization, migration, or ownership facts.

#### Reuse and retirement

- Structural reuse is allowed for infrastructure, pure utilities, data sources,
  and components whose contract is verified to match the target.
- Structural reuse is not semantic reuse. Do not infer compatibility from code location or naming.
  The same rule applies to an existing screen, a shared cache key, or a familiar adapter.
- Do not retain old state mappings, fallback branches, payload fields, cache
  readers, entry points, or side effects merely to keep old callers compiling.
- For a breaking replacement, old behavior must be retired, isolated, or
  explicitly migrated; an implicit bridge is a defect.
- For a compatible replacement, define the compatibility boundary and test old
  and new representations at that boundary.
- If a required protocol, authorization, migration, or ownership fact is
  missing, mark only the dependent decision or task as awaiting that fact in
  the host workflow's existing notation and ask for it. Continue independent
  work; do not guess endpoint names, token fields, expiry, error codes, or
  equivalent protocol details.

### Evidence

Acceptance must cover the target behavior and the old behavior that must no
longer be reachable. Positive and negative acceptance should exercise applicable
entry points, old snapshots, cache hydration, replayed events, retries,
concurrent calls, and side-effect boundaries. A fresh-context review must ask
which legacy paths can still be reached and whether each remaining reuse has
evidence for semantic compatibility.
For UI-bearing replacements, acceptance must also show that interactive
controls are real and that every visual unit has separate static and motion
evidence. Static golden confirmation alone is insufficient for an animated
surface; an explicit no-motion decision or motion waiver must be recorded when
runtime motion evidence cannot yet be produced.
For every retired or isolated surface, name the retirement boundary and attach
negative evidence for that boundary; do not claim that unrelated, out-of-scope
legacy behavior was removed. Include duplicate-side-effect and stale-test or
generated-reference checks when they apply.

When multiple scenarios are selected, designate one primary scenario and label
the others orthogonal. Merge their analysis by surface. If their decisions
conflict, classify only that surface as `unknown`, stop at its narrow boundary,
and ask the responsible owner; no scenario wins by default.

### Non-goals

- This scenario does not redesign the surrounding delivery workflow or create
  a new lifecycle, approval, or control model.
- It does not require unrelated legacy surfaces to be audited, migrated, or
  kept compatible.
- It does not decide missing product, protocol, authorization, migration, or
  ownership facts; those remain explicit decisions for their owners.

## Extending the catalog

When adding a scenario, keep it optional and technology-agnostic. Define a
stable unique kebab-case ID, trigger, classification or decision model,
affected surfaces or applicability, boundaries, acceptance evidence, and
non-goals. Add scenario-specific subsections only when its trigger requires
them. Add the same ID to the registry and a matching section in every
maintained language copy; validate uniqueness and parity. Do not encode project names, framework
assumptions, host-specific routing, new workflow control tokens, or hidden
compatibility defaults in the catalog. Keep product- or domain-specific field
names and example payload fields out of the catalog as well.
