---
name: ui-truth-mapping
description: Use only when the ai-delivery orchestrator has a governed `.ai-delivery` requirement slice in Stage 2, CP-UI is confirmed, and a Figma or runtime-baseline UI truth source must be frozen as a real host-stack component (Flutter first) plus an official-stack preview for acceptance. Use for scoped subtrees, multiple reviewable states, motion/Spine/Lottie/shimmer, mask/alpha compositing, or repairing a prior HTML-contract/full-screen dump. Do not use for a generic Figma implementation request; use the host project's normal UI workflow or `figma-design-to-code` instead.
---

# UI Truth Mapping

Extract structured UI truth from Figma or an approved runtime baseline and freeze it as **real components in the host project**, plus an official-stack preview the user can open.

The orchestrator selects `ui_truth_mode=figma` when Figma supplies visual evidence, or `ui_truth_mode=runtime-baseline` when the requirement, project, or explicit user decision supplies the baseline without stable Figma. This skill never presents a runtime baseline as 1:1 Figma truth.

**Principle 1 — no second conversion.** Write the widget/component the project already uses. Do not freeze HTML (or any parallel mock) and later translate it into Flutter/React.

**Principle 2 — official preview.** Flutter: golden PNG from `flutter test --update-goldens`. Web: whatever that repo already uses to preview a component. In chat, give the user the **absolute path**. In the delivery index, store **repo-relative** paths only.

**Principle 3 — separate visible design truth from runtime truth.** Figma owns only the pixels and transitions it actually evidences. Requirements own product behavior; established project rules own implementation conventions; explicit user decisions close material gaps. A runtime state that Figma does not show is never called "1:1 to Figma". Never silently let a runtime convention overwrite evidenced Figma pixels.

This skill does one thing: after CP-UI authorization, use the **same slice worktree** throughout governed Stage 2, locate or create the matching unit in the **project source tree**, freeze visual truth and approved runtime coverage there, show each visual scenario preview path, and record a v2 pointer/governance index. It does not own pipeline status beyond that index, decide the next stage, or invent a second visual-truth file (YAML/JSON/markdown must not be used as pixels).

## Input

- A requirement-slice (scope, fields, acceptance signals)
- A truth source locator: Figma file key + node id for `figma`, or a requirement/project/user-decision reference for `runtime-baseline`
- For follow-ups: any hint of the target unit (path, widget name, or "no known unit yet")

## Output

Per independent unit, **production code** in the host tree + an official preview file + one pointer row in the sub-requirement index.

```
<host project>
├── lib/…/<unit>.dart          # Flutter: real widget (follow neighbors)
├── test/…/<unit>_golden_test.dart
└── test/goldens/<unit>.png    # review medium

.ai-delivery/requirements/<req-id>/sub-requirements/<sr-id>/contracts/
└── ui-truth-index.json        # pointers only — not paint
```

Write review notes, freeze packets, and necessary production/test code comments in the user's current conversation language. Preserve code symbols, test APIs, machine-readable keys and enum values, IDs, paths, commands, and literal protocol tokens exactly. Product UI copy still follows the product's localization requirements.

`ui-truth-index.json` is a **pointer and coverage ledger**, not a drawing. Use [templates/ui-truth-index-template.json](templates/ui-truth-index-template.json), preserve its machine structure, and write human-readable `confirmation.note` and `coverage[].note` values in the user's current conversation language. Persist at least:

| Field | Meaning |
|---|---|
| `schema_version` | Integer `2` |
| `ui_truth_mode` | `figma` or `runtime-baseline`; must match the sub-requirement status |
| `design_source` | Figma file key/root node/revision for `figma`, or evidence origin/source reference for `runtime-baseline`, plus capture timestamp |
| `unit_id` / `type` / `stack` | Kebab-case id, `page`/`component`/`modal`/`shared-component`, `flutter`/`web` |
| `source_node` / `dependencies` | Figma source node and unit dependency ids |
| `component_path` / `component_sha256` | Repo-relative real component and current content hash |
| `golden_test` / `golden_test_sha256` | Flutter golden test and current content hash |
| `profiles[]` | Test surface, size, orientation, theme, locale, text scale, reduced motion, and input mode |
| `states[]` | `state_id`, `evidence_origin`, `source_ref`; Figma-origin states also require `source_node` |
| `scenarios[]` | State + profile + coverage dimensions + review mode + source; visual scenarios point to a deterministic preview |
| `coverage[]` | Exactly one applicability row for every required runtime dimension |
| `confirmation` | `confirmed` or `waived`, timestamp/by; visual confirmation binds `reviewed_preview_sha256` |

