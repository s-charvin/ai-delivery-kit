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
- Within a per-unit subagent, process frames ONE AT A TIME — never batch all frames into a single Figma query. Each pass iterates frame by frame: query one frame, fill its fields, move to the next. This keeps context focused and prevents missed details.
- Each of the three passes fills ONLY its assigned fields. Never touch fields owned by a different pass. Pass 1 owns id/type/name/source_node/visible_when/states. Pass 2 owns anchor/layout/box. Pass 3 owns background/content/interaction/description.

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

**After section-map is written — dispatch per-unit subagents.** For each independent unit (page, modal, shared-shell) in the section-map, spawn a subagent. Each subagent receives only its unit's frames (each with a `source_node` for Figma queries and a `state_type` for the YAML state id), the requirement-slice, the design source locator, and the template path. It independently executes Stage 3 for its assigned unit — running three incremental passes (skeleton → layout → style/content), each pass processing frames ONE AT A TIME, and editing a single YAML file. Dispatch all units in parallel. The main session does not gather evidence or freeze YAML; it only dispatches, collects results, then runs Stage 4 review.

Skip subagent dispatch only when the user explicitly requested no subagent usage, or when there is exactly one unit with ≤2 state frames.

### 3. Three-Pass Incremental Contract Construction *(runs inside per-unit subagent)*

This step runs inside each per-unit subagent. The subagent has access only to its assigned unit's frames and evidence — no cross-contamination from other units.

**Execution model:** Three sequential passes over the same YAML file. Each pass processes frames ONE AT A TIME — never batch all frames into a single Figma query. Each pass fills ONLY its assigned fields and does not touch fields owned by other passes.

**First, copy the template.** Locate `templates/ui-acceptance-contract-template.yaml` and copy it verbatim to the output path for this unit. All three passes edit this single file.

#### Pass 1 — Skeleton Layer

**Purpose:** Build the component tree structure and state declarations.

**Figma queries:** `get_structure(frame_source_node)` — once per frame, structure-level only. Do NOT use `get_code` in this pass.

