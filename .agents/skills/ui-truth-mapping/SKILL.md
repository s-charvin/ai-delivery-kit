---
name: ui-truth-mapping
description: Use only when the ai-delivery orchestrator has a governed `.ai-delivery` requirement slice in Stage 2, CP-UI is confirmed, and a Figma design must be frozen as a real host-stack component (Flutter first) plus an official-stack preview for acceptance. Use for scoped subtrees, multiple reviewable states, motion/Spine/Lottie/shimmer, mask/alpha compositing, or repairing a prior HTML-contract/full-screen dump. Do not use for a generic Figma implementation request; use the host project's normal UI workflow or `figma-design-to-code` instead.
---

# UI Truth Mapping

Extract structured UI truth from a design source (Figma) and freeze it as **real components in the host project**, plus an official-stack preview the user can open.

**Principle 1 — no second conversion.** Write the widget/component the project already uses. Do not freeze HTML (or any parallel mock) and later translate it into Flutter/React.

**Principle 2 — official preview.** Flutter: golden PNG from `flutter test --update-goldens`. Web: whatever that repo already uses to preview a component. In chat, give the user the **absolute path**. In the delivery index, store **repo-relative** paths only.

This skill does one thing: after CP-UI authorization, use the **same slice worktree** throughout governed Stage 2, locate or create the matching unit in the **project source tree**, freeze visual truth there, show the preview path, and record a v1 pointer/governance index. It does not own pipeline status beyond that index, decide the next stage, or invent a second visual-truth file (YAML/JSON/markdown must not be used as pixels).

## Input

- A requirement-slice (scope, fields, acceptance signals)
- A design source locator (Figma file key + node id, or equivalent)
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

`ui-truth-index.json` is a **pointer**, not a drawing. Use [templates/ui-truth-index-template.json](templates/ui-truth-index-template.json) and persist at least:

| Field | Meaning |
|---|---|
| `schema_version` | Integer `1` |
| `design_source` | Figma file key, root node, revision, capture timestamp |
| `unit_id` / `type` / `stack` | Kebab-case id, `page`/`component`/`modal`/`shared-component`, `flutter`/`web` |
| `source_node` / `dependencies` | Figma source node and unit dependency ids |
| `component_path` / `component_sha256` | Repo-relative real component and current content hash |
| `golden_test` / `golden_test_sha256` | Flutter golden test and current content hash |
| `states[]` | `state_id`, `source_node`, `preview_path`, `preview_sha256`, and confirmation evidence |
| `confirmation` | `confirmed` or `waived`, timestamp/by; waiver requires a note |

Do **not** generate `ui-contract.html`. Do **not** copy `ui-contract-template.html` (removed). Do **not** translate HTML into Flutter.

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

The example teaches `MaterialApp` / `RepaintBoundary` / `matchesGoldenFile` / `--update-goldens`, plus preview rules in comments (PNG canvas ≠ runtime size, one `testWidgets` per state, no system chrome, no in-widget state-switcher). **It is not a widget template.** Widget code must follow adjacent production files. Do not add dependencies the host project does not already use.

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

- Invoke only from a governed Stage 2 slice after CP-UI is recorded. This skill writes production code, golden tests, previews, and the v1 index inside the recorded slice worktree; it is not an implementation-free preflight.
- **Requirement-scoped extract:** In Scope artifacts decide the root — smallest ancestor covering artifacts that belong to **one** unit. Disconnected artifacts → split units. Never dump the full page.
- **Unit Split Plan before evidence:** fill §1b before any `get_code` or component code.
- **Scoped `get_code` only.** The `get_code` target **must equal** the planned `source_node`. Full-page `get_code` then prune is a process failure.
- **Do not invent visual truth.** No units, states, paints, or icons beyond Figma evidence (`get_code` / `get_structure`).
- **Do not invent layout.** Transfer geometry mechanically into the host layout system (Flutter constraints, CSS, etc.). Do not rewrite into a hand-authored semantic page that drops evidence.
- Preview px is an artboard snapshot, not runtime sizing. Classify **fill / hug / fixed** (§5b). Variable copy is hug or fill plus overflow / min / max — never fixed from the sample.
- Never copy TemPad `data-hint-*` into product code or the index.
- A Figma mask / alpha-only gradient is **not a second visible wash**. Run §3b.
- Do not model system UI (status bar, gesture bar, IME, device chrome) as component content — use safe-area handling.
- Do not declare a unit frozen without **explicit per-unit user confirmation** of the preview (absolute path). Skip only when the user waives re-review.
- Do not create a second visual-truth file beside the component (no companion mapping YAML/JSON/markdown used as paint). `ui-truth-index.json` is pointers only.
- Do not scan every historical file in the repo to find a match. Locate via requirement id, route/widget semantics, a known relationship, or an explicit path.
- Do not write an unverified `delivery.implemented.target` (or equivalent) from memory.

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
3. **Assets** — persist Lottie/GIF/video when bytes exist; otherwise `pending-user`, poster frame only — do not invent the file.
4. **Classify** (`content-bound`, `component-variant`, `motion-preset`, `design-animation-asset`, `prototype-transition`).
5. **Map** to states / goldens / placeholders. **User-named reference implementation:** if the user points at existing code, **read it first**; preview mechanics must match that reference (get_code packing must not silently invert growth/reveal).
6. **Consistency check (REQUIRED before writing component code):** same chrome across states/instances must not get uneven motion coverage without explicit evidence. Uneven coverage is an anomaly — stop and ask.
7. **Coverage review after every prune (REQUIRED):** re-read remaining source clauses against remaining targets. Split a multi-clause SECTION note per unit.