Do **not** generate `ui-contract.html`. Do **not** copy `ui-contract-template.html` (removed). Do **not** translate HTML into Flutter. Runtime-baseline evidence must use only `requirement`, `project`, or `user-decision` origins; never fabricate Figma metadata.

## Stack

Judge from the repo. Do not run a heavy probe.

- Looks like Flutter (Dart widgets, `pubspec.yaml` with a Flutter SDK, existing `test/` goldens) → **Flutter**. This skill is written for that path.
- Looks like a web app (existing page/component tree in that repo's stack) → **Web**. Follow **that** architecture (React/Vue/Svelte/plain HTML — whatever neighbors use). Do not assume "the contract is HTML".
- Unsure → **stop and ask**. Do not default to an HTML contract.

## Template (Flutter golden skeleton only)

```
templates/
├── flutter-golden-preview-test.dart.example
└── ui-truth-index-template.json
```

The example teaches `MaterialApp` / `RepaintBoundary` / `matchesGoldenFile` / `--update-goldens`, plus preview rules in comments (PNG canvas ≠ runtime size, one `testWidgets` per visual scenario, no system chrome, no in-widget state-switcher). **It is not a widget template.** Do not copy its instructional comments into project code; rewrite only necessary comments in the user's current conversation language. Widget code must follow adjacent production files. Do not add dependencies the host project does not already use.

## Quick Reference — Scenario → Unit split

Do not map the entire Figma evidence by default. Match the **requirement size** first:

| Real scenario | Unit(s) to freeze | `get_code` / root | States | Do NOT |
|---|---|---|---|---|
| New full route (page itself In Scope) | `page` (+ shared shell only if the shell is newly accepted) | Page content frame (exclude already-owned shell) | Page-level variants | Dump a persistent tab/nav that already has a unit |
| Tiny badge / red-dot / one control on existing shell | **Patch** the existing widget if its root contains the artifact; else **create** `component` rooted at the badge | Minimal ancestor of the badge/control | Usually none | Create a whole-page widget just to carry the badge |
| Disconnected In Scope artifacts | One `component` / `modal` **per cluster** | Each cluster's local minimal ancestor | Per-unit as needed | One page whose root is the full screen "to cover both" |
| Bottom sheet / dialog / popover | `modal` alone; trigger patched into the trigger's container widget | Sheet/dialog frame | All sheet frames as named states / goldens | Nest the sheet as a page state; put the trigger inside the modal widget |
| Multi-state list/form/module | One `component` (or `page` if the route is the scope) | Scoped module root | Every visual frame → one golden (or the host's multi-golden style) | Separate widgets per state of the same unit |
| Element property only (`disabled` / `selected`) | Patch that node in its existing unit | Unchanged | Do **not** add a unit-level state | Spawn `disabled` as a full-unit golden |
| Component with **variant properties** or **motion** | Same unit; record motion in comments / review notes on the golden | Component/instance root | Static **keyframe** golden; motion spec in notes | Treat motion as a static PNG only and omit the motion table |
| Same-bounds **color gradient + alpha gradient** / Figma mask | Same unit; run **§3b** before treating siblings as paint | The composited paint root | One composited effect | Two `src-over` overlay fills |

## Hard Boundary

- Invoke only from a governed Stage 2 slice after CP-UI is recorded for `ui_truth_mode=figma` or `runtime-baseline`. This skill writes production code, golden tests, previews, and the v2 index inside the recorded slice worktree; it is not an implementation-free preflight.
- **Requirement-scoped extract:** In Scope artifacts decide the root — smallest ancestor covering artifacts that belong to **one** unit. Disconnected artifacts → split units. Never dump the full page.
- **Unit Split Plan before evidence:** fill §1b before any `get_code` or component code.
- **Scoped `get_code` only.** The `get_code` target **must equal** the planned `source_node`. Full-page `get_code` then prune is a process failure.
- **Do not invent visual truth.** No Figma-origin unit, state, paint, icon, or transition beyond Figma evidence (`get_code` / `get_structure`). Missing runtime behavior may come only from requirement, project, or explicit user-decision evidence and must be labeled accordingly.
- **Do not invent layout.** Transfer geometry mechanically into the host layout system (Flutter constraints, CSS, etc.). Do not rewrite into a hand-authored semantic page that drops evidence.
- Preview px is an artboard snapshot, not runtime sizing. Classify **fill / hug / fixed** (§5b). Variable copy is hug or fill plus overflow / min / max — never fixed from the sample.
- Never copy TemPad `data-hint-*` into product code or the index.
- A Figma mask / alpha-only gradient is **not a second visible wash**. Run §3b.
- Do not model system UI (status bar, gesture bar, IME, device chrome) as component content — use safe-area handling.
- Do not declare a unit frozen without **explicit confirmation for every visual scenario** after showing its preview absolute path. Skip only when the user waives that exact scenario review.
- Do not create a second visual-truth file beside the component (no companion mapping YAML/JSON/markdown used as paint). `ui-truth-index.json` is pointers only.
- Do not scan every historical file in the repo to find a match. Locate via requirement id, route/widget semantics, a known relationship, or an explicit path.
- Do not write an unverified `delivery.implemented.target` (or equivalent) from memory.
- Do not freeze while any applicable runtime dimension is unresolved. `covered` and reasoned `not_applicable` are the only legal coverage statuses.
- Do not silently fix a visible accessibility, platform, or performance conflict by changing evidenced Figma pixels. Preserve non-visual improvements where possible; otherwise stop for an explicit design/user decision.

## Locate

Run an **implementation lookup** before create vs patch: does a matching widget/component already exist for this unit?

- Prefer an explicit path the user or slice already names.
- **Route by the in-scope artifact's physical Figma container**, not by the requirement's owning route. A badge on a shared tab bar is patched into that bar's widget.
- Exactly one match → Decide. Zero → create. More than one plausible match → STOP and ask.

## Decide: create vs incremental patch

| Situation | Action |
|---|---|
| No existing unit matches | **Create** next to neighboring production files. |
| Exactly one match and the change fits | **Incremental patch.** Edit only the affected subtree / states. |
| Boundary / route / shared dependency changes fundamentally | **Rebuild** that unit; keep the id stable if it is conceptually the same. |
| Match is ambiguous | **Block.** Ask. |

**Rebuild/split metadata rule:** inherited "already implemented" claims must be **re-verified against current code** (definition + reference/usage search) or dropped.

## Workflow

### 1. Confirm upstream, scope inventory, and locate

Build a short **scope inventory** from the slice (must-freeze / context-only / ignored). Then Locate. Record create / patch / rebuild **before** querying TemPad.

### 1b. Unit Split Plan (REQUIRED before any `get_code` or component code)

Publish this table in chat (do **not** write a companion mapping file):

```
| artifact (node id + label) | unit id | type (page\|component\|modal\|shared-component) | action (create\|patch\|rebuild) | source_node | states | dynamics | get_code target (= source_node) |
```

Enumerate frames to classify — not to freeze. Skipping the §1b Unit Split Plan is a process failure.

### 2. Enumerate frames to classify — not to freeze

Classify each frame: `page` / `component` / `*-state` / `modal` / `shared-component` / `context` / `ignore` / `dynamics-hint`.

**Grouping:** local In Scope → prefer `component`/`modal`. Disconnected artifacts → multiple units. Same shell, different content → states of one unit. Modals always their own unit; the trigger lives in the trigger's container.

### 2c. Dynamics & motion scan (REQUIRED per unit, after §2)

0. **Text-hint sweep** — TEXT / sticky / callout in the scoped subtree **and** parent SECTION siblings. Keywords: motion, animation, transition, typewriter, shimmer, Lottie, GIF, skeleton, placeholder, API-returned, pulse, loading (and the designer's language equivalents).
1. **Candidate sweep** on `source_node` (INSTANCE/COMPONENT, image fills, motion-named layers).
2. **Motion probe** when available (`get_node_motion` / equivalent). Text hints still count if tools are missing.
3. **Assets** — persist Lottie/GIF/video when bytes exist; otherwise `pending-user`, poster frame only — do not invent the file. Record trigger, playback/loop policy, interruption behavior, off-screen policy, and reduced-motion fallback.
4. **Classify** (`content-bound`, `component-variant`, `motion-preset`, `design-animation-asset`, `prototype-transition`).
5. **Map** to states / goldens / placeholders. **User-named reference implementation:** if the user points at existing code, **read it first**; preview mechanics must match that reference (get_code packing must not silently invert growth/reveal).
6. **Consistency check (REQUIRED before writing component code):** same chrome across states/instances must not get uneven motion coverage without explicit evidence. Uneven coverage is an anomaly — stop and ask.
7. **Coverage review after every prune (REQUIRED):** re-read remaining source clauses against remaining targets. Split a multi-clause SECTION note per unit.

Record a **Motion and transitions** table for the user (in their language): Scenario | Trigger | From | To/keyframes | Duration | Easing | Delay | Repeat | Interrupt/reverse/cancel | Reduced-motion fallback | Performance strategy | Reference. Motion ≠ data binding. Missing lifecycle evidence is unresolved coverage, not permission to choose a generic animation. Put this in golden/widget comments or the chat freeze packet — not as a second paint file.

### 2d. Missing-resource escalation

`pending-user` assets → stop and ask (file or explicit waiver) before freeze.

**Dispatch:** more than one independent unit → per-unit subagent so evidence stays isolated.

### 3. Gather minimal TemPad evidence

For each planned unit / state, `get_code` the **scoped** `source_node` only. `get_structure` when hierarchy, overlap, or fill vs hug vs fixed is still ambiguous. Resolve every asset: classify (static vs content-bound vs motion) → reuse existing project asset if identical → persist bytes (TemPad URLs are ephemeral) → never hand-draw a "close enough" glyph.

### 3b. Paint compositing / mask scan (REQUIRED after `get_code`)

Overlapping fills in the same box are **not** automatically two drawing layers.

TemPad hints (never copy `data-hint-*` into product code):

| Source | Signal | Meaning |
|---|---|---|
| `get_code` | `data-hint-mask="true"` | This node is the **mask** |
| `get_code` | `data-hint-has-mask="true"` | SVG **already baked** the mask — do not stack another overlay |
| `get_structure` | `"isMask": true` | Same as mask (field omitted when false) |

Also run when names/CSS mention mask / `mask-image` / blend != src-over, or two fills share bounds, or a gradient only changes alpha.

| Role | Test | Freeze as |
|---|---|---|
| `paint` | Removing it removes visible color/image | Color/image source |
| `mask` | Removing it only changes another layer's alpha/clip | Alpha/clip **of the paint** — **not a second visible wash** |
| `overlay` | Still adds visible color if the other layer is gone | Independent layer |

Default for same-bounds opaque RGB + fading alpha → **one** composited effect. Implement as `Mask` / `dstIn` / `ShaderMask` / `mask-image`, not two stacked fills. Ambiguous tint-vs-mask → stop and ask.

### 3c. Runtime Coverage Plan (REQUIRED before component code)

Figma commonly shows one finished sample, while production code must survive real state, environment, content, and input changes. Publish one plan per unit after design evidence is gathered and before component code is written.

Use this source order for every scenario:

1. **Figma** — authoritative only for visible pixels and transitions that are actually evidenced.
2. **Requirement** — authoritative for product behavior and acceptance boundaries.
3. **Project** — established design-system, platform, localization, accessibility, asset, and testing conventions.
4. **User decision** — required when the first three sources do not resolve a material behavior or visible result.

Record each state and scenario with `evidence_origin` (`figma` / `requirement` / `project` / `user-decision`) and a concrete `source_ref`. Figma-origin states also record `source_node`. A conflict between sources is a blocker; do not merge them by guesswork.

For each unit, classify every dimension below as `covered` with scenario ids or `not_applicable` with a reason. Any applicable but unresolved row blocks freeze.

| Dimension | Applicability scan |
|---|---|
| `state` | Initial, loading, refreshing, populated, empty, partial, error, offline, authentication, permission, and disabled states that the data/interaction model can reach |
| `layout` | Minimum/target/maximum constraints, container or viewport breakpoints, orientation, safe areas, fixed/sticky coexistence, overlays, IME, scroll behavior, z-order, clipping, and hit testing |
| `content` | Empty/short/long/multiline/unbroken strings, list counts, large numbers and localized formats, RTL, locale changes, text scaling or browser zoom, wrapping/truncation/expand behavior |
| `interaction` | Idle, hover, focus, pressed, selected, expanded, keyboard, pointer/touch, drag/swipe alternatives, rapid repeat, re-entry, focus trap/return, and disabled behavior |
| `motion` | Trigger, from/to or keyframes, timing, easing, delay, repeat, interruption/reversal/cancel, reduced-motion result, deterministic test keyframe, and repaint/resource lifecycle |
| `assets` | Static vs content-bound vs motion, source/ownership, vector palette/themeability, fit/crop/focal point, aspect ratio, density, loading/error/empty/offline fallback, cache, and semantics |
| `theme` | Figma variable modes, host semantic tokens, supported light/dark/high-contrast modes, contrast, and interaction-state parity |
| `accessibility` | Native semantics, name/role/state/value, reading/focus order, visible focus, screen-reader updates, platform touch targets, non-color cues, WCAG AA on web, and reduced motion/text scaling |
| `platform` | Supported platforms and input modes, system bars/safe areas, back/navigation behavior, IME, pointer vs touch conventions, and platform-specific primitives |
| `performance` | Stable loading layout, list virtualization when applicable, correctly sized images, animation/repaint isolation, controller/resource disposal, off-screen pausing, and project-native budgets |

Create only profiles the product actually supports; do not generate a universal Cartesian matrix. Each profile records `surface.kind` (`viewport` or `container`), test width/height, optional device-pixel ratio, orientation, theme, locale, text scale, reduced-motion preference, and input mode. Profile dimensions configure evidence and tests — they are not runtime size constants.

Each scenario binds one state to one profile and lists the dimensions it proves. Use `review_mode: visual` for pixel review, `behavior` for semantics/interaction/lifecycle checks, or `both`. Visual and `both` scenarios require deterministic previews and explicit confirmation. Behavior scenarios require an approved source and later project-native verification evidence.

Runtime scenarios without Figma frames may use existing project primitives and tokens only when their semantics match. They are approved technical behavior, never "1:1 to Figma". If a visible accessibility or platform correction conflicts with Figma, implement non-visual semantics/hit-area fixes first; otherwise stop for a design/user decision.

### 3d. Asset and rendering plan (REQUIRED when `assets` is covered)

Record for each image, SVG, icon, animation, gradient, blur, shadow, mask, or blend effect: role, evidence/source, persisted delivery path, sizing class, fit/crop/focal point, aspect ratio, density or vector scaling, token/theme behavior, loading/error/offline fallback, cache policy, semantics, and test fixture.

Use the least complex host-native path that preserves the evidence: existing/native primitive → established project dependency → custom painter/shader → pre-rendered asset only for truly static output whose scaling, theme, and accessibility behavior remain correct. Missing fonts, weights, vector semantics, effects, or runtime assets block freeze; do not silently substitute a close-enough implementation.

### 4. Write the real component (Flutter first)

**Create:** add the widget next to neighbors. Match their constructor style, theme, spacing helpers, and folder layout. **Do not** copy a Dart template and fill blanks.

**Incremental patch:** open the matched file; do not rewrite unrelated subtrees.

Map evidence into the host layout system:

- Flutter: `Row`/`Column`/`Stack`/`Positioned`/`Expanded`/`Flexible`/`Wrap`/`SizedBox`/`AspectRatio` as the geometry requires. Images: use the project's existing fixture/`ImageProvider` pattern in tests — **golden tests must not hit the network**.
- Web: the same discipline in that repo's components.

Implement every covered scenario through the component's real API. Prefer native interactive primitives and established project components; preserve semantic role/name/state, keyboard or gesture alternatives, focus order/trap/return, platform touch targets, and screen-reader announcements. Add focused behavior/semantics tests where the host already supports them. Do not add a dependency solely to satisfy this skill.

Figma-origin scenarios preserve evidenced values exactly, including font family/available weight, line metrics, letter spacing, filters, shadows, gradients, blur, masks, blend mode, clip, opacity, and stacking. A missing font/effect or a conflict with the host renderer is a blocker, not permission to approximate. Requirement/project/user-decision scenarios follow their recorded source while reusing the host design system.

Encode review notes (in/out scope, runtime coverage, motion table, assets, sizing, compositing, accessibility) as comments on the widget/golden and in the freeze chat. They are audit copy, not product UI.

State ids: kebab-case ASCII (`^[a-z][a-z0-9-]*$`), usable as golden filenames (`loading`, `empty-state`).

### 5b. Layout sizing classification (REQUIRED after mechanical transfer)

`get_code` px is **preview geometry**. Classify every in-scope box (unit root required; children when different):

| Class | Meaning | Flutter (typical) | Web (typical) |
|---|---|---|---|
| `fill` | stretches to remaining parent space | `Expanded` / tight parent constraints | `width: 100%` / flex-grow — **not** snapshot px |
| `hug` | sizes to content | intrinsic child size, optional clamp | `width: fit-content` / auto |
| `fixed` | designed lock | `SizedBox` / explicit constraint | explicit px only when locked |

**fill detection rule:** use `fill` when ANY of: Figma FILL / stretch constraints; measured px equals **parent width minus symmetrical horizontal inset** (1px tolerance); the node visually spans the remaining content column.

**hug:** text, chips, rows, anything that should follow content (including i18n / server strings longer than the sample).

**fixed only:** icons, avatars, non-content images, min tap targets, explicit locks. Defaulting to `fixed` because get_code printed px is a process failure.

**Variable content:** hug or fill on that axis — never fixed from the snapshot. Record **overflow policy** (`wrap` / `ellipsis` / `clip` / `scroll` / `grow-parent`) plus min/max when the design or requirement locks them. If requirement **and** design are silent → **stop and ask the user**.

Implementation consumes the classification, not snapshot `w×h`. Dumping every snapshot box into layout constants is a process failure. Tests for fill/hug assert constraint behavior, not snapshot equality.

### 6. Official preview (Flutter golden)

Use `templates/flutter-golden-preview-test.dart.example` as a **skeleton** only. Follow host `flutter_test` conventions when they already exist.

```bash
flutter test <golden_test.dart> --update-goldens
```

Then print each visual scenario PNG **absolute path** to the user. Multiple state/profile combinations → multiple goldens (or the host's existing pattern).

Skeleton comments are binding, not optional color. In particular:

- `setSurfaceSize` is the **PNG canvas** (artboard snapshot), not a runtime width lock. fill / hug / fixed lives in the widget.
- One `testWidgets` per reviewable visual scenario. The test configures its recorded profile without turning canvas dimensions into widget locks. Do **not** bake a state-switcher or review panel into the widget (retired HTML preview chrome).
- Do **not** paint status-bar / home-indicator / IME unless those bars are in-scope product UI. Zero `MediaQuery` padding / `viewPadding`.
- Motion = named **keyframe** PNG. A looping animation inside the golden is wrong. Motion table stays in comments / freeze chat.
- Use the host Theme / localizations / image-fixture / golden harness when neighbors already do.

Web: open/build the component the way that repo already previews (Storybook, a local route, a static file). Print that **absolute path**. Do not add Playwright just for this skill.

**Freeze bar:**

1. Component compiles / the host preview opens.
2. Official preview file exists; chat showed its **absolute path**.
3. The v2 `contracts/ui-truth-index.json` validates repo-relative containment, file types, SHA-256 hashes, dependencies, profiles, sourced states, scenarios, and all ten coverage dimensions.
4. Every visual scenario has a deterministic preview plus confirmation/waiver bound to its current `preview_sha256`; behavior scenarios have approved sources and an explicit Stage 4 verification mode.
5. Scope matches the slice; icons/images are evidence-backed; runtime coverage is resolved; motion/asset plans are present when applicable; sizing is classified; compositing is recorded when §3b fired.
6. Stage 2 tests pass and the latest fresh-context review is clean; record the slice worktree/branch for Stage 4 reuse.
7. If the unit set changed, sweep stale pointers in the requirement directory in the same change.

Do **not** claim freeze from "the widget looks right" without a preview path. Do **not** generate `contract-preview-*.png` as a substitute for the official golden.

### 7. Index and status

Write/update `.ai-delivery/requirements/<req-id>/sub-requirements/<sr-id>/contracts/ui-truth-index.json` from the v2 template. It stores pointers, environment profiles, coverage, governance hashes, source provenance, and confirmation metadata, never paint.

For `ui_truth_mode=runtime-baseline`, set `ui_truth_mode` in the index, use a `requirement`, `project`, or `user-decision` `design_source`, and omit Figma-only identifiers. For `ui_truth_mode=figma`, the top-level source must be Figma; runtime gaps may still use the other allowed origins on individual states and scenarios.

Set `acceptance_frozen` only after the freeze bar. On failure → `blocked_verification_failure`.

There is no HTML validator and no v1 compatibility path. Kit status validation checks the complete v2 matrix, confirmation-to-preview hash binding, and that listed relative paths resolve from the **repository root**.

### 8. After implementation (Stage 4 consumers)

Stage 4 **wires** the already-written component (API, route, state, mount) in the same slice worktree. It must not create a second worktree, re-draw Flutter from HTML, or re-query TemPad by default.

Stage 4 verifies every indexed scenario using the recorded profile and project-native tools, then writes structured `visual-acceptance.json`. If component code changes but every rendered preview hash stays identical, update the component hash and keep the bound confirmations. If any preview hash changes, regenerate the preview and obtain fresh confirmation before the index can validate.

**Reference check:** run a reference/usage search before writing any "implemented at" claim. Definition-only is not enough.

### 9. Replace or deprecate — sweep stale pointers in the same change

When a unit is deleted, replaced, or rebuilt under a new id: redirect active pointers (`status.json` notes, visual-acceptance, progress/todo) in the same change. Historical "superseded / deleted / removed / replaced" lines may remain.

## Anti-patterns (process failure)

- Generating `ui-contract.html` or copying any HTML contract template as the freeze medium.
- **Do not translate HTML into Flutter** (or into the host web stack).
- Baking a state-switcher or review panel into the Flutter widget because the old HTML preview had one.
- Writing a companion YAML/JSON/markdown file to hold **paint**.
- Whole-page dump; full-page `get_code` then prune; skipping §1b.
- Collapsing disconnected in-scope artifacts into one page widget.
- Routing a tiny change by the requirement's owning route instead of the artifact's physical container.
- Inventing a brand-new full shell widget solely to host a badge.
- Hand-authoring a semantic layout that drops `get_code` geometry.
- Copying get_code `w-[Npx]` into implementation as a hardcoded width when fill detection says fill.
- Dumping every snapshot box into layout constants.
- Treating snapshot `w×h` as pass/fail for fill/hug.
- Skipping §5b; marking variable copy as fixed; inventing overflow instead of asking.
- Hand-drawing icons; leaving asset shells unresolved; rebuilding a masked SVG from structure and dropping the baked mask.
- Treating a mask / alpha gradient as a second src-over overlay; skipping §3b; copying `data-hint-*`.
- Downloading a Figma **example** image as a frozen asset when the requirement shows server content.
- Skipping §2c; scoping the text-hint sweep only to `source_node`; truncating a multi-clause SECTION note; silently rewriting motion coverage.
- Shipping a motion preview whose mechanics disagree with a user-named reference implementation.
- Hitting the network inside a golden test.
- Adding Flutter/web dependencies the host project does not already use.
- Declaring freeze without an absolute preview path and explicit user confirmation.
- Dispatching this skill before CP-UI, writing production code outside the recorded slice worktree, or creating a second Stage 4 worktree for the same slice.
- Leaving `ui-truth-index.json` paths as absolute filesystem paths (index is repo-relative).
- Omitting `schema_version`, profiles, sourced states, scenario previews/confirmation, coverage, or content hashes; accepting hash drift after freeze.
- Omitting a runtime coverage dimension; using `unresolved` as if it were a legal frozen status; marking an applicable case `not_applicable` without a reason.
- Calling a requirement/project/user-decision runtime state "1:1 to Figma"; assigning `figma` origin without a source node.
- Reusing a confirmation after its `reviewed_preview_sha256` no longer matches the scenario preview.
- Treating one artboard as proof of all container sizes, orientations, themes, locales, text scales, input modes, or reduced-motion behavior.
- Silently changing evidenced pixels to repair accessibility/platform conflicts instead of escalating the visible conflict.
- Recording only animation keyframes while omitting trigger, interruption, reduced-motion, or resource/performance behavior.
- Recording a content image without loading/error/offline, crop/focal point, density/scaling, cache, fixture, and semantics decisions when those cases apply.
- Scanning every historical unit to "find" a match; rewriting an entire matched widget for a small requirement.
