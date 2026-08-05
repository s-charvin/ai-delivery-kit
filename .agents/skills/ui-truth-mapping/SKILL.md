---
name: ui-truth-mapping
description: Use when a design source (Figma) needs to be extracted into a single canonical HTML UI contract (schema v2) for 1:1 implementation. Auto-detects and splits multiple units (pages, modals, shared components) from a single design source.
---

# UI Truth Mapping

Extract structured UI truth from a design source (Figma) and freeze it as a single canonical `ui-contract.html` file per unit (schema v2). The HTML file is the only output — there is no separate mapping document, and no companion YAML or JSON file beside it.

A single design source may contain multiple independent units: distinct pages, modal overlays, shared components (navigation shells, tab bars), or **requirement-scoped component subtrees**. Each unit gets exactly one `ui-contract.html`. Multiple states of the same unit (loading, empty, error, selected/unselected) live inside that one file as `<template data-ui-state>` blocks — they are never separate contracts.

**Browser preview is mandatory for every contract (single-state files keep the infrastructure for consistency).** Every state (including default) lives in `<template data-ui-state>`. Native `<template>` is not rendered by browsers — the template's fixed `script[data-ui-state-preview]` hydrates `[data-ui-state-host]` on load and powers `[data-ui-state-switcher]` so reviewers can flip states. Do not claim layout fidelity from an unhydrated empty host.

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
│   └── ui-contract.html   # schema v2 — meta + tokens + DOM + state preview + review panel
├── <unit-id>/
│   └── ui-contract.html
```

There is no aggregate index file. Cross-unit relationships (e.g. a page depending on a shared component) live inside each unit's own `unit.dependencies` metadata.

## Template

Use the provided template — do not invent structure:

```
templates/
└── ui-contract-template.html   # HTML contract v2 template — meta, tokens, DOM, preview, review panel
```

## Hard Boundary

- **Requirement-scoped extract:** read the requirement-slice **In Scope** first. List the visual artifacts that must appear (e.g. reject tip, appeal CTA, report sheet). The contract root is the **smallest ancestor subtree covering the in-scope artifacts that belong to one unit** — not the full-screen frame by default. **When in-scope artifacts are disconnected in the Figma tree** (their smallest common ancestor is the full page — e.g. a tip in the message list *and* a CTA in the composer), **split them into multiple `component` / `modal` units, one per artifact cluster**, each with its own local minimal-ancestor root. Never collapse disconnected artifacts into a single whole-page contract just to satisfy "one root covers everything" — that is the whole-page-dump anti-pattern. Full-page chrome that is not in scope is context only (`data-ui-scope="context"` / `ignore`), never acceptance truth.
- Do not invent visual truth — no adding units, states, components, or fields beyond what Figma evidence supports.
- Do not invent layout — DOM structure, dimensions, positioning, spacing, and stacking come from TemPad `get_code` by **mechanical transfer**. Only add `data-ui-*` / `data-figma-node` / `data-evidence` annotations. Hand-authored semantic flex/grid rewrites that drop get_code geometry are process failures.
- Do not treat screenshots or node names alone as sufficient evidence. Structured `get_code`/`get_structure` payloads are required.
- Do not create a second UI truth source beside `ui-contract.html` — no companion YAML, JSON, or markdown mapping/notes file.
- Do not model system UI as contract content: status bars, system navigation, soft keyboards, and device chrome must never appear as `data-ui-kind` values. Use CSS safe-area handling on the affected unit instead.
- Do not assign a functional `data-ui-kind` to empty containers; every `data-ui-id` element needs visible text, icon, image, or clear structural evidence.
- Do not leave a `data-ui-id` element without both `data-figma-node` and `data-ui-kind` — every unit of truth must stay traceable to its source.
- Do not truth-annotate context chrome. Elements marked `data-ui-scope="context"` exist only to preserve layout geometry for the in-scope subtree; they must **not** carry `data-ui-id`, `data-ui-kind`, or `data-figma-node`. Context is positioning, not acceptance truth — mixing the two creates a second freeze surface the gate cannot govern.
- Do not use `data-evidence="inferred"` without a matching note in `[data-ui-review-panel]` — silent inference is a process failure.
- Do not generate `ui-contract.html` from memory. Copy `templates/ui-contract-template.html` verbatim to the output path, then fill in values field by field. Preserve the four constrained regions (`#ui-contract-meta`, `<style>` tokens, `<main data-ui-contract>`, `[data-ui-review-panel]`) — never add a fifth free-form region. Required preview infrastructure (`[data-ui-state-switcher]`, `[data-ui-state-host]`, `script[data-ui-state-preview]`) lives **inside** `<main>` and must be kept from the template.
- Do not delete or reimplement `script[data-ui-state-preview]`. Without it, default and alternate states are invisible in the browser.
- Do not batch every frame into a single Figma query. Process one frame at a time: query it, fill its evidence, move to the next.
- Do not scan or diff every historical `ui-contract.html` in the repo to find a match. Locate the candidate contract via requirement id, component/route semantics, an already-known unit relationship, or an explicit user-specified path — never a blind repo-wide scan.
- Do not patch a matched contract when the match is ambiguous (more than one plausible candidate) — stop and ask the user to disambiguate before touching any file.
- Do not claim `delivery.status: "implemented"` or `"merged"` without a complete `delivery.implemented` object (`type`, `target`, `requirement`, `version`, `status`).
- Do not claim `frozen` / 1:1 fidelity from validator `OK` alone — `OK` means schema passed; browser-hydrated default preview and scope alignment are also required before calling the contract frozen.

