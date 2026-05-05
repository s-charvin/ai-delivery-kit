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

**Output:** a `section-map.json` following the template in `templates/section-map-template.json`.

### 3. Gather design evidence
- Check cache first if available.
- Use structured design data from the provider (structure-level query first, then drill to code-level evidence per frame).
- **Every state frame must have evidence.** A page classified with N state frames in step 2 must produce N screen_state entries, each backed by structured evidence from its source_node. Do not map only the simplest/idle state and skip the rest.
- **Ignore system UI:** status bars, system navigation bars, soft keyboards, device chrome, and OS-level overlays are not part of the application UI. Exclude them from evidence and contracts. Only map the application-controlled viewport.
- **Distinguish fill vs fixed width:** A pixel value that equals (frame_width − symmetrical_horizontal_margins) is a design-tool snapshot, not layout intent. Use `fill` when an element spans the full width with consistent margins; reserve fixed px for intentionally sized elements (icons, avatars, fixed buttons).
- **Calculate offsets from anchor bottom:** Region offset = child's top-y − (anchor's top-y + anchor's height). The offset is the gap between the bottom edge of the anchor and the top edge of the child — not the distance between their top edges.

### 4. Freeze YAML contract
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
- `anchor`: `top` | `bottom` | `<region-id>` — attachment point and offset. **Offset = child.top − (anchor.top + anchor.height)** — always measured from the anchor's bottom edge, never from its top edge.
- `layout`: direction, alignment, gap between children
- `box`: width (fill/fixed/auto), height, padding, margin
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
- `box`: width, height, padding, margin
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
- `width: fill` for elements that span their parent's full width (including descendants inside a fill parent). Fixed px only for intentionally sized elements (icons, avatars, fixed buttons). The design tool's pixel value is a frame-size snapshot, not layout intent. Judge by visual context: is this element meant to span the available space, or is it intentionally fixed?
- **Font align uses `start`/`end`** (not `left`/`right`) for RTL compatibility. `layout.align` already follows this convention.
- **Text with `font.size` uses `height: auto`.** Fixed heights on text elements conflict with font rendering across platforms. Containers (buttons, cards, inputs) that wrap text may keep fixed heights for touch targets or layout.
- **Keyboard-aware regions use `safe_area: "bottom"` with `offset: "0px"`.** When a design frame includes a system keyboard and a region sits directly above it, the region's pixel position is a design-tool snapshot — it will move with the keyboard at runtime. Anchor it to `bottom`; the system handles keyboard avoidance. Do NOT calculate an offset from the frame bottom.

## Component Type Vocabulary

`container`, `card`, `list`, `list-item`, `form`, `text`, `text-input`, `button`, `image`, `icon`, `tab`, `navigation`, `divider`, `badge`, `modal`, `sheet`, `toast`, `custom`
