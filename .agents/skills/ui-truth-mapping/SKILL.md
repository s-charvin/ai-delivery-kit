---
name: ui-truth-mapping
description: Use when a design source (Figma) needs to be extracted into a canonical YAML UI contract for 1:1 implementation. Auto-detects and splits multiple sections (pages, modals, states) from a single design source.
---

# UI Truth Mapping

Extract structured UI truth from a design source (Figma) and freeze it as a canonical YAML contract. The YAML is the only output — there is no separate mapping document.

A single design source may contain multiple top-level sections: distinct pages, modal overlays, or multiple states of the same page. This skill auto-detects and splits them into independently structured units.

This skill does one thing: reads a requirement-slice + design source → produces one or more YAML UI contracts + a section-map. It does not manage state, decide what runs next, or handle blockers.

## Input

- A requirement-slice document (scope, fields, acceptance signals)
- A design source locator (Figma file key + node id, or equivalent)

## Output

When the design source contains a single page:
```
<output-dir>/
└── ui-acceptance-contract.yaml   # canonical YAML — component tree, layout, spacing, typography, states
```

When the design source contains multiple independent pages or modals, one contract per unit:
```
<output-dir>/
├── <page-or-modal-id>/
│   └── ui-acceptance-contract.yaml
├── <page-or-modal-id>/
│   └── ui-acceptance-contract.yaml
└── section-map.json              # maps each section to its classified unit and page
```

## Templates

Use the provided templates — do not invent fields or structures:

```
templates/
├── ui-acceptance-contract-template.yaml   # YAML contract template
└── section-map-template.json              # section → unit mapping template
```

## Hard Boundary

- Do not invent visual truth — no adding pages, fields, components, or states.
- Do not treat screenshots or node names alone as sufficient evidence. Structured payloads are required.
- Do not use top-level `SECTION` as the final executable node target.
- Do not create a second UI acceptance source beside the YAML.
- Do not accept `children: []` when source evidence shows multiple visible blocks, lanes, or clusters.
- Do not ship empty `font` when visible text exists, or empty `icon`/`image` when visible assets exist.
- Do not include system UI in contracts: status bars, system navigation bars, soft keyboards, device chrome, or OS-level overlays must not appear in the component tree. Use `safe_area` on the affected region to declare system UI overlap instead.
- Do not assign functional roles to empty containers; any UI component needs visible icons, styles, or textual evidence.
- Do not map empty spacer. Containers with no visible child elements, no text, no icons, no images, and no background are only used for layout symmetry design considerations and are captured by `layout`, and are not worth recording.
- Do not generate YAML contracts or `section-map.json` from memory. Locate the corresponding template file under `templates/`, copy it verbatim to the output path, then fill in values field by field. Preserve all field keys, ordering, YAML comments, and structure. Only change values — never add, remove, or rename fields. Every populated value must be source-backed; leave template defaults (`null`, `{}`, `[]`) unchanged when no evidence exists.
- Do not generate contracts for multiple units in the main session's context. For each independent unit (page, modal, shared-shell) identified in the section-map, spawn a separate subagent that gathers evidence and freezes the YAML for that unit alone. Only exception: skip subagent dispatch when the user explicitly requests no subagent usage, or when there is exactly one unit with ≤2 state frames — those are simple enough for inline handling without quality loss.
- Do not ship empty or partial `padding` on any component. Every component must declare explicit padding values for all 4 directions (`top`, `right`, `bottom`, `left`). Use `0` where the design shows no visual spacing — silence is ambiguity, not evidence.
- Prefer `auto` width/height over fixed px values. Layout spacing between siblings uses `margin` or `padding` on the parent container, not fixed dimensions on children. Reserve fixed px for intentionally sized elements: icons, avatars, explicit button sizes, and baseline-anchoring rows only.
- When a component must use a fixed `width` or `height` px value, document the reason in the component's `description` field so reviewers understand why `auto` was not applicable.
- Do not ship empty or partial `anchor` on any component. Every component must declare all 4 anchor directions (`start`, `end`, `top`, `bottom`), each with explicit `to`, `direction`, and `offset`. Use `offset: 0px` when flush to the reference edge. Use `offset: auto` when the parent layout (e.g. a list with multiple items) controls positioning — when `auto`, document how the offset is calculated in the anchor entry's `note` field.

## Workflow

### 1. Confirm upstream
Read the requirement-slice to understand what UI elements are needed before touching design data.