## Locate: requirement lookup and implementation lookup

Before deciding to create or patch, run an implementation lookup: check whether a matching `ui-contract.html` already exists for this unit.

- Prefer an explicit path the user or the requirement-slice already names.
- **Route by the in-scope artifact's physical Figma container, not by the requirement's owning route.** A tiny change (red dot, badge, single control) often physically lives inside another unit's `source_node` subtree — e.g. an unread badge on a shared tab bar, a disabled state on a button inside an existing page. In that case patch the contract whose `unit.source_node` contains the artifact, even if the requirement nominally belongs to a different route. Routing by requirement-route here would fork the artifact into the wrong contract and fragment the shared component's truth.
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

### 1. Confirm upstream, scope inventory, and locate

Read the requirement-slice **In Scope** / **Out of Scope** (or equivalent) and build a short **scope inventory** before touching design data:

1. **Must-freeze artifacts** — every visual product the slice accepts (components, tips, CTAs, sheets…).
2. **Context-only chrome** — surrounding page pieces useful for orientation but not accepted against.
3. **Ignored** — notes, annotations, device chrome.

Then run the Locate step above. Record the decision (create / incremental patch / rebuild) before querying TemPad.

Contract `unit.source_node` / `source.root_node` must be the **minimal ancestor covering the must-freeze artifacts that belong to this one unit** — never default to the full-screen page frame when the slice only hits a subtree. **If the must-freeze artifacts are disconnected** (smallest common ancestor is the whole page), do not enlarge one unit's root to swallow them all: split into multiple `component` / `modal` units and give each its own local minimal-ancestor root. The "smallest ancestor" rule is per-unit, never per-requirement-global.

### 2. Enumerate frames and classify units

**Enumerate ALL frames first:** query the design source at the parent/selection level (not a specific node) to list every top-level sibling frame — id, name, type, position. Skipping this step causes state variants to be missed.

Classify each frame:

| Classification | Meaning | Action |
|---|---|---|
| `page` | A full-screen **route** change that is itself in In Scope | One `ui-contract.html` with `unit.type: "page"` |
| `component` | A requirement-scoped subtree / control / tip / inline module (not a full route) | One `ui-contract.html` with `unit.type: "component"` — prefer this over copying the whole page |
| `page-state` / `component-state` | An alternative state of an already-classified unit (loading, empty, error, selected, unselected) | A `<template data-ui-state>` block inside that unit's file — do NOT create a separate contract |
| `modal` | A modal dialog, bottom sheet, popover, or overlay | One `ui-contract.html` with `unit.type: "modal"` — never nested inside a page |
| `shared-component` | A shared navigation shell, tab bar, or persistent frame wrapping pages | One `ui-contract.html` with `unit.type: "shared-component"`; referenced via `unit.dependencies` from pages that use it |
| `context` | Page chrome needed only to locate the in-scope subtree | Omit from acceptance DOM, or include with `data-ui-scope="context"` — never treat as freeze truth |
| `ignore` | Non-UI content (designer notes, annotations, guide lines) or out-of-scope chrome | Exclude from contracts entirely |