Record a **Motion and transitions** table for the user (in their language): State | Where | Effect | Reference. Motion ≠ data binding. Put this in golden/widget comments or the chat freeze packet — not as a second paint file.

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

Also run when names/CSS mention mask / 蒙版 / `mask-image` / blend ≠ src-over, or two fills share bounds, or a gradient only changes alpha.

| Role | Test | Freeze as |
|---|---|---|
| `paint` | Removing it removes visible color/image | Color/image source |
| `mask` | Removing it only changes another layer's alpha/clip | Alpha/clip **of the paint** — **not a second visible wash** |
| `overlay` | Still adds visible color if the other layer is gone | Independent layer |

Default for same-bounds opaque RGB + fading alpha → **one** composited effect. Implement as `Mask` / `dstIn` / `ShaderMask` / `mask-image`, not two stacked fills. Ambiguous tint-vs-mask → stop and ask.

### 4. Write the real component (Flutter first)

**Create:** add the widget next to neighbors. Match their constructor style, theme, spacing helpers, and folder layout. **Do not** copy a Dart template and fill blanks.

**Incremental patch:** open the matched file; do not rewrite unrelated subtrees.

Map evidence into the host layout system:

- Flutter: `Row`/`Column`/`Stack`/`Positioned`/`Expanded`/`Flexible`/`Wrap`/`SizedBox`/`AspectRatio` as the geometry requires. Images: use the project's existing fixture/`ImageProvider` pattern in tests — **golden tests must not hit the network**.
- Web: the same discipline in that repo's components.

Encode review notes (in/out scope, motion table, assets, sizing, compositing) as comments on the widget/golden and in the freeze chat. They are audit copy, not product UI.

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

Then print the PNG **absolute path** to the user. Multiple states → multiple goldens (or the host's existing pattern).

Skeleton comments are binding, not optional color. In particular:

- `setSurfaceSize` is the **PNG canvas** (artboard snapshot), not a runtime width lock. fill / hug / fixed lives in the widget.
- One `testWidgets` per reviewable state. Do **not** bake a state-switcher or review panel into the widget (retired HTML preview chrome).
- Do **not** paint status-bar / home-indicator / IME unless those bars are in-scope product UI. Zero `MediaQuery` padding / `viewPadding`.
- Motion = named **keyframe** PNG. A looping animation inside the golden is wrong. Motion table stays in comments / freeze chat.
- Use the host Theme / localizations / image-fixture / golden harness when neighbors already do.

Web: open/build the component the way that repo already previews (Storybook, a local route, a static file). Print that **absolute path**. Do not add Playwright just for this skill.

**Freeze bar:**

1. Component compiles / the host preview opens.
2. Official preview file exists; chat showed its **absolute path**.
3. The v1 `contracts/ui-truth-index.json` validates repo-relative containment, file types, SHA-256 hashes, dependencies, and one `states[]` entry per reviewable state; each state has confirmation or a reasoned waiver.
4. Scope matches the slice; icons/images are evidence-backed; motion table present when dynamics exist; sizing classified; compositing recorded when §3b fired.
5. Stage 2 tests pass and the latest fresh-context review is clean; record the slice worktree/branch for Stage 4 reuse.
6. If the unit set changed, sweep stale pointers in the requirement directory in the same change.

Do **not** claim freeze from "the widget looks right" without a preview path. Do **not** generate `contract-preview-*.png` as a substitute for the official golden.

### 7. Index and status

Write/update `.ai-delivery/requirements/<req-id>/sub-requirements/<sr-id>/contracts/ui-truth-index.json` from the v1 template. It stores pointers and governance hashes/confirmation metadata, never paint.

Set `acceptance_frozen` only after the freeze bar. On failure → `blocked_verification_failure`.

There is no HTML validator. Kit status validation checks that the index exists and listed relative paths resolve from the **repository root**.

### 8. After implementation (Stage 4 consumers)

Stage 4 **wires** the already-written component (API, route, state, mount) in the same slice worktree. It must not create a second worktree, re-draw Flutter from HTML, or re-query TemPad by default.

**Reference check:** run a reference/usage search before writing any "implemented at" claim. Definition-only is not enough.

### 9. Replace or deprecate — sweep stale pointers in the same change

When a unit is deleted, replaced, or rebuilt under a new id: redirect active pointers (`status.json` notes, visual-acceptance, progress/todo) in the same change. Historical "superseded / deleted / 已删除 / 取代" lines may remain.

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
- Omitting `schema_version`, per-state previews/confirmation, or content hashes; accepting hash drift after freeze.
- Scanning every historical unit to "find" a match; rewriting an entire matched widget for a small requirement.
