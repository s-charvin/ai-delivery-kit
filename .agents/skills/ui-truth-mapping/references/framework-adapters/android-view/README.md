# Android View capture adapter

Use for production XML/ViewBinding, Activity, Fragment, RecyclerView, and custom
Views; no Compose. Read the sibling orchestrator skill's
`references/framework-adapters/android-view.md` for feature ownership, MVI,
Flow/lifecycle, design, and device-verification rules.

## Renderer and scope

Reuse a proven project capture stack. Without one, recommend Robolectric Native
Graphics + Roborazzi. Both are community tools, not official Android rendering
test APIs. Here the shared official-stack preview requirement means actual
Android View rendering with the declared community harness; it does not promise
device-equivalent rendering. Record renderer, versions, command, and limitations.

Use production XML, generated binding, resources, theme, and View controls.
Layout Editor/`tools:` data does not prove actual rendering. Configure dimensions,
density, fontScale, locale/RTL, night mode, and insets explicitly. Assert
`wrap_content`, `match_parent`, ConstraintLayout `0dp`, long text, and list bounds
for applicable scenarios. Use genuine, approved assets, never the kit demo's
visuals as business evidence.

- `component-only`: mount a production component in a test container and record
  uncovered host composition.
- `host-static`: an existing runnable entrypoint must mount the production
  Activity/Fragment, its layout, theme, resources, and actual component boundary.
- `host-runtime`: use the production host on an emulator/device, with platform
  preflight and a bounded visual smoke before expensive lifecycle tests.

Resolve all shared host capability checks before capture. A synthetic test Activity
assembling components is not production-host evidence. Capture Dialog and
PopupWindow in their own windows. SurfaceView, WebView, media, GL/Spine, platform
IME, permissions, and real system-back behavior require capability-specific
device coverage; record missing evidence explicitly. Activity recreation does
not prove process-death recovery.

## PNG and animated GIF

Use Roborazzi or the project's established path for PNG. For motion use the
shared [AnimatedViewCapture.kt](AnimatedViewCapture.kt) helper only after its
clock/raster behavior is verified for the target View and harness. The kit
fixture at `tests/fixtures/android-view/` consumes this same source; avoid a
second copy that drifts. Its existence is not proof that a project capture ran.

1. Mount and lay out the real View. Start the production animation by a real
   click or production event; never assign per-frame properties to fake motion.
2. Advance Robolectric's main Looper/Choreographer by cumulative elapsed time.
   Sample at 25 fps (40 ms). Use a View/Bitmap capture path demonstrated not to
   drain the animation queue or jump automatically to its terminal frame.
   The helper first delivers the initial VSync and reports its trigger-to-frame
   offset as `startOffsetMs`. Animation time zero is that first frame; the
   offset is not hidden inside the animation duration. It advances callbacks in
   1 ms steps and captures every 40 ms: large Looper jumps can delay VSync until
   the jump endpoint and corrupt animation origins or chained transitions.
3. Include time zero, intermediate frames, and the exact terminal sample. For
   non-40 ms endpoints append that terminal sample; do not slow the animation to
   fit cadence. Keep terminal review hold separate from animation time.
4. Encode with JDK ImageIO only. Explicitly set GIF delays, disposal and infinite
   loop metadata. Composite transparency against the real background. GIF delay
   precision is 10 ms: declare the rounding policy and measured timeline error.
   No ffmpeg, WebP, MP4, or additional encoder is required.
5. Decode before publishing. Assert frame dimensions/count, changing start and
   middle pixels, expected settled state, total duration including separate
   hold, disposal, and infinite-loop metadata. PNG remains the reference for
   text and color precision; GIF palette quantization is not pixel fidelity.
6. Close ImageIO writers/streams, recycle test bitmaps, stop animations, and
   release host resources on success and failure. Keep intermediate frames in
   ignored/temporary storage and clean in `finally`. Publish only a fully
   validated new output, and invalidate/delete failed output so a previous run's
   GIF cannot masquerade as current evidence. Repeated-run and injected encoder
   failure checks are required for the helper.

Do not remove multi-frame assertions or substitute a device-only workflow when
the reference local GIF path fails. Diagnose the clock, mounting, capture, and
encoder independently and report the actual blocker. For business hosts lacking
a deterministic path, follow the existing explicit motion-decision/deferred
runtime-verification rule; never claim an unavailable preview was captured.

## v3 index and acceptance