### 2. Analyze sections and split

**CRITICAL — Enumerate ALL frames first:** Do NOT query individual nodes in isolation. Query the design source at the **parent/selection level** (not a specific node) to get the complete list of top-level sibling frames. Record every frame's id, name, type, and position before doing anything else. Skipping this step causes entire state variants to be missed.

**After full enumeration**, classify every frame:

**Classification:**
| Classification | Meaning | Action |
|---|---|---|
| `page` | A full-screen page or screen route | Structure as an independent page-level contract |
| `page-state` | An alternative state of an already-classified `page` (e.g. loading, empty, error, selected, unselected) | Group under the parent `page` as a screen state — do NOT create a separate contract |
| `modal` | A modal dialog, bottom sheet, popover, or overlay | Structure as an independent page-level contract — do NOT nest inside a page |
| `shared-shell` | A shared navigation shell, tab bar, or persistent frame that wraps pages | Extract once as a shared component; reference it from dependent pages |
| `ignore` | Non-UI content (designer notes, annotations, guide lines) | Exclude from contracts entirely |

**Grouping rules:**
- Frames with the same name prefix but different suffixes (e.g. "性别-未选择", "性别-男", "性别-女") → `page-state` variants under one `page`. These share the same shell/layout and differ only by content state.
- Sections that share the same shell/layout and differ only by content state → group as `page-state` variants under one `page`.
- Sections with distinct layouts, different navigation context, or independent entry points → split as separate `page` units.
- Modal overlays, sheets, and dialogs → always split as independent units. They have their own lifecycle, entry trigger, and dismissal — they are not child components of a page.
- When in doubt between `page` and `page-state`: check if the sections would be reached via the same route/URL. Same route → `page-state`. Different route or triggered by a user action → `page`.

**Verification:** After classification, confirm every enumerated frame has been assigned to a unit. No frame left unclassified. If a frame doesn't fit, re-examine — it may be a state variant you overlooked.

**Output:** Copy `templates/section-map-template.json` to the output path, then fill in values for each classified frame. Preserve all field keys, ordering, and structure exactly as the template defines them — never regenerate from memory.

**After section-map is written — dispatch per-unit subagents.** For each independent unit (page, modal, shared-shell) in the section-map, spawn a subagent. Each subagent receives only its unit's frames (with source_node ids), the requirement-slice, the design source locator, and the template path. It independently executes Steps 3+4 for its assigned unit — gathering evidence only for its frames, then freezing one YAML contract. Dispatch all units in parallel. The main session does not gather evidence or freeze YAML; it only dispatches, collects results, then runs Step 5 review.

Skip subagent dispatch only when the user explicitly requested no subagent usage, or when there is exactly one unit with ≤2 state frames.

### 3. Gather design evidence *(runs inside per-unit subagent)*
- Check cache first if available.
- Use structured design data from the provider (structure-level query first, then drill to code-level evidence per frame).
- **Every state frame must have evidence.** A page classified with N state frames in step 2 must produce N screen_state entries, each backed by structured evidence from its source_node. Do not map only the simplest/idle state and skip the rest.
- **Ignore system UI:** status bars, system navigation bars, soft keyboards, device chrome, and OS-level overlays are not part of the application UI. Exclude them from evidence and contracts. Only map the application-controlled viewport.
- **Distinguish fill vs fixed width:** A pixel value that equals (frame_width − symmetrical_horizontal_margins) is a design-tool snapshot, not layout intent. Use `fill` when an element spans the full width with consistent margins; reserve fixed px for intentionally sized elements (icons, avatars, fixed buttons).
- **Calculate offsets from anchor bottom:** Region offset = child's top-y − (anchor's top-y + anchor's height). The offset is the gap between the bottom edge of the anchor and the top edge of the child — not the distance between their top edges.

### 4. Freeze YAML contract *(runs inside per-unit subagent)*

This step runs inside each per-unit subagent. The subagent has access only to its assigned unit's frames and evidence — no cross-contamination from other units.

**First, copy the template.** Locate `templates/ui-acceptance-contract-template.yaml` and copy it verbatim to the output path for this unit. Never regenerate the structure from memory — the template's field keys, ordering, YAML comments, and default values are the source of truth.

**Then fill in values** from design evidence. Only change template values — never add, remove, or rename fields. Leave defaults (`null`, `{}`, `[]`) where no evidence exists.