**Grouping rules:**
- When In Scope is a local change (tip, badge, sheet entry, one control) → prefer `component` or `modal`, **not** a full `page` dump of the Figma screen.
- **Disconnected in-scope artifacts → multiple units, not one page contract.** When the must-freeze artifacts live in disconnected Figma subtrees whose smallest common ancestor is the full page (e.g. a reject tip in the message list *and* an appeal CTA in the composer), assign each artifact cluster to its own `component` (or `modal`) unit. Never collapse them into a single `page` contract whose root is the whole screen — that is the whole-page-dump anti-pattern dressed up as "one root covers all". Typical splits: `reject-tip` component + `appeal-cta` component; `top-badge` component + `report-sheet` modal + the sheet's trigger button (patched into the button's physical container contract).
- Frames sharing the same shell/layout that differ only by content state → state variants of one unit.
- Frames with distinct layouts, different navigation context, or independent entry points → separate units.
- Modal overlays, sheets, and dialogs → always a separate unit. They have their own lifecycle, entry trigger, and dismissal — never a child template of a page's contract. **The trigger button is NOT part of the modal contract** — patch it into the contract of the button's physical container (the page or component where the button lives). The modal records its trigger in `unit.route_or_trigger` (e.g. `"triggered by report-button click on message-row"`); the container records its dependency on the modal in `unit.dependencies`.
- **Element-level property variants are not state templates.** A single element's attribute change (button `disabled`, input `readonly`, icon `active`, tab `selected`) is patched onto that element's existing node — it does **not** spawn a unit-level `<template data-ui-state>`. Unit-level states are for whole-unit visual changes the reviewer must flip between (loading / empty / error / logged-out). If only one element changes, patch its visual attributes; reserve state templates for full-unit variants.
- When in doubt between `page` and state: check whether the frames are reached via the same route/URL. Same route → state. Different route or triggered by a user action → separate unit (`page` / `modal` / `component` as appropriate).
- When in doubt between `component` and `component-state`: same component instance reached under the same trigger context, differing only in visual content → state of that component. Different instance or different trigger context → separate `component` units.

**Dependency direction:** `unit.dependencies` points from consumer to consumed — a page that renders a shared tab bar lists the tab bar's unit id in its `dependencies`; a page whose action opens a modal lists the modal's unit id. The consumed unit (tab bar, modal) does **not** reverse-reference its consumers.

**Verification:** confirm every enumerated frame has been assigned to a unit, state, context, or ignore. No frame left unclassified. Confirm every must-freeze artifact from §1 appears in some unit's DOM.

**Dispatch:** for more than one independent unit, spawn a per-unit subagent so evidence gathering and DOM authoring stay isolated — no cross-unit contamination. Skip subagent dispatch only when the user explicitly requests no subagent usage, or there is exactly one unit with ≤2 states.

### 3. Gather minimal TemPad evidence *(runs inside per-unit subagent when dispatched)*

For each frame in the unit, one at a time:

1. Call `get_code(frame_source_node)` first — it returns markup, **layout styles**, tokens, and asset references. This is the primary evidence source for structure, positioning, spacing, and content. Prefer the **scoped root** from §1, not the entire page, when In Scope is local.
2. Call `get_structure(frame_source_node)` only when hierarchy, geometry, or overlap remains ambiguous after `get_code`. Do not call it by default — it is a disambiguation tool, not a first-pass query.
3. Record every `data-figma-node` you intend to cite before writing DOM — no node id may be invented.

### 4. Copy the template verbatim (create) or open the matched file (patch)

**Create:** locate `templates/ui-contract-template.html` and copy it verbatim to `<output-dir>/<unit-id>/ui-contract.html`. All four regions (`#ui-contract-meta`, `<style>`, `<main data-ui-contract>`, `[data-ui-review-panel]`) stay intact; keep `[data-ui-state-switcher]`, `[data-ui-state-host]`, and `script[data-ui-state-preview]` from the template; never add a fifth free-form region.

