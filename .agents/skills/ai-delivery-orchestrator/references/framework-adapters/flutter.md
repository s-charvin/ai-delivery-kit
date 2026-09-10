# Flutter Stage 4 Adapter

Use this adapter only when the host project is Flutter and its existing test
stack supports the relevant capture mode. It implements the framework-neutral
evidence-scope contract; it does not expand a scenario's frozen scope.

## Capability mapping

- `component-only`: mount the real production widget in the project's existing
  widget golden harness. The preview may use `RepaintBoundary`, but the widget
  under test must remain the production component. Assert behavior separately.
- `host-static`: use an existing page/widget test entrypoint that mounts the
  production page or sheet. Drive production interactions to the target state,
  then use the project's official golden or viewport capture path.
- `host-runtime`: use an integration-test entrypoint on a supported physical
  device when native views, media decoders, plugins, or runtime resources are
  required. Capture the production host after entering through production
  navigation and interactions.

A `Widget` tree that manually places several production components in a new
`Column`, `Stack`, or test-only page is not a production host. It can prove
component behavior only and must be classified `component-only`.

## Deterministic static capture

1. Reuse the project's existing binding, dependency injection, localization,
   theme, screen-size, and image fixture setup.
2. Mount the real production host when the scope is `host-static`; do not copy
   its child layout into the test.
3. Prepare deterministic application state through existing controller,
   repository, route, or test dependency boundaries.
4. Wait for image metadata, decode, and the first painted frame before capture.
   Use bounded pumps or an explicit readiness signal; do not use unbounded
   settling around continuously active media.
5. Capture the indexed boundary through the existing `RepaintBoundary` or
   project viewport screenshot facility.
6. Add geometry assertions for required landmarks and spatial constraints.
   Resolve actual rendered rectangles through finders/render objects; verify
   visibility, containment, edge insets, relative position, spacing, and
   hug/fill/fixed behavior before producing the image.
7. Write a machine-readable assertion report beside the screenshot in the
   indexed native test evidence directory. Both files stay outside
   `.ai-delivery/`.

## Device and media preflight

Before a `host-runtime` run, perform a cheap preflight and stop before compiling
or launching an expensive lifecycle suite when any required condition fails:

- exactly the intended physical device is connected and authorized;
- battery level is sufficient for the expected run, or the device is charging;
- required media/storage permissions are granted or deterministically handled;
- the target platform and ABI support every native plugin under test;
- deterministic media exists and is readable through the production boundary;
- screenshot output and assertion-report directories are writable;
- the selected test can launch and reach its first production route.

Do not default to a simulator when the scenario requires a physical device.
Do not repeatedly run a full integration suite while device, media, or capture
preconditions remain unresolved.

## Visual smoke before native lifecycle

Split runtime verification into two commands or filtered phases:

1. `visual smoke`: launch, enter the production host, prepare one deterministic
   item, verify required controls are visible, run geometry assertions, capture
   one screenshot, and verify the file is non-empty and reviewable.
2. `native lifecycle`: only after smoke passes, exercise start, release/stop,
   completion, disable interruption, page-change interruption, route-exit
   interruption, and native resource disposal as applicable.

For `xc_video_player` or another native media player, observe lifecycle through
the production controller/plugin boundary. A mocked controller can prove Dart
state projection but cannot prove native playback or resource release.

## Live-media evidence boundary

Flutter UI projection may accept a real `AssetEntity` whose test media source
deterministically marks the item as Live. That proves the UI capability: badge,
toggle, routing, and player state projection. It does not prove that the Android
media stack can classify an iOS Live Photo pair.

Record native classification as platform-uncovered unless it is exercised on
the owning platform with real paired media and the production classifier. An
Android device may validate the visible projection and generic image/video
playback, but must never be cited as proof of iOS Live Photo recognition.

## Evidence output

For host scopes, `runtime-capture` points to:

- the screenshot under the indexed project-native test evidence root;
- the exact widget/integration test source and its SHA-256;
- the geometry assertion report and its SHA-256;
- the exact command and physical device id when applicable;
- production host path, entrypoint, and capture boundary matching
  `host_binding`;
- all required landmarks and spatial-constraint ids verified by the report;
- reviewer identity, timestamp, and `reviewed_capture_sha256`.

Never copy runtime screenshots into `.ai-delivery/`. Governance artifacts keep
only repo-relative pointers and hashes.
