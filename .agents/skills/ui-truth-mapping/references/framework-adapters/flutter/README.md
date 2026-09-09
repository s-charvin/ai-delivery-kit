# Flutter Adapter Reference

This directory is the Flutter implementation reference for the framework-neutral
UI Truth Mapping contract. It is not the default workflow and it is not a
production widget template. Use it only when the host project is Flutter and
the existing project test/asset conventions support the examples.

## Static capture

`golden-preview-test.dart.example` shows the official `flutter_test` pattern:
mount the real widget, configure one deterministic visual scenario, use a
`RepaintBoundary` and `matchesGoldenFile`, and update goldens with the host's
normal test command. The example's canvas and profile are evidence settings,
not runtime layout constants.

## Motion capture

`motion-preview-test.dart.example` shows the host-supported motion path:

- trigger the real widget behavior;
- advance cumulative fake time at the declared cadence;
- write each frame through `matchesGoldenFile` into a temporary/ignored frame
  directory;
- encode a duration-preserving GIF with the existing concat/VFR path;
- decode and verify frame count, total duration, terminal/cycle state, and
  automatic looping;
- remove frames, manifests, and encoder scratch files in `finally`, including
  failure paths.

The examples deliberately use Flutter APIs such as `testWidgets`, `pump`, and
`matchesGoldenFile`. Those APIs are adapter details, not core skill
requirements. Another framework may use a different official renderer, clock,
capture API, and encoder while producing the same governed evidence fields.