Use `stack: "android-view"`. `component_path` is a repository-contained `.kt`,
`.java`, or `.xml` file. `golden_test` is mandatory and points to the actual `.kt`
or `.java` test. Static previews are PNG and motion previews GIF. Preserve the
shared source, coverage, scope, static confirmation, independent motion
confirmation/waiver, and final integration acceptance contracts.

Each Android unit must provide `render_inputs: [{path, sha256}]`: enumerate the
production code, XML, resources, theme, production host when applicable, and
build/configuration files that influence its scenarios. Paths are unique,
repository-relative, contained after symlink resolution, and hash current file
bytes. Include the test and shared helper when they influence rendering. A
component-file hash alone cannot bind resource/theme or build changes.

When any input changes, rerun affected tests and recapture affected previews,
then update input hashes. Retain a static or motion confirmation only if its
preview and approved behavior/motion contract are unchanged. Identical pixels
alone cannot preserve approval after a behavior or motion-contract change.
For host scopes, bind `host_binding` and native test evidence outside
`.ai-delivery/`; a scope label cannot replace real host provenance. Existing
Flutter/Web v3 records require no new fields or schema migration.

## Copyable test entrypoint

Copy `AnimatedViewCapture.kt` into the host's test sources, never production
sources. It requires Robolectric, JUnit and the JDK desktop ImageIO module;
Roborazzi supplies the separate PNG capture. Enable Android resources for local
unit tests. Set `roborazzi.test.record=true` only for explicit preview recording;
normal baseline comparison must not silently overwrite approved images.

Android Kotlin compilation can hide JDK desktop APIs even in local tests.
For the reference Kotlin Gradle plugin, expose them only to JVM unit-test tasks:

```kotlin
tasks.withType<org.jetbrains.kotlin.gradle.tasks.KotlinJvmCompile>().configureEach {
    if (name.contains("UnitTest")) compilerOptions.noJdk.set(false)
}
```

Keep production and instrumented Android compilation unchanged. ImageIO is a
host-JVM test dependency, not an Android runtime API.

```kotlin
@RunWith(RobolectricTestRunner::class)
@Config(sdk = [35], qualifiers = "w360dp-h640dp-mdpi")
@GraphicsMode(GraphicsMode.Mode.NATIVE)
@LooperMode(LooperMode.Mode.PAUSED)
class MotionReviewTest {
    @Test fun review() {
        AnimatedViewCapture.withHost(ActivityScenario.launch(ProductionActivity::class.java)) { scenario ->
            scenario.onActivity { activity ->
                val root = activity.findViewById<View>(android.R.id.content)
                root.captureRoboImage(File("build/outputs/ui-review/initial.png"))
                val result = AnimatedViewCapture.capture(
                    root, File("build/outputs/ui-review/transition.gif"),
                    durationMs = 400, terminalHoldMs = 80,
                    trigger = { activity.findViewById<View>(R.id.trigger).performClick() },
                    onFrame = { elapsed -> /* Assert the real timeline here. */ },
                )
                assertEquals(480, result.durationMs)
            }
        }
    }
}
```

Replace the named production entrypoint and trigger with actual host symbols.
The helper requires an attached, laid-out View with an opaque production
background. Capture the appropriate production ancestor when the child is
transparent. It does not synthesize a background, capture separate windows, or
prove SurfaceView/media output. Scene-specific assertions must prove changing
frames and the actual terminal state; successful encoding alone is insufficient.
Use `withHost` for an isolated test host: close it on success or failure, restore
the clock mode, and deliver at most two already-scheduled VSync frames, each no
later than the configured frame delay. API 35 window teardown calls
`BackProgressAnimator.reset()`: its Spring `skipToEnd` needs a first frame to
establish time and a second to consume the end request. These teardown frames
are outside the GIF timeline. Do not run independent captures concurrently on
the shared main Looper. The production host still owns and
cancels its animators/subscriptions during normal lifecycle teardown; the helper
does not cancel arbitrary application jobs or drain an infinite animation.
Never reset a global animation registry or add arbitrary delays to make a
lifecycle test pass. Additional cleanup must be scoped to resources the host
owns; unexpected pending work requires diagnosis. This test-harness handling
does not establish that real system-back gestures have been verified.

Use the host's exact module/variant test command. In the kit source checkout,
`bash scripts/test-android-view.sh` runs the reference fixture and lint without
an emulator. That script and fixture are not installed into business projects.