Produce one `ui-acceptance-contract.yaml` per independent unit (each `page` or `modal` classification from step 2).

This is a single page with a single component tree. States toggle component visibility and style — they do NOT duplicate the tree.

**States** — top-level declaration of which visual states this page can be in. A page with N state frames from step 2 produces N `states` entries:
- Each state has an `id` and a `source_node` pointing to its specific design frame. Nothing else — no duplicated regions.
- Common state ids: `idle` (default), plus domain-specific states like `male-selected`, `female-selected`, `filled`, `empty`, `loading`, `error`.
- Every state frame enumerated in step 2 must appear here.

**`background`** — page-level fill color/image (extracted from the idle/default frame unless evidence shows it changes per state).

**Regions** — single shared component tree for the entire page. Components from ALL state frames are merged into this one tree:
- `id`, `name` (human-readable), `source_node` (from the default/idle frame where this component exists; for state-specific additions, use the frame where it first appears)
- `safe_area`: `"top"` | `"bottom"` — declare when system UI overlaps this region's edge; omit if not applicable
- `anchor`: list of 4 attachment entries, one per direction (`start`, `end`, `top`, `bottom`). All 4 must be present. Each entry has `to` (reference component or page edge), `direction`, `offset` (explicit `<Npx>` gap from the reference edge, or `auto` when parent layout controls the position), and `note` (required when `offset` is `auto` — explain how the value is calculated). Anchors replace `margin` — spacing from a reference edge is expressed as `offset`, not as `margin` on the component.
- `layout`: direction, alignment, gap between children
- `box`: width (auto/fill/<Npx>), height (auto/<Npx>), padding (all 4 sides required). Layout spacing is expressed through `anchor.offset`, not `margin`.
- `background`: color, image
- `children`: recursive component list

**State handling across the single tree:**

Components handle state differences using two fields:
- `visible_when`: condition under which this component is rendered. Use semantic conditions (`"gender is selected"`, `"input is not empty"`), not mechanical state-ID checks. `null` means always visible.
- `states`: per-state style diffs for this component, keyed by semantic component state (`selected`, `active`, `disabled`, etc.), each value a diff from the component's default properties. The page-state transition logic maps page states to these component states. Example: when page is `male-selected` → `btn-male` goes to `selected` state (blue border), `btn-next-step` goes to `active` state (blue bg).

**Merging components from multiple frames:**
- Components present in all states → use the idle/default frame's `source_node`, specify no `visible_when`.
- Components present only in some states → use the `source_node` from a frame where they ARE visible, set `visible_when` to the semantic condition that causes them to appear.
- Components that differ only in style between states → one component entry with default = idle style, `states` = the diffs for non-default states.
- Never create two component entries with the same `id` for different states.

**Components** — recursive, same shape at every level:
- `id`, `type` (text|icon|image|button|input|list|container|custom), `name`, `source_node`
- `visible_when`: condition for conditional visibility. Use semantic conditions. `null` = always visible.
- `description`: implementation hint
- `layout`: direction, align, gap
- `box`: width (auto/fill/<Npx>), height (auto/<Npx>), padding (all 4 sides required; 0 where no visual gap). Layout spacing is expressed through `anchor.offset`, not `margin`.
- `background`: color, border (radius/width/color), shadow, opacity
- Content — exactly one slot populated:
  - `text` + `font` (family, size, weight, color, height, align)
  - `icon` (src, size)
  - `image` (src, width, height, fit)
- `interaction`: on (click/long-press), action, note
- `states`: per-state diffs from default. Component-state keys (e.g. `selected`, `active`, `disabled`), each a partial component diff. Example: `{ selected: { background: { border: { color: "#41B8F4" } } } }`
- `children`: recursive