**FIELDS YOU FILL:**
- `version`, `contract_id`
- `source` — requirement filename, figma file key, root node id, cache path
- `states` — one entry per frame: `id` (from frame's `state_type` classification) and `source_node`
- `background` — page-level color only, from the default/idle frame
- `regions[].children[]` — component tree skeleton: `id`, `type`, `name`, `source_node`, `visible_when`, recursive `children`

**DO NOT TOUCH:** `anchor`, `layout`, `box` (width/height/padding), `background` (component-level), `content` (text/icon/image/font), `interaction`, `description`. Leave these as template defaults (`null`, `{}`, `[]`, `0`).

**Per-frame iteration:**

For EACH frame in the unit's frame list, one at a time:

1. Call `get_structure(<frame-source-node>)`.
2. Extract the component hierarchy — component types, nesting relationships, visible elements.
3. **First frame processed:** Create all component nodes in `regions[].children[]`. Fill `id`, `type`, `name`, `source_node`. Set `visible_when: null` (default state components are always visible). Recursively populate `children` using the Figma parent-child structure.
4. **Subsequent frames:** For each component found in this frame:
   - If a component with the same `source_node` already exists in the tree → it is the same component in a different state. Do NOT create a duplicate. Set or refine the `visible_when` condition if it is state-specific.
   - If a component has a new `source_node` not yet in the tree → it is state-specific content. Append it to the appropriate parent's `children` with `visible_when` set to the semantic condition that makes it appear.
5. Add the frame's state entry to the `states` list at the top of the YAML — one `id` + `source_node` per frame.

**Merging rules across states:**
- Components present in all states: use the default/idle frame's `source_node`, `visible_when: null`.
- Components present only in some states: use a frame where they ARE visible as `source_node`, set `visible_when` to the semantic condition.
- Components that differ only in style between states: one component entry, style diffs go into `states` — filled in Pass 3.
- Never create two component entries with the same `id`.

**After Pass 1:** The YAML has a complete `states` list and a complete component tree with `id`, `type`, `name`, `source_node`, `visible_when`. All other fields are template defaults.

#### Pass 2 — Layout Layer

**Purpose:** Fill positioning, sizing, and layout for every component.

**Figma queries:** `get_code(frame_source_node)` — once per frame, code-level. Read the YAML from Pass 1 to find components by `source_node`.

**FIELDS YOU FILL:**
- `anchor` — exactly 4 entries per component: `start`, `end`, `top`, `bottom`. Each has:
  - `to`: reference component id, `screen_start`, `screen_end`, `screen_top`, `screen_bottom`
  - `direction`: which edge of the reference to attach to
  - `offset`: `<Npx>` gap from the reference edge, or `auto` when parent layout controls position
  - `note`: required when `offset` is `auto` — explain how the offset is calculated
- `layout` — `direction` (vertical/horizontal/none), `align`, `gap`
- `box` — `width` (auto/fill/<Npx>), `height` (auto/<Npx>), `padding` (all 4 required: top/right/bottom/left; use `0` when flush)

**DO NOT TOUCH:** All Pass 1 fields (`id`, `type`, `name`, `source_node`, `visible_when`, `states`). Also: `background` (component-level), `content` (text/icon/image/font), `interaction`, `description`. Do NOT write `description` here — Pass 3 handles it even for fixed px.

**Per-frame iteration:**

For EACH frame in the unit's frame list, one at a time:

1. Read the current YAML file. Find all components whose `source_node` belongs to this frame.
2. Call `get_code(<frame-source-node>)` for precise positioning data.
3. For each component found in this frame, extract and fill:
   - **anchor**: Compute all 4 anchor entries. Offset from reference bottom edge formula: `offset = child.topY − (ref.topY + ref.height)`. Use `0px` for flush attachment. Use `auto` when the parent layout (e.g. a list) controls positioning — add a `note` explaining the calculation.
   - **layout**: Extract direction, alignment, and gap from Figma auto-layout or manual positioning data.
   - **box**: `width` prefer `auto` > `fill` > `<Npx>`. `height` prefer `auto` > `<Npx>`. `padding` all 4 directions from measured insets; use `0` where the design shows flush edges.
4. Move to the next frame. Repeat until all frames processed.

**After Pass 2:** Every component has complete anchor, layout, and box. `background` (component-level), `content`, `interaction`, and `description` remain as template defaults.

#### Pass 3 — Style/Content Layer

**Purpose:** Fill visual styling, content, and interactions for every component.

**Figma queries:** `get_code(frame_source_node)` — once per frame, code-level. May reuse cached data from Pass 2 (same `get_code` query). Read the YAML from Pass 2 to find components.

**FIELDS YOU FILL:**
- `background` — component-level: `color`, `border` (radius/width/color), `shadow`, `opacity`
- `content` — exactly ONE slot populated per component:
  - Text components: `text` (visible text content) + `font` (family, size, weight, color, height, align)
  - Icon components: `icon` (src — asset filename, size — display size)
  - Image components: `image` (src, width, height, fit)
- `interaction` — `on` (click/long-press/none), `action`, `note`
- `states` — per-state diffs from default. Component-state keys (e.g. `selected`, `active`, `disabled`), each a partial component diff. Example: `{ selected: { background: { border: { color: "#41B8F4" } } } }`.
- `description` — required when `box.width` or `box.height` uses fixed `<Npx>`; explain why `auto` was not applicable (e.g. "icon baseline size", "touch target minimum").

**DO NOT TOUCH:** All Pass 1 fields, all Pass 2 fields (`anchor`, `layout`, `box`). DO NOT modify component tree structure, add/remove nodes, or change `source_node` values. DO NOT change `visible_when` conditions.

**Per-frame iteration:**

For EACH frame in the unit's frame list, one at a time:

1. Read the current YAML file. Find all components whose `source_node` belongs to this frame.
2. Call `get_code(<frame-source-node>)` — reuse cached results from Pass 2 if available in `.ai-delivery/figma-cache/<file-key>/code/<node-id>.json`; fetch if not cached.
3. For each component in this frame, extract and fill:
   - **background**: Color fill, border styling, shadow, opacity.
   - **content**: Determine content type from the Figma node — text node → `text`+`font`; vector/icon node → `icon`; image fill node → `image`. Populate exactly one slot.
   - **interaction**: If the component is interactive (has click/long-press behavior in the design), fill `on`, `action`, and `note`.
   - **states**: If this component has style variations across states identified in Pass 1, write the per-state diffs. Each diff contains only the changed properties from the component's default (Pass 3) values.
   - **description**: If `box.width` or `box.height` uses fixed `<Npx>`, write a brief justification.
4. Move to the next frame. Repeat until all frames processed.

**After Pass 3:** The YAML contract is COMPLETE. All fields are populated with source-backed values.

**After all three passes:** The subagent returns the completed `ui-acceptance-contract.yaml` to the main session. The main session collects all unit contracts and proceeds to Stage 4.

### 4. Final Contract Review

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