**Incremental patch:** open the located file directly. Do not recopy the template over an existing contract. If the matched file lacks the preview infrastructure (older v2 file or pre-preview draft), backfill it in this order without rewriting unrelated truth DOM:
1. Move existing truth-bearing DOM (every `data-ui-id` subtree) into a new `<template data-ui-state="default">` inside `<main>`. This is a structural relocation, not a rewrite — preserve nodes, attributes, and order verbatim.
2. Add empty `[data-ui-state-host]` and `[data-ui-state-switcher]` from the current template, and copy `script[data-ui-state-preview]` verbatim.
3. Backfill `meta.states` with one entry `{ "id": "default", "source_node": <unit.source_node>, "default": true }` and set `data-ui-state-default="default"` on `<main>`.
4. Leave the four regions intact; do not introduce a fifth.

### 5. Fill or patch the one-unit HTML

- `#ui-contract-meta` — fill `schema_version: 2`, `contract_id`, `source` (`requirement`/`design_file`/`root_node`/`cache`), `unit` (`id`/`type`/`title`/`route_or_trigger`/`requirements`/`source_node`/`dependencies`), `states` (one entry per frame, exactly one `default: true`), `revision`, `delivery.status`. `unit.type` is `page` | `modal` | `shared-component` | `component`. `unit.source_node` is the scoped root from §1. **State ids must be kebab-case lowercase ASCII** (`^[a-z][a-z0-9-]*$`, e.g. `loading`, `empty-state`) — the preview script builds CSS selectors from state ids and breaks on spaces, quotes, or brackets. **Default state** = the state a reviewer sees on first page load (typically `loaded`/`success`, not transient `loading`/`error`), so the hydrated preview matches the screen's primary visual, not a flicker frame.
- `<style>` — **mechanical transfer** of evidence-backed CSS from `get_code` (including geometry: width/height, position, inset, gap, padding, margin, display, flex/grid, z-index, typography, color). Prefer `var(--token)` when TemPad returns a canonical token binding; otherwise keep the literal value TemPad returned. Do not replace get_code layout with a rewritten semantic stylesheet.
- `<main data-ui-contract>` —
  - Keep `[data-ui-state-switcher]` and empty `[data-ui-state-host]`.
  - Put **every** declared state (including default) into `<template data-ui-state="<id>">`. Transfer get_code DOM into the template; only add annotation attributes.
  - Shared identical chrome across all states may sit outside the host **only** when it is in scope and identical across every state; otherwise duplicate it inside each state template.
  - Out-of-scope positioning chrome (context) may sit outside the host to preserve geometry, but must be marked `data-ui-scope="context"` and must **not** carry `data-ui-id` / `data-ui-kind` / `data-figma-node`. Context is not truth; the validator rejects truth-annotated context.
  - `data-ui-unit-id`/`data-ui-unit-type`/`data-ui-state-default` on `<main>` must match meta.
  - Every truth-bearing element carries unique `data-ui-id`, `data-ui-kind`, and `data-figma-node`.
  - Keep `script[data-ui-state-preview]` verbatim so open-in-browser hydrates the default state and enables switching.
- `[data-ui-review-panel]` — include:
  - `dt[data-ui-scope="in_scope"]` / `dd` listing must-freeze artifacts (node ids + labels); every node id listed here must appear on a non-context `data-figma-node` in the DOM (the validator cross-checks this).
  - `dt[data-ui-scope="out_of_scope"]` / `dd` listing context chrome or `"none"`;
  - inference notes: every `data-evidence="inferred"` needs a matching `dt[data-ui-evidence-for]`/`dd`.
- Incremental patch: touch only the subtree, states, and metadata fields the requirement actually changes. Leave unrelated `data-ui-id` subtrees, unrelated states, and other units' `unit.dependencies` untouched.

Process one frame at a time — never batch every frame into a single query or a single edit pass.

### 6. Browser review

