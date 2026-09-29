# Stage 4: Implementation

For Android View, load [the Android View adapter](framework-adapters/android-view.md) for feature-boundary implementation rules, Flow/ViewBinding lifecycle checks, local PNG/GIF evidence, and the limits requiring emulator/device verification.

## When to run

Each dependency-ready sub-requirement at `design_ready` or `in_dev` when
reconcile emits `implement`. See
[stage-4-sdd-bridge.md](stage-4-sdd-bridge.md) for dynamic execution-brief and
progress-ledger rules. The current hash-bound design review authorizes work
inside its scope; there is no separate development checkpoint.

## Slice execution order

Follow the sub-requirement dependency graph and each UI unit's type/dependencies persisted in `ui-truth-index.json`: `shared-component` → `page` / `component` → `modal` (each modal after its trigger page). A unit starts only when its listed dependencies are complete in the slice workspace.

For `ui_truth_mode=figma` or `runtime-baseline`, continue in the **same user-approved workspace used during Stage 2** and implement against the frozen host-stack component plus the v3 profile/state/scenario coverage, evidence scopes, host bindings, and confirmed visual previews recorded in `ui-truth-index.json`. **That component + preview set is the only visual source of truth for Stage 4.** Stage 4 owns business wiring, scenario verification, and remaining implementation; it does not create a second workspace or re-draw the component. `ui_truth_mode=existing` uses the existing component and ordinary behavior/semantic verification; `none` has no UI truth artifact. Provider skills supply evidence; `ui-truth-mapping` remains the Stage 2 author. Never translate a parallel preview from one host stack into another.

Before adding an integration abstraction, trace the host's existing ownership and call path for the same kind of operation: API/client, transport, serialization, repository/use-case, dependency injection, and test seam. Extend that path when it fits. Do not introduce a parallel adapter, client, repository, transport, or injection architecture solely for one new operation or for easier testing; a new layer requires an established project boundary or an explicit requirement decision.

### Visual truth — do not re-query Figma by default

Do not re-query TemPad or official Figma as a pre-implement ritual. Stage 2 already froze the real widget/component. Re-fetching creates a second truth and can disagree with the landed preview.

Reacquire Figma evidence **only** when:

1. The frozen component is missing geometry the task needs, or
2. Visual acceptance failed and the mismatch cannot be resolved from the confirmed preview, or
3. The user explicitly asks to re-pull Figma.

For authorized reacquisition, follow [provider routing](../../ui-truth-mapping/references/figma-provider-routing.md), including official skill prerequisites and installation refusal handling.

If live Figma evidence disagrees with the frozen component / confirmed preview, **the frozen component wins**, unless the user unfreezes the unit or you are in an explicit repair loop.

Figma-origin scenarios are the only scenarios eligible for a 1:1 Figma claim. Requirement/project/user-decision scenarios are approved runtime behavior. Do not silently use runtime conventions to change evidenced Figma pixels; visible accessibility/platform/performance conflicts require an explicit repair decision.

### Layout sizing at implement time

Follow fill / hug / fixed classification from Stage 2. Preview px is an artboard snapshot — **not a runtime constant**.

