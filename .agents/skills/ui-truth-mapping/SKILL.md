---
name: ui-truth-mapping
description: Use when a design source (Figma) needs to be extracted into a single canonical HTML UI contract (schema v2) for 1:1 implementation. Auto-detects and splits multiple units (pages, modals, shared components) from a single design source.
---

# UI Truth Mapping

Extract structured UI truth from a design source (Figma) and freeze it as a single canonical `ui-contract.html` file per unit (schema v2). The HTML file is the only output — there is no separate mapping document, and no companion YAML or JSON file beside it.

A single design source may contain multiple independent units: distinct pages, modal overlays, or shared components (navigation shells, tab bars). Each unit gets exactly one `ui-contract.html`. Multiple states of the same unit (loading, empty, error, selected/unselected) live inside that one file as `<template data-ui-state>` blocks — they are never separate contracts.

This skill does one thing: given a requirement-slice + design source, it locates a matching existing contract (if any) or creates a new one, then freezes or patches a single `ui-contract.html` per unit. It does not manage delivery state beyond its own metadata, decide what runs next, or handle blockers outside its own hard gate.

## Input

- A requirement-slice document (scope, fields, acceptance signals)
- A design source locator (Figma file key + node id, or equivalent)
- For follow-up requirements against an existing unit: any hint of the target contract (explicit path, unit id, or "no known contract yet")

## Output

One `ui-contract.html` per independent unit:

```
<output-dir>/
├── <unit-id>/
│   └── ui-contract.html   # schema v2 — meta + tokens + semantic DOM + review panel
├── <unit-id>/
│   └── ui-contract.html
```

There is no aggregate index file. Cross-unit relationships (e.g. a page depending on a shared component) live inside each unit's own `unit.dependencies` metadata.

## Template

Use the provided template — do not invent structure:

```
templates/
└── ui-contract-template.html   # HTML contract v2 template — meta, tokens, DOM, review panel
```

## Hard Boundary

- Do not invent visual truth — no adding units, states, components, or fields beyond what Figma evidence supports.
- Do not treat screenshots or node names alone as sufficient evidence. Structured `get_code`/`get_structure` payloads are required.
- Do not create a second UI truth source beside `ui-contract.html` — no companion YAML, JSON, or markdown mapping/notes file.
- Do not model system UI as contract content: status bars, system navigation, soft keyboards, and device chrome must never appear as `data-ui-kind` values. Use CSS safe-area handling on the affected unit instead.
- Do not assign a functional `data-ui-kind` to empty containers; every `data-ui-id` element needs visible text, icon, image, or clear structural evidence.
- Do not leave a `data-ui-id` element without both `data-figma-node` and `data-ui-kind` — every unit of truth must stay traceable to its source.
- Do not use `data-evidence="inferred"` without a matching note in `[data-ui-review-panel]` — silent inference is a process failure.
- Do not generate `ui-contract.html` from memory. Copy `templates/ui-contract-template.html` verbatim to the output path, then fill in values field by field. Preserve the four constrained regions (`#ui-contract-meta`, `<style>` tokens, `<main data-ui-contract>`, `[data-ui-review-panel]`) — never add a fifth free-form region.
- Do not batch every frame into a single Figma query. Process one frame at a time: query it, fill its evidence, move to the next.
- Do not scan or diff every historical `ui-contract.html` in the repo to find a match. Locate the candidate contract via requirement id, component/route semantics, an already-known unit relationship, or an explicit user-specified path — never a blind repo-wide scan.
- Do not patch a matched contract when the match is ambiguous (more than one plausible candidate) — stop and ask the user to disambiguate before touching any file.
- Do not claim `delivery.status: "implemented"` or `"merged"` without a complete `delivery.implemented` object (`type`, `target`, `requirement`, `version`, `status`).

## Locate: requirement lookup and implementation lookup

Before deciding to create or patch, run an implementation lookup: check whether a matching `ui-contract.html` already exists for this unit.