Open the contract HTML in a browser (or the IDE's rendered preview). The preview script must hydrate the default state into `[data-ui-state-host]` without opening the review panel:

- Confirm the **hydrated default** layout matches the Figma scoped root (geometry + content), not an empty host or a hand-rewritten approximation.
- Use `[data-ui-state-switcher]` to step through **every** declared state; each activated host contents must match its source frame.
- Expand `[data-ui-review-panel]` and confirm scope inventory, every cited `data-figma-node`, and inference notes are legible and accurate.
- Never assume "validator OK ⇒ looks like Figma."

### 7. Run the validator

```bash
python3 scripts/validate-ui-contract-html.py <path-to-ui-contract.html>
```

Only continue when it prints `OK`. On failure, fix the contract and re-run — never claim `acceptance_frozen` on a failing contract. Validator `OK` is necessary but not sufficient: browser-hydrated default preview and requirement-scope alignment from §1/§6 are still required before freezing.

**What the validator checks automatically:** schema/DOM structure, single unit root, `data-ui-id` uniqueness + `data-figma-node`/`data-ui-kind` presence (placeholder figma nodes rejected), preview infrastructure present, **every** state template non-empty with visible text/media, `in_scope`/`out_of_scope` inventory present, **in_scope node ids cross-checked against `data-figma-node` values frozen in the DOM**, context chrome not truth-annotated, inference notes back every `data-evidence="inferred"`, delivery fields.

**What the validator cannot check (remain §6 process checks):** `unit.source_node` minimality (no Figma tree access — you must verify the scoped root is the local minimal ancestor, not the full page), layout fidelity to Figma (mechanical transfer vs hand-authored rewrite), browser hydration fidelity (open it and look), and semantic correctness of state/default choices. `OK` ≠ "looks like Figma" and ≠ "scope matches the slice" — those are human/§6 gates.

### 8. After implementation — backfill delivery and revalidate

Once the unit is implemented, edit the same file's `#ui-contract-meta`:

- set `delivery.status` to `"implemented"` (or `"merged"` once merged);
- fill `delivery.implemented`: `type`, `target` (code location), `requirement`, `version`, `status`.

Re-run the validator — it enforces that `delivery.implemented` is complete whenever `delivery.status` is `"implemented"` or `"merged"`. Do not create a separate implementation-tracking file; this backfill inside the same HTML is the only implementation record.

## Component Type Vocabulary

`container`, `card`, `list`, `list-item`, `form`, `text`, `text-input`, `button`, `image`, `icon`, `tab`, `navigation`, `divider`, `badge`, `modal`, `sheet`, `toast`, `custom`

## Anti-patterns (treat as process failure)

- Writing a companion YAML, JSON, or markdown file to hold UI truth alongside `ui-contract.html`.
- **Whole-page dump** of a Figma screen when the slice In Scope only hits a local subtree (reject tip, sheet, badge…).
- **Collapsing disconnected in-scope artifacts into one whole-page contract** (root = full screen) instead of splitting them into per-cluster `component` / `modal` units with local minimal-ancestor roots.
- Skipping the §1 scope inventory and freezing unrelated nav / list / composer chrome as acceptance truth.
- **Routing a tiny change (red dot, badge, disabled state) by the requirement's owning route** instead of by the artifact's physical Figma container, forking the artifact into the wrong contract.
- **Truth-annotating context chrome** (`data-ui-scope="context"` with `data-ui-id` / `data-ui-kind` / `data-figma-node`) — context is positioning only.
- **Spawning a unit-level state template for a single element's property variant** (button `disabled`, input `readonly`) instead of patching that element's attributes.
- **Putting the modal's trigger button inside the modal contract** instead of patching it into the button's physical container contract.
- Hand-authoring a semantic flex/grid layout instead of mechanically transferring `get_code` geometry.
- Putting default (or any) state only in `<template>` and deleting/omitting `script[data-ui-state-preview]` so the browser shows an empty host.
- Claiming browser default-state review without hydration / switcher working, or without stepping through **every** declared state.
- Modeling status bars, navigation bars, keyboards, or device chrome as `data-ui-kind` content instead of using CSS safe-area handling.
- Using `data-evidence="inferred"` with no matching review-panel note.
- Leaving template `PLACEHOLDER-*` values in `data-figma-node` or `unit.source_node` (validator rejects placeholder figma nodes; source_node minimality is a §6 process check).
- Scanning every historical contract file to "find" a unit instead of using requirement id, semantics, or an explicit user-specified path.
- Rewriting an entire matched contract for a small requirement instead of an incremental patch.
- Claiming `acceptance_frozen`/`frozen`/`implemented`/`merged` from validator `OK` alone without hydrated preview + scope alignment.
- Hand-authoring DOM structure without copying the template first.