- `fill` → stretch to the parent; apply the measured insets as padding/margin. Do **not** hardcode the preview px.
- `hug` → intrinsic / content size, with overflow / min / max from the sizing table.
- `fixed` → explicit size from the snapshot px (then the host project's size scale, if any) **only** when the table says fixed (icons, avatars, asset boxes, explicit locks).

If fill detection says `fill`, implement as parent minus insets, not as a copied snapshot width. Do **not** dump every snapshot `width`/`height`/`left`/`top` into layout constants.

If a box is content-bound / i18n / variable length and the sizing table (or requirement / design) does not record overflow / min / max → **stop and ask**. Do not invent a lock from snapshot px.

Prefer constraint layout (flex / stretch / intrinsic). A few fixed or min sizes for unchanging chrome is acceptable; copying the whole artboard as constants is not.

Tests and visual acceptance for `fill`/`hug` boxes assert constraint behavior (stretches with parent, hugs short content, clamps long content) — **not** snapshot `w×h` equality. A visual-acceptance note that scores `fill`/`hug` boxes by matching snapshot px is a review finding, not a pass.

### Runtime scenario verification

Use the exact profiles and scenarios from the v3 index; do not invent a universal device/theme Cartesian matrix. Apply project-native checks for the covered dimensions:

- state/data lifecycle, reachable error/offline/permission/disabled paths, and rapid re-entry;
- container/viewport boundaries, orientation, safe areas, fixed/sticky overlays, IME, scroll, clipping, and hit testing; every editable input exercises empty/not-editing, active-editing, completed/not-editing, IME-hidden, and IME-shown states when applicable, with visuals driven by real control state;
- long/unbroken/localized/RTL content, text scaling or zoom, list-count and numeric/date boundaries; for locale- or data-dependent length, exercise representative supported values including a layout-risk case, then assert rendered geometry and the approved overflow behavior rather than only confirming that a text node exists;
- position-dependent edge fades, masks, gradients, or overlays at leading/interior/trailing scroll states; verify they follow actual scroll state and do not obscure text or hit targets contrary to the approved contract;
- hover/focus/pressed/selected/expanded, keyboard/pointer/touch/gesture alternatives, focus trap/return, and semantics announcements;
- motion trigger/keyframes/timing/interruption/reduced-motion/resource lifecycle and applicable performance checks; the review artifact must show the complete transition or loop without excessive idle time, replay automatically, and decode to the expected frame count and total duration; use the indexed motion preview when available and project-native behavior/manual evidence when it is unavailable;
- image/vector loading/error/offline, crop/focal/aspect/density/theme/cache/semantics behavior;
- supported themes, contrast/state parity, platform semantics, input modes, and native accessibility expectations.

Do not add packages merely to run this matrix. Use existing golden/screenshot, widget/component, semantics/accessibility, integration, and performance facilities. A scenario may be explicitly waived only by the user with timestamp and reason.

### Evidence-scope execution

- `component-only`: reuse the frozen real-component preview and component behavior tests. Record the uncovered host boundary and do not add or imply a host-visual pass.
- `host-static`: enter through the indexed existing test entrypoint, mount the indexed production host, prepare deterministic state/resources, capture the indexed boundary, and verify every required landmark and spatial constraint.
- `host-runtime`: run cheap environment, resource, and visual smoke checks first. Only after visual smoke passes may the expensive native lifecycle suite run. Capture the indexed production host and verify the same landmark/constraint contract.

Never construct a synthetic page to satisfy host evidence. If the real host cannot be mounted or captured as frozen, stop and return the scenario for a corrected capability decision; do not silently downgrade or forge a passing screenshot. Host screenshots and assertion reports belong under the indexed project-native test evidence root outside `.ai-delivery/`.

If component code changes while all regenerated visual preview hashes remain identical, update the component hash and keep existing preview-bound confirmations. If any preview hash changes, regenerate that preview and obtain fresh confirmation; a stale `reviewed_preview_sha256` must block progress.

For `stack: "android-view"`, this retention rule additionally requires unchanged approved behavior and motion contracts. Any changed `render_inputs` requires rerunning affected tests and regenerating affected previews before updating input hashes; retain a corresponding confirmation only when both its preview and approved behavior/motion contract remain unchanged.

When a stable Figma reference bitmap exists, record project-native image-diff evidence with reference/candidate/diff hashes, metric, threshold, actual result, and command. Without a stable reference bitmap, require exact design-value mapping, deterministic preview, and user confirmation; never claim an automated pixel comparison occurred.

## Test design before implementation

For every UI mode, derive cases from original requirement sources, B-###,
AC-###, applicable T-###, and user decisions before coding the bounded unit.
Specify preconditions, inputs/events, expected outcomes, forbidden outcomes,
and the source of each expectation. Unknown business expectations invoke the
requirement-conflict question protocol; implementation behavior is not an oracle.

Select cases by risk and applicability, not an exhaustive Cartesian product:

- Input equivalence classes and boundaries: empty/null, valid/invalid, minimum,
  maximum and just outside each limit, long content and Unicode.
- State transitions: guards passing/failing, illegal transitions, repeated entry,
  navigation return, and permission changes.
- Async ordering: duplicate requests, out-of-order and stale results, timeout,
  cancellation followed by success, retry/idempotency and partial success.
- Lifecycle and consistency: disposal callbacks, restart/restore, persistence
  failures, ownership and preventing old data from overwriting newer changes.
- Integration: the actual entrypoint, state owner, request serialization, result
  handling and UI projection; test doubles must not hide the wiring under test.

Use a decision table for interacting business rules and a transition/sequence
table for order-sensitive behavior. Keep a compact coverage summary in design.md
acceptance notes; detailed cases belong in native tests. Record material exclusions
and risks, not repetitive not_applicable rows. Before implementation, review case
coverage against the original sources independently of the proposed code; the
fresh-context reviewer must also check omitted cases and incorrect expectations.

Choose the lowest test layer that proves the behavior and integration checks
where boundaries matter. Control time, scheduling and external failures with the
host's existing facilities; avoid sleeps and live network dependence. Assert
business results and forbidden side effects, not only mocks or internal calls.
For automatable defects, reproduce with a failing regression test before fixing.
Use property-based or mutation checks selectively for high-risk invariants when
existing tooling makes them practical; they are not universal dependencies.

Before completion, map each AC-### to actual test names/paths, commands and
results in verification.md. Recheck the original requirement for omissions and
unauthorized deviations. Missing, skipped or environment-blocked checks remain
unproven; report residual risks and obtain explicit disposition before claiming
acceptance. Test success alone does not prove requirement completeness.

## Final human UI acceptance

For figma/runtime-baseline slices, after automated checks and clean review,
present one complete slice-level acceptance packet with current preview paths,
scenario scope, static and motion results, limitations and outstanding decisions.
Obtain explicit user acceptance of the implemented static UI and motion (or an
explicit scoped waiver) before visual_acceptance_passed. Record the response,
reviewed scenario/unit IDs, current index SHA-256, evidence hashes, reviewer and
time in verification.md alongside visual-acceptance.json. Stage 2 approval does
not substitute for final acceptance of the integrated result. If motion could
not be previewed earlier, provide the agreed runtime/manual evidence now.
Unchanged evidence can be accepted in one batch; re-review only affected evidence
after changes. Existing structured validators do not establish that a human
actually approved; the orchestrator must verify the recorded user response.

After presenting the complete evidence packet, collect that response under the
orchestrator's **User decision interaction** protocol. Prefer
`request_user_input` when it is available and permitted in the current turn,
runtime, and mode; otherwise use one structured chat question. A permission
approval prompt is not visual or motion acceptance.

## Execution discipline (abstract chain)

The `implement` action always follows this chain, regardless of framework tier:

1. **Resolve workspace** — follow [workspace-policy.md](workspace-policy.md). Reuse the recorded Stage 2 user-approved workspace for `ui_truth_mode=figma` or `runtime-baseline`; otherwise default to the current checkout. Creating or reusing a project-local worktree is allowed only after explicit confirmation for this sub-requirement.
2. **Execution loop** — derive the next bounded unit from `design.md`, dependencies, current code, and tests; run TDD inside each unit (red → green → refactor).
3. **Review loop** — every unit closes through the [Review loop](#review-loop-closed-loop) below; it is complete only when a review round comes back clean.
4. **Visual/runtime acceptance** (`ui_truth_mode=figma` or `runtime-baseline` only) — execute every v3 scenario under its recorded profile and evidence scope with project-native tools. Compare visual scenarios against confirmed previews, exercise behavior scenarios for state/interaction/motion/assets/theme/accessibility/platform/performance expectations, and record schema v2 structured `visual-acceptance.json` with one independent motion acceptance record for every indexed unit. Host scopes require hash-bound `runtime-capture` evidence; `component-only` must not claim host coverage. Static golden evidence never satisfies the motion record. `ui_truth_mode=existing` uses ordinary behavior/semantic evidence; `none` has no visual acceptance artifact. Failures enter the same review loop. Snapshot `w×h` equality is not a pass for fill/hug boxes. Data-bound visuals with no real value must be accepted as empty/omitted, not as fabricated fixture content.
5. **Verification** — integration checks before merge; record human-readable evidence in the user's current conversation language in `verification.md` (template `templates/verification-template.md`; remove its language instruction comment).
6. **Full analyze + full test** — project static analysis and test suite must pass clean.

Before claiming a clean verification gate, classify every failure as an
introduced regression, pre-existing baseline, environment/tooling failure, or
test/contract contradiction. Re-run the narrowest failing evidence against the
unchanged baseline when possible, and record the command, observed result, and
classification. A baseline or environment failure is not a pass; it requires an
explicit user waiver or a scoped blocker. If a test contradicts the approved
contract, stop and resolve the contract/test decision before weakening
production behavior.

How each step is executed depends on the tier (superpowers skills, ECC agents, or native discipline): see [frameworks/superpowers.md](frameworks/superpowers.md), [frameworks/ecc.md](frameworks/ecc.md), [frameworks/native.md](frameworks/native.md).

### Failure triage before editing code

When a triage result is reusable, append the problem and the attempted solution
to the requirement-level `retrospective.md` before trying another solution.
Afterward tell the user the problem ID and the recorded conclusion. This is a
memory aid, not a substitute for current evidence or an implementation-stage gate.

When an execution unit stalls or a scenario fails, first classify the failure and verify
the smallest candidate cause before changing business code. Check candidates in
roughly this order: state propagation / wiring; copy vs. reference semantics;
model representation; time and async ordering; resource availability or an
as-yet-unconfirmed protocol. Then make the smallest change and re-run only the
narrowest failing evidence.

Common classes with their default fix path:

- **Async restore racing live user state.** Delayed initialization or restore
  must treat the user's already-advanced live state as the local truth: merge
  configuration and appearance into it, but never overwrite live progress with
  a later-arriving snapshot.
- **State writes not reaching the rendered owner.** After asynchronous
  initialization or hydration, verify that the state mutation notifies the
  actual rendered owner and that a changed content identity resets any
  stateful renderer that must not be reused. Test empty-to-loaded, re-entry,
  and stale-instance paths; changing a model without observing the view is not
  a successful transition.
- **Debug gates leaking into production.** A temporary early return, mock, or
  disabled path must be explicit, observable, and isolated. Callers must be
  able to distinguish "empty result" from "disabled"; never leave a silent
  debug disable inside a shared production path.
- **Runtime callbacks treated as proof of completion.** Completion or
  transition events can fire early, on the wrong track, or out of order. Treat
  them as candidate signals and guard visual/flow duration with a minimum
  elapsed time plus a business-layer timeout fallback.
- **Two visible layers overlapping during a swap.** Define a single
  visible-layer owner and switch atomically once the real resource is ready;
  delaying a few frames only lowers the repro rate.
- **Parallel layout algorithms for one visual entity.** Unify geometry,
  centering, and sizing in one layout/coordinate source of truth instead of
  patching per-surface constants.
- **Folding several states into one flag.** Do not collapse "request
  triggered", "step entered", "server completed", "still needed locally", or
  "credential still valid" into one boolean. Model request timing, lifecycle,
  persistence semantics, one-time permissions, and restart behavior
  separately; deduplicate same-session requests; do not fake success on
  failure.
- **Source data replaced by local defaults.** Preserve source-owned identity,
  value, and ordering at the UI and protocol boundaries. Do not hardcode a
  label or identifier, sort or normalize a source-ordered list, or fabricate a
  fallback when the contract does not authorize it. Test a non-default source
  value through selection, state projection, and the outgoing boundary.
- **Preparation work coupled to a presentation toggle.** Keep resource
  preparation/upload identity and its result independent from a later display
  or publish toggle. Key reusable results by the source identity, and let the
  toggle change only the outgoing projection. A generation token can prevent
  stale completion from being applied; it cannot cancel an already-sent
  request. Test completed, in-flight, and toggle-round-trip cases with request
  counts and resource identities, and verify any reuse, detach, or cleanup
  semantics at the protocol boundary before choosing re-upload or deletion.
- **Capability classification split across entry points.** When several views
  expose the same source resource or capability, compute one identity-keyed
  result with an explicit source, loading/error/empty state, and platform
  boundary, then have each view project that result. Do not let each entry
  point derive a local boolean or use evidence from one platform to claim
  another platform's native behavior. Test the same identity through every
  applicable entry point and keep unsupported platform cases explicitly
  unproven.
- **Telemetry treats change as display.** First entry, restored entry,
  re-render, and step switch have different meanings. Fire the initial
  exposure explicitly, land event producers and consumers as pairs, and mark
  unimplemented remote events as unfinished instead of emitting local
  substitutes.
- **Half-finished code polluting verification.** Keep every intermediate state
  compilable, land producer/consumer pairs together, replace scattered string
  literals with typed constants, and run static checks before the slice tests.
  A partial state is not acceptance evidence.
- **Incremental text sliced by storage units.** A byte/code-unit index is not a
  user-visible character boundary. Typewriter, truncation, preview, and
  streaming paths must use the host's grapheme-aware API (or an equivalent
  Unicode-safe representation) and include a regression case for surrogate
  pairs, combining marks, and other multi-code-unit characters. Never pass a
  partial character to a renderer.

### Decision corrections retire superseded artifacts

When the user confirms a new decision, correction, or scope narrowing
mid-delivery, retire the superseded implementation assumptions, tests, wiring,
branches, cache behavior, and documentation statements in the same change batch
or the immediate follow-up. Do not keep the old path as a fallback or add a
compatibility shim. A temporary assumption or guess — endpoint names, token
fields, expiry, error codes, migration facts — must be marked as such in the
record and must never be written as a confirmed fact.

## Review loop (closed loop)

Every execution unit and every visual-acceptance failure closes through this loop, regardless of framework tier:

```
implementer finishes the bounded unit
  → reviewer (fresh context) reviews against the execution brief + design contract
  → clean → record the review outcome → next unit
  → findings → findings list becomes the fix brief → implementer fixes → re-review
  → still not clean after review_loop.max_rounds rounds → stop and escalate to the user
```

Rules:

- The reviewer always runs in fresh context (a subagent where the tier supports it), never the implementer reviewing itself.
- Each round's findings and fix summary are appended to `progress.md` for traceability and to the review-rounds area identified by its stable marker in `verification.md` (the verification artifact).
- Iteration budget `review_loop.max_rounds` defaults to 3. Resolution order: sub-requirement `decisions.md` override → `.ai-delivery/meta/workflow-policy.json` `review_loop.max_rounds` → default 3.
- Budget exhausted: pause, report the outstanding findings to the user, and either open `blocked_verification_failure` or follow the user's direction. **Never auto-merge work whose latest review round is not clean.**
- The loop owner is the main orchestrator session; it decides clean/not-clean from the reviewer report, not from the implementer's claim.

## Subagent policy

```
Slice units independent AND non-overlapping files?
  → NO (default): one implementer per unit, sequential, dual review
  → YES (rare): parallel dispatch only for independent test/bug domains
Never: two implementers parallel-editing the same slice file set
```

Gate / blocker / status / merge decisions stay in the main session always.

## Status updates

- `in_dev` when implementation starts.
- Set `visual_acceptance_passed` only for `ui_truth_mode=figma` or `runtime-baseline`, after schema v2 `visual-acceptance.json` binds the current v3 index and every scenario is passed or explicitly waived with evidence appropriate to its frozen scope.
- `merged` after successful rebase, and only when `verification.md` is signed (the validate-delivery-status gate rejects `merged` without it).

## Progress ledger (optional)

When cross-session recovery is useful, record completed and pending work,
blockers, review outcomes, and verification commands/results in
`.ai-delivery/requirements/<req-id>/progress.md`. Do not turn it into a second
plan or treat it as source of truth; reconcile from governed artifacts and
`status.json`.

## Blockers

| Trigger | Blocker |
|---------|---------|
| Upstream slice not merged | `blocked_dependency_slice` |
| Rebase failed | `blocked_merge_conflict` |
| Tests/review/visual failed after auto-fix | `blocked_verification_failure` |

## Next handoff

Slice complete → `finish` action → `merged`. See [handoff-table.md](handoff-table.md).

When every sub-requirement is `merged`, reconcile enters `runtime_mode=closing` (CP-ARCHIVE). Before the final archive command, instantiate `templates/delivery-report-template.md` in the user's current conversation language, remove its language instruction comment, and retain all placeholders. Run `scripts/archive-subrequirement.py` per subreq to update status to `archived` in place; it must not create a snapshot or copy canonical artifacts. Pass the prepared template to the final command with `--delivery-report-template <path>`. The requirement becomes `completed` only once all subreqs are `archived` and the localized `delivery-report.md` exists.

## Finishing / PR

Before the `finish` action creates a commit (rebase-merge), inspect
`git diff --cached --name-status` and compare
it with the current execution unit's declared file scope. Stage only owned paths; pre-existing
staged, unstaged, untracked, ignored, or generated files are not consent to
include them. Never use a broad add/commit command to inherit another user's
staging area. If the staged set is contaminated, remove only the unrelated
paths from the index while preserving their worktree contents, then re-check the
staged diff before committing.

| Environment | Recommended next step |
|-------------|----------------------|
| Cursor | `cursor:babysit` — triage PR comments, fix CI, keep merge-ready |
| Cursor (multi-slice) | Optional `cursor:split-to-prs` to split parallel slices into reviewable PRs |
| Claude / Codex / manual | Open PR, watch CI, address review comments, re-run project validators until green |

Babysit and split-to-prs are handoff recommendations, not hard gates.
