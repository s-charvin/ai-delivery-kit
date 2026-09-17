# Android View delivery adapter

Read for XML, Activity, Fragment, RecyclerView, or custom View work. Keep the
existing stages and canonical `design.md`; this adapter does not introduce
Compose, an extra state, or another approval gate.

## Stage 1: classify the feature boundary

Inspect the target module, Gradle variant, SDK/JDK, language, architecture,
async mechanisms, resources, navigation, and existing rendering/test facilities.
Record whether this is an existing feature extension or an independent feature.

| Ownership | Implementation rule |
|---|---|
| Existing page/feature repairs, extensions, extracted helpers | Preserve its MVP/MVVM/MVI, language, and async mechanisms. |
| Independent new page or feature module | Kotlin + MVI + Flow/StateFlow + ViewBinding. |
| New feature reusing existing Repository, Service, or navigation | Adapt at the existing boundary; do not rewrite the old implementation. |
| Utilities, local custom Views, ViewHolders | Use responsibility-appropriate techniques; do not create a meaningless MVI Store. |

A new file is not necessarily a new feature. An independent feature hosted by
an old Activity still owns its own MVI boundary. Ask and record a decision only
if competing ownership boundaries materially change scope or maintenance.

## Stage 3: one design contract

Default to an AndroidX ViewModel implementing a small MVI loop. The View submits
`Intent/Event`; a pure Reducer/Decision returns state and commands. The ViewModel
executes I/O and dispatches result events back into the loop. Expose read-only
`StateFlow<UiState>` and keep mutation private. Do not require a third-party MVI
framework or separate Store/Reducer/EffectHandler classes for a simple feature.

Record business state, request state, local input, and UI projection ownership
in `design.md`, including errors, retry, cancellation, duplicate actions,
concurrency, stale results, and restoration. A compact transition table is
enough for simple behavior; use the existing complex state-flow contract only
when justified. MVI alone never triggers `state_flow_required` or CP-DESIGN.

Keep one-time `UiEffect` separate from persistent `UiState`. Specify delivery,
discard, or acknowledgement semantics while backgrounded, on rotation, on back,
and on recreation. A Channel or SharedFlow configuration is not by itself a
reliable-delivery guarantee. If delivery must survive disconnection or process
death, define ownership, durable storage, identifiers, and acknowledgement.
Use existing Repository/SavedStateHandle boundaries where appropriate; ViewModel
retention does not prove process recovery. Unknown business outcomes use the
existing requirement-conflict question protocol.

Collect Flow with `repeatOnLifecycle(STARTED)`. In a Fragment, use
`viewLifecycleOwner.lifecycleScope` and its lifecycle, not the Fragment's longer
lifetime. Release binding, listeners, animation callbacks, and View references
in `onDestroyView`; a ViewHolder owns its own binding. Cancellation and
resubscription must follow the declared state/effect semantics.

## Stage 2 and Stage 4: rendering and verification

For PNG/GIF capture and v3 evidence binding, read the sibling UI Truth Mapping
skill's `references/framework-adapters/android-view/README.md`. Reuse established
project facilities. When absent, recommend Robolectric Native Graphics with
Roborazzi: these are community tools exercising real Android Views, not official
Android screenshot APIs. This is the Android-specific interpretation of the
shared host-stack preview requirement, not a claim of device fidelity.

Mount production XML, binding, theme, resources, and controls. Local fixtures
may provide deterministic data through production seams; kit fixture visuals
are never substitutes for a business project's evidence-backed resources.
Verify applicable density/dp/sp/px, fontScale, locale/RTL, night mode, insets,
`wrap_content`, `match_parent`, ConstraintLayout `0dp`, long text, and list edges.
Layout Editor and XML `tools:` values are not rendered acceptance evidence.

Old features retain existing tests. New features cover pure transitions,
ViewModel/Flow, real View rendering, duplicate actions, cancellation, stale
responses, effect consumption, Fragment View recreation/binding release,
subscription stop/restart, and RecyclerView reuse. Repeat capture and failure
paths to expose leaked clocks, listeners, resources, or stale output reuse.

Use local tests for state, interaction, geometry, recreation, and resource
ownership. Use emulator/device evidence for actual permission dialogs, IME,
system back, window behavior, platform media, and supported native surfaces.
Dialog/PopupWindow capture must target their actual window. SurfaceView,
WebView, media, GL/Spine and similar surfaces need capability-specific device
coverage. Activity recreation is not process-death verification. Record each
uncovered platform behavior; a local pass cannot establish it.

For `component-only`, mount the production component in a test container. For
`host-static`, use an existing entrypoint mounting the production Activity or
Fragment. For `host-runtime`, capture the production host on a device. Synthetic
test pages cannot manufacture host evidence. Preserve separate static, motion
(including explicit no-motion), and final human integration acceptance.

## Reference environment and distribution

The kit fixture lives at `tests/fixtures/android-view/`. Its reference versions
are JDK 17, AGP 8.13.2, Gradle 8.13, Kotlin 2.3.21, compileSdk 36,
Robolectric 4.14.1, and Roborazzi 1.74.0. Pin and run the fixture before claiming
that combination works in an environment; a listed version is not test evidence.
Do not force a business project to upgrade to this combination.

Skill guides/capture helpers ship with skill assets. The fixture is kit-only;
`init` must not copy it, alter business Gradle dependencies, or create governance
state in the kit root. The independent Android CI requires JDK/SDK and fails
when they are absent; ordinary Go/release checks remain Android-SDK independent.