- Prefer an explicit path the user or the requirement-slice already names.
- Otherwise search by requirement id (`unit.requirements` contains this sub-requirement), component/route semantics (`unit.route_or_trigger`, `unit.title`), or a known shared-component dependency.
- The Figma node id is a **patch anchor once a file is located** — not a discovery key across the whole repository. Do not search by node id alone across every contract file.
- Exactly one match → proceed to Decide. Zero matches → create new. More than one plausible match → STOP, report the candidates, and ask the user to pick one.

## Decide: create vs incremental patch

| Situation | Action |
|---|---|
| No existing contract matches this unit | **Create.** Copy the template and run the full workflow below. |
| Exactly one contract matches and this requirement's change fits inside it (new state, content edit, minor layout adjustment) | **Incremental patch.** Edit only the affected subtree, states, and metadata fields in place. Leave unrelated units and unrelated subtrees untouched. |
| The unit's boundary, route, or shared dependency changes fundamentally | **Rebuild** that unit's contract, keeping its `contract_id`/`unit.id` stable if the unit is conceptually the same. |
| Match is ambiguous | **Block.** Do not guess; ask the user to disambiguate before touching any file. |

## Workflow

### 1. Confirm upstream and locate

Read the requirement-slice to understand the UI scope, then run the Locate step above. Record the decision (create / incremental patch / rebuild) before touching design data.

### 2. Enumerate frames and classify units

**Enumerate ALL frames first:** query the design source at the parent/selection level (not a specific node) to list every top-level sibling frame — id, name, type, position. Skipping this step causes state variants to be missed.

Classify each frame:

| Classification | Meaning | Action |
|---|---|---|
| `page` | A full-screen page or screen route | One `ui-contract.html` with `unit.type: "page"` |
| `page-state` | An alternative state of an already-classified page (loading, empty, error, selected, unselected) | A `<template data-ui-state>` block inside that page's file — do NOT create a separate contract |
| `modal` | A modal dialog, bottom sheet, popover, or overlay | One `ui-contract.html` with `unit.type: "modal"` — never nested inside a page |
| `shared-component` | A shared navigation shell, tab bar, or persistent frame wrapping pages | One `ui-contract.html` with `unit.type: "shared-component"`; referenced via `unit.dependencies` from pages that use it |
| `ignore` | Non-UI content (designer notes, annotations, guide lines) | Exclude from contracts entirely |

**Grouping rules:**
- Frames sharing the same shell/layout that differ only by content state → `page-state` variants of one unit.
- Frames with distinct layouts, different navigation context, or independent entry points → separate `page` units.
- Modal overlays, sheets, and dialogs → always a separate unit. They have their own lifecycle, entry trigger, and dismissal — never a child template of a page's contract.
- When in doubt between `page` and `page-state`: check whether the frames are reached via the same route/URL. Same route → `page-state`. Different route or triggered by a user action → `page`.

**Verification:** confirm every enumerated frame has been assigned to a unit or state. No frame left unclassified.

**Dispatch:** for more than one independent unit, spawn a per-unit subagent so evidence gathering and DOM authoring stay isolated — no cross-unit contamination. Skip subagent dispatch only when the user explicitly requests no subagent usage, or there is exactly one unit with ≤2 states.

### 3. Gather minimal TemPad evidence *(runs inside per-unit subagent when dispatched)*

For each frame in the unit, one at a time:

1. Call `get_code(frame_source_node)` first — it returns semantic markup, layout styles, tokens, and asset references. This is the primary evidence source for structure, positioning, and content.
2. Call `get_structure(frame_source_node)` only when hierarchy, geometry, or overlap remains ambiguous after `get_code`. Do not call it by default — it is a disambiguation tool, not a first-pass query.
3. Record every `data-figma-node` you intend to cite before writing DOM — no node id may be invented.

### 4. Copy the template verbatim (create) or open the matched file (patch)