**Rules:**
- Never invent values. Leave fields null when source provides no evidence.
- `children: []` only valid for leaf nodes with no visible children.
- `states` records only the diff from default (the component's top-level properties are the default state).
- `visible_when` uses semantic conditions, not state IDs. Prefer `"gender is selected"` over `"state == 'male-selected' or state == 'female-selected'"`.
- `width: fill` for elements that span their parent's full width (including descendants inside a fill parent). Fixed px only for intentionally sized elements (icons, avatars, fixed buttons) — when used, document the reason in `description`. The design tool's pixel value is a frame-size snapshot, not layout intent. Judge by visual context: is this element meant to span the available space, or is it intentionally fixed?
- **Font align uses `start`/`end`** (not `left`/`right`) for RTL compatibility. `layout.align` already follows this convention.
- **Text with `font.size` uses `height: auto`.** Fixed heights on text elements conflict with font rendering across platforms. Containers (buttons, cards, inputs) that wrap text may keep fixed heights for touch targets or layout.
- **Keyboard-aware regions use `safe_area: "bottom"` with `offset: "0px"`.** When a design frame includes a system keyboard and a region sits directly above it, the region's pixel position is a design-tool snapshot — it will move with the keyboard at runtime. Anchor it to `bottom`; the system handles keyboard avoidance. Do NOT calculate an offset from the frame bottom.

### 5. Final Contract Review

**Mandatory — run after every YAML freeze.** Review EVERY contract produced (page, page-state, modal, shared-shell). Do not skip any unit. Use a subagent for clean isolation — the subagent receives all contracts plus `section-map.json` and returns optimized contracts.

This review normalizes layout semantics and sizing only. It does NOT add or remove source-backed components, states, `visible_when` conditions, or `source_node` values.

**Review order (follow strictly):**

**A. Safe areas & system UI**
- A region whose top edge sits under the system status bar → `safe_area: "top"`.
- A region sitting above the system navigation bar, home indicator, or soft keyboard → `safe_area: "bottom"`, anchor to `bottom` with `offset: "0px"`.
- Never model status bars, navigation bars, keyboards, or device chrome as components in the tree.

**B. Keyboard adaptation**
- Pages with text inputs, codes, passwords, or email fields → the region containing the input area must anchor to `bottom` with `safe_area: "bottom"`. The system handles keyboard avoidance at runtime.
- Do not use fixed pixel offsets to simulate keyboard-pushed positions. Do not model the keyboard as a component or fixed-height spacer.

**C. Width/height convergence — hardcoded px → auto / fill**
- Text, labels, descriptions, value displays → `width: "auto"`, `height: "auto"`.
- Cards, rows, list containers spanning available width → `width: "fill"`.
- **fill detection rule**: if a component's px width equals (parent_width − symmetrical horizontal padding), it is a design-snapshot value — use `fill`, not a fixed px.
- Fixed px kept only for: icon sizes, avatar sizes, minimum touch targets (≥44px), modal widths with explicit design intent, and visually intentional fixed baselines.
- **Fixed-value justification**: every component that retains a fixed `width` or `height` px value must have a `description` that explains why `auto` was not applicable (e.g. "icon baseline size", "touch target minimum", "image intrinsic dimension").

**D. Fixed-value preservation**
- Keep fixed sizes for: icons, avatars, explicit button/touch heights, modal width baselines, and row heights that anchor visual rhythm.
- Do not force `auto` where the design clearly requires a fixed dimension for visual stability.

**E. Component tree constraints**
- Do not add pages, components, states, or copy absent from the design source.
- Do not delete source-backed components for layout convenience.
- Do not alter `source_node`, state `id`, or `visible_when` conditions.

**F. Padding completeness**
- Audit every component's `padding`. All 4 directions (`top`, `right`, `bottom`, `left`) must have explicit values.
- Use `0` where design shows flush edges — never leave a padding field `null` or omitted.
- Containers with visible children at a consistent inset → padding reflects that inset on the container, not fixed dimensions on children.

**G. Anchor completeness**
- Audit every component's `anchor`. All 4 directions (`start`, `end`, `top`, `bottom`) must be present — no missing entries.
- Each entry must have explicit `to`, `direction`, and `offset` — no nulls, no empty strings.
- `offset: "0px"` for flush attachment to the reference edge.
- `offset: "auto"` when the parent layout controls positioning (e.g. list item spacing, flex distribution). Every `auto` offset must include a `note` explaining how the value is calculated.
- Components below a sibling → anchor `top` to that sibling's `bottom` with the measured gap as `offset`.

**Output**: overwrite each `ui-acceptance-contract.yaml` with the optimized version. Update `section-map.json` only if unit classification changes. If a fixed value is source-justified, keep it. If `auto`/`fill` is semantically correct, apply it. Surface any ambiguous case in the subagent's response.

## Component Type Vocabulary

`container`, `card`, `list`, `list-item`, `form`, `text`, `text-input`, `button`, `image`, `icon`, `tab`, `navigation`, `divider`, `badge`, `modal`, `sheet`, `toast`, `custom`