**Create:** locate `templates/ui-contract-template.html` and copy it verbatim to `<output-dir>/<unit-id>/ui-contract.html`. All four regions (`#ui-contract-meta`, `<style>`, `<main data-ui-contract>`, `[data-ui-review-panel]`) stay intact; never add a fifth region.

**Incremental patch:** open the located file directly. Do not recopy the template over an existing contract.

### 5. Fill or patch the one-unit HTML

- `#ui-contract-meta` — fill `schema_version: 2`, `contract_id`, `source` (`requirement`/`design_file`/`root_node`/`cache`), `unit` (`id`/`type`/`title`/`route_or_trigger`/`requirements`/`source_node`/`dependencies`), `states` (one entry per frame, exactly one `default: true`), `revision`, `delivery.status`.
- `<style>` — only evidence-backed CSS custom properties and rules read from `get_code`. Prefer `var(--token)` when TemPad returns a canonical token binding; otherwise keep the literal value TemPad returned.
- `<main data-ui-contract>` — build the semantic DOM. `data-ui-unit-id`/`data-ui-unit-type` on `<main>` must match `meta.unit.id`/`meta.unit.type`. Every truth-bearing element carries a unique `data-ui-id`, a `data-ui-kind` from the component vocabulary, and a `data-figma-node`. Wrap state-only content in `<template data-ui-state="<id>">` matching a declared state id.
- `[data-ui-review-panel]` — a collapsed-by-default `<details>` holding source nodes, state notes, and any inference reasoning. Every `data-evidence="inferred"` element must have a matching `dt[data-ui-evidence-for]`/`dd` pair here.
- Incremental patch: touch only the subtree, states, and metadata fields the requirement actually changes. Leave unrelated `data-ui-id` subtrees, unrelated states, and other units' `unit.dependencies` untouched.

Process one frame at a time — never batch every frame into a single query or a single edit pass.

### 6. Browser review

Open the contract HTML in a browser (or the IDE's rendered preview) and compare it side by side with the Figma frame:

- Verify the default-state layout matches without opening the review panel.
- Expand `[data-ui-review-panel]` and confirm every cited `data-figma-node` and inference note is legible and accurate.
- Step through each `<template data-ui-state>` block (or its rendered preview) to confirm each state's content matches its source frame.

### 7. Run the validator

```bash
python3 scripts/validate-ui-contract-html.py <path-to-ui-contract.html>
```

Only continue when it prints `OK`. On failure, fix the contract and re-run — never claim `frozen`/`acceptance_frozen` on a failing contract.

### 8. After implementation — backfill delivery and revalidate

Once the unit is implemented, edit the same file's `#ui-contract-meta`:

- set `delivery.status` to `"implemented"` (or `"merged"` once merged);
- fill `delivery.implemented`: `type`, `target` (code location), `requirement`, `version`, `status`.

Re-run the validator — it enforces that `delivery.implemented` is complete whenever `delivery.status` is `"implemented"` or `"merged"`. Do not create a separate implementation-tracking file; this backfill inside the same HTML is the only implementation record.

## Component Type Vocabulary

`container`, `card`, `list`, `list-item`, `form`, `text`, `text-input`, `button`, `image`, `icon`, `tab`, `navigation`, `divider`, `badge`, `modal`, `sheet`, `toast`, `custom`

## Anti-patterns (treat as process failure)

- Writing a companion YAML, JSON, or markdown file to hold UI truth alongside `ui-contract.html`.
- Modeling status bars, navigation bars, keyboards, or device chrome as `data-ui-kind` content instead of using CSS safe-area handling.
- Using `data-evidence="inferred"` with no matching review-panel note.
- Scanning every historical contract file to "find" a unit instead of using requirement id, semantics, or an explicit user-specified path.
- Rewriting an entire matched contract for a small requirement instead of an incremental patch.
- Claiming `frozen`/`implemented`/`merged` status without running the validator to `OK`.
- Hand-authoring DOM structure without copying the template first.
