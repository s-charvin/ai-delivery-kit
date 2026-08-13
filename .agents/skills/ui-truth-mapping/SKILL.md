---
name: ui-truth-mapping
description: Use when a Figma design must become frozen HTML UI contract(s) (schema v2) before implementation — especially when evidence is a whole page but the requirement only hits a subtree, when multiple states need browser-switchable preview, when motion/Spine/Lottie/shimmer must be audited via a review-panel motion table, or when prior contracts dumped full screens / conflated motion with data binding / failed hydrated preview.
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

## Quick Reference — Scenario → Unit split

Do not map the entire Figma evidence by default. Match the **requirement size** first:

| Real scenario | Unit(s) to freeze | `source_node` / root | States | Do NOT |
|---|---|---|---|---|
| New full route (page itself In Scope) | `page` (+ `shared-component` only if shell is also newly accepted) | Page content frame (exclude already-owned shell) | Page-level variants in this file | Dump persistent tab/nav shell that already has its own contract |
| Tiny badge / red-dot / one control on existing shell | **Patch** existing `shared-component` / page if its `source_node` contains the artifact; else **create** `component` rooted at the badge/control subtree | Minimal ancestor of the badge/control only | Usually none (element patch); unit states only if the whole unit visually flips | Create a new `messages-page` / whole-shell contract just to carry the badge |
| Disconnected In Scope artifacts (tip in list + CTA in composer) | One `component` / `modal` **per cluster** | Each cluster's local minimal ancestor | Per-unit as needed | One `page` whose root is the full screen "to cover both" |
| Bottom sheet / dialog / popover | `modal` alone; trigger button patched into the button's physical container contract | Sheet/dialog frame | All sheet frames as `<template data-ui-state>` in the modal file | Nest sheet as a page state; omit preview script; put trigger inside the modal contract |
| Multi-state list/form/module | One `component` (or `page` if the route itself is the scope) | Scoped module root | Every visual frame → one template; hydrate + switcher mandatory | Separate contracts per state; empty default template |
| Element property only (`disabled` / `selected`) | Patch that node in its existing unit | Unchanged | Do **not** add a unit-level state template | Spawn `disabled` as a full-unit `<template data-ui-state>` |
| Component with **variant properties** or **motion** (pulse, Lottie, GIF, prototype) | Same unit as the component; add `meta.dynamics[]` + review-panel inventory | Component/instance root | Static **keyframe** in a state template for preview; motion spec in `dynamics` | Treat motion as static PNG only; omit design-delivered animation assets |

## Dynamics & motion — discovery vs reviewer presentation

| Dynamic concern | Discovered in §2c? | Where reviewers audit it |
|---|---|---|
| Whole-unit visual states (loading / empty / error / selected shell) | **Yes** | State switcher + `[data-ui-state-host]` static snapshots |
| Element property only (`disabled`, tab `selected`) | **Yes** | Patched node in default state — not a unit-level state template |
| Server/user **content** (avatar, nickname, counts) | **Yes** | `content-bound` in `meta.dynamics[]` + review-panel **Canvas placeholder / Copy** notes — **not** the motion table |
| Figma **component variant** properties | **Yes** | `component-variant` + state templates or element patch |
| **Motion / animation** (Spine, Lottie, shimmer, typewriter, Figma Motion) | **Yes** | `meta.dynamics[]` **and** review-panel **Motion and transitions** table (§ below) |
| Designer-delivered **animation assets** (Lottie / GIF / video) | **Yes** | Poster frame on canvas + `design-animation-asset` + table row + `asset_status` |

**Goal of §2c:** discover, classify, and persist assets when available. **Goal of the review panel:** expose the same facts in **human audit copy** (the user's language) so humans can approve motion and transitions before freeze — not only in chat or `meta.dynamics[]`.

### Why dynamics often miss user review (RCA)

When reviewers ask where the motion is, the failure is usually **presentation**, not that §2c never ran:

| Symptom | Typical cause | Fix |
|---|---|---|
| “Dynamic” confused with API / field binding | Agent treated **motion / UI effects** (Spine, Lottie, shimmer, typewriter) as **dynamic data** (server fields, avatars) | Motion → **Motion and transitions** table; data → **Canvas placeholder / Copy** notes |
| Motion known from requirement/Figma hints but absent from HTML | §2c inventory stayed in chat only; `meta.dynamics[]` / review panel never filled; **or** the note lived on the parent SECTION and the sweep never left `source_node` | Fill **both** `meta.dynamics[]` and the human table **before** presenting the contract; sweep SECTION siblings |
| Cluttered or misleading canvas | Binding tables, field legends, or motion callouts on `[data-ui-state-host]` | Canvas = static layout only (+ optional motion **preview hint**); audit copy lives in `[data-ui-review-panel]` only |
| States switch but host looks blank | Malformed host tag (`<div data-ui-state-host"></div>` with a stray `"`) | Copy verbatim from template: `<div data-ui-state-host></div>` |

**For req-dm-match-card–style units:** Lottie, shimmer, and Spine were in the requirement slice and breakdown — discovery succeeded; reviewers could not audit until the **Motion and transitions** table lived in the review panel (not on the canvas, not as a top field-binding table). A later Figma note (`4451:90123`: load-complete typewriter + tip scale/fade 300ms + match stagger fade 300ms) sat on the **SECTION canvas**, outside `source_node`, and was dropped until the parent-sibling sweep was required.

### Two acceptance surfaces (mandatory split)

| Surface | Purpose | What belongs here |
|---|---|---|
| `[data-ui-state-host]` | Static layout acceptance | get_code DOM in state templates; optional CSS **motion preview hints** (`aria-hidden`, review-panel disclaimer) |
| `[data-ui-review-panel]` | Human audit (user's language) | What the canvas accepts · Not accepted here · **Motion and transitions** table · Canvas placeholder & inference notes |

Never put API field-binding tables, `data-ui-binding` legends, or motion-spec prose on the canvas.

### Terminology — motion / UI effects ≠ dynamic data

| Reviewer term | Skill `kind` | Review-panel home |
|---|---|---|
| **Motion / UI effects** — Spine loop, Lottie, shimmer, typewriter, transitions | `motion-preset`, `design-animation-asset`, `prototype-transition` | **Motion and transitions** `<table class="effect-table">` |
| **Dynamic data / placeholders** — server text, avatar URL, counts | `content-bound` | **Canvas placeholder / Copy** `dt[data-ui-evidence-for]` |
| Whole-unit state flip (loading shell → success shell) | (state templates) | State switcher + `in_scope` list |

When the product doc says “dynamic”, default to **motion / UI effects** unless the sentence is clearly about API fields.

### Review panel — Motion and transitions table (required when motion dynamics exist)

When `meta.dynamics[]` contains any `motion-preset`, `design-animation-asset`, or `prototype-transition` entry:

1. Add a plain `<dt>` (no `data-ui-scope`) in the **user's language**, e.g. the local equivalent of **Motion and transitions (implement in code)**.
2. Open with one sentence: these rows are **motion and transitions**, not data-binding specs.
3. Include `<table class="effect-table">` with columns equivalent to **State | Where | Effect | Reference**, translated into the user's language.
4. Keep `dt[data-ui-dynamics-inventory]` in sync (full rows, or “see Motion and transitions table above” in the user's language when the table is canonical).
5. In §6 user confirmation, **explicitly direct the user to this table** before claiming frozen.

Write `[data-ui-review-panel]` as **human audit copy** (not product UI, not engineer-only jargon). Use the **user's language** for summary, dt labels, table headers, and body copy — the language they are using in this conversation (or the requirement, if that is clearer). Template PLACEHOLDER English is structure only; do not lock the filled panel to English. Keep Figma notes verbatim in `meta.dynamics[].hint_text`; the panel cites `hint_node` and may paraphrase in the user's language. Summary example in the template: `Review notes (not product UI)`.

### Motion preview hints (optional, canvas only)

When a directional cue helps (e.g. loading shimmer):

- CSS-only loop inside the relevant state template, `aria-hidden="true"`, no Lottie/Spine/video bytes in HTML.
- Review panel must say the hint is **preview-only**; product motion is defined in the **Motion and transitions** table.
- Hints do **not** replace `meta.dynamics[]` or the table.

### Dynamics taxonomy (`meta.dynamics[].kind`)

| `kind` | Meaning | Freeze in HTML | Design asset |
|---|---|---|---|
| `content-bound` | Data from server/user/API (avatar URL, nickname, count) | Geometry + placeholder; Figma image is example only | None — note binding field in `implementation_notes` |
| `component-variant` | Figma component property axis (not a full frame) | One state template per variant value **or** element patch when single-property | Static preview per variant frame |
| `motion-preset` | Figma Motion / prototype-driven effect on a node | **Static keyframe** in default state for layout review | Optional reference frame id in `static_preview` |
| `design-animation-asset` | Designer supplied Lottie/GIF/video/spritesheet | Static poster frame in contract; persist animation file in project assets | **Required** — path + hash in `design_asset` |
| `prototype-transition` | Transition between frames (duration, easing) | Document only — not playable in contract | N/A — `implementation_notes` describe trigger → target |

`meta.dynamics` is optional; use `[]` when the unit is entirely static snapshots. When non-empty, every entry must have a matching row in `[data-ui-review-panel]` and, when tied to a frozen node, `data-ui-dynamic` + `data-ui-dynamic-id` on that DOM node.

Each `meta.dynamics[]` entry should also record **how you learned it** and **whether the asset exists**:

| Field | Values | Meaning |
|---|---|---|
| `evidence_source` | `figma-structure` \| `figma-text-hint` \| `requirement-slice` \| `user-confirmed` | Layer/variant/motion probe vs designer copy / sticky vs requirement doc vs user chat |
| `hint_text` | string (optional) | Verbatim designer note when `evidence_source` is `figma-text-hint` — cite the TEXT node id in `hint_node` |
| `hint_node` | Figma node id (optional) | The annotation TEXT / sticky / callout node — not the UI node it describes |
| `asset_status` | `resolved` \| `pending-user` \| `not-applicable` \| `waived` | Whether design bytes are already in the repo, **must ask user**, N/A (content-bound), or user waived |

Example when Figma only has a text callout and no Lottie file:

```json
{
  "id": "badge-breathe",
  "figma_node": "12:340",
  "kind": "design-animation-asset",
  "evidence_source": "figma-text-hint",
  "hint_node": "12:901",
  "hint_text": "Badge pulse motion; Lottie asset attached separately",
  "asset_status": "pending-user",
  "design_asset": null,
  "static_preview": "default",
  "implementation_notes": "Poster frame only until user provides .json"
}
```

### Messy Figma is normal — do not rely on clean layer names alone

Designers often have **non-canonical** layer hygiene. Assume dynamics may appear only as:

- A **TEXT / sticky / callout** near the UI ("motion", "Lottie", "gif", "asset attached separately", "placeholder", "API-returned", "sample", "see motion…")
- A **static screenshot** standing in for animation (no asset embedded in Figma)
- **No file at all** — asset delivered later via drive, chat, or handoff outside Figma

**Rules:**

1. **Text hints are first-class evidence** for *whether* something is dynamic — not for inventing motion curves or asset bytes. Record `evidence_source: "figma-text-hint"` + verbatim `hint_text`.
2. **Map hint → target node** by spatial proximity and copy semantics (e.g. arrow/callout parent, same auto-layout row, or explicit node name in the note). If ambiguous → **ask the user** which node the note refers to; do not guess.
3. **Do not classify dynamics-hint text as `ignore`** unless it is clearly unrelated meta (version stamp, designer credit). Notes that describe motion, placeholders, or "resource attached separately" feed §2c — they are not disposable chrome.
4. **Off-Figma assets are expected.** When hint or requirement says Lottie/GIF/video/spritesheet but Figma has no fetchable bytes → `asset_status: "pending-user"`, freeze **poster/placeholder** geometry only, and **escalate to the user** (see §2d). Never redraw animation as a static icon and call it done.
5. **Empty `dynamics: []` is allowed only after** structure sweep **and** text-hint sweep (**scoped subtree + parent SECTION siblings**) **and** requirement-slice keyword pass all return nothing dynamic.

## Hard Boundary

- **Requirement-scoped extract:** read the requirement-slice **In Scope** first. List the visual artifacts that must appear (e.g. reject tip, appeal CTA, report sheet). The contract root is the **smallest ancestor subtree covering the in-scope artifacts that belong to one unit** — not the full-screen frame by default. **When in-scope artifacts are disconnected in the Figma tree** (their smallest common ancestor is the full page — e.g. a tip in the message list *and* a CTA in the composer), **split them into multiple `component` / `modal` units, one per artifact cluster**, each with its own local minimal-ancestor root. Never collapse disconnected artifacts into a single whole-page contract just to satisfy "one root covers everything" — that is the whole-page-dump anti-pattern. Full-page chrome that is not in scope is context only (`data-ui-scope="context"` / `ignore`), never acceptance truth.
- **Unit Split Plan before evidence:** fill the §1b plan (artifact → unit → scoped `source_node` → `get_code` target) before any TemPad call or template copy. Skipping the plan and authoring from a whole-page selection is a process failure.
- **Scoped `get_code` only:** call `get_code` on each planned unit's `source_node` (and its state frames). Do **not** `get_code` the full-screen page and prune, and do not paste a whole-page dump then mark leftovers `context`.
- **Tiny-change create vs patch:** if a matching contract already owns the physical container → **incremental patch** (add/adjust only the in-scope nodes; update `unit.requirements` + review-panel `in_scope`; do not expand `in_scope` to the whole shell). If no matching contract exists → **create `component`** rooted at the artifact's minimal ancestor — do **not** invent a brand-new full `shared-component` / `page` dump of the surrounding chrome solely to host a badge.
- Do not invent visual truth — no adding units, states, components, or fields beyond what Figma evidence supports.
- Do not invent layout — DOM structure, dimensions, positioning, spacing, and stacking come from TemPad `get_code` by **mechanical transfer**. Only add `data-ui-*` / `data-figma-node` / `data-evidence` annotations. Hand-authored semantic flex/grid rewrites that drop get_code geometry are process failures.
- Do not invent or redraw icon/image glyphs. Every icon or image must come from the design asset itself (mechanical transfer of asset bytes) or from an **existing project asset** reused verbatim. When `get_code` returns an asset shell (`<svg data-src="...">` or an asset URL), the asset bytes must be fetched and persisted (inline SVG bytes or a saved project asset file, annotated with the asset hash) — never an empty shell left in place, and never a hand-drawn "looks close enough" approximation. An icon that merely resembles the design is a forged truth.
- `get_structure` is **geometry-only evidence** — it never proves paint. Color, opacity, gradient, and stroke values must come from `get_code` tokens or asset bytes; an element cited from structure alone must not carry paint values filled in from memory (a 20%-opacity handle bar rebuilt as solid black is a forged truth).
- Do not treat every picture in Figma as a static design asset. Distinguish **static design icons** (frozen asset truth) from **dynamic/server-provided imagery** (avatars, user uploads, server badges — the Figma picture is only an example). Judge from requirement context; freeze only geometry + placeholder semantics for dynamic content, note it in the review panel, and never download example content as a frozen asset.
- Do not skip the **§2c dynamics scan** when the scoped subtree contains COMPONENT/INSTANCE nodes, motion-named layers, or the requirement mentions animation/Lottie/GIF/video — record `dynamics: []` only after explicit confirmation the unit is static.
- Do not skip **parent SECTION / canvas sibling** TEXT notes in §2c step 0. A note that sits beside the frames (not nested in `source_node`) is still first-class motion evidence. Truncating a multi-line transition note, or classifying it as `ignore` because it is “outside the unit root”, is a process failure.
- Do not omit `meta.dynamics[]` when the review panel already lists motion, or when a nearby Figma note describes a transition / typewriter / shimmer. The table and `meta.dynamics[]` must stay in sync; a table-only inventory is not freeze-complete.
- Do not treat a **loading→success (or similar) transition note** as a loop that plays inside every state. Map it to `prototype-transition` with trigger → target; canvas may show a **preview hint only on the target state**.
- Do not approximate **Lottie/GIF/video** motion as a hand-drawn static icon — classify as `design-animation-asset`, persist the file when fetchable, and freeze a poster keyframe for preview.
- Do not ignore **Figma component variant properties** when variant frames or `componentProperties` exist — map them to `component-variant` dynamics and/or state templates; do not collapse unrelated variants into one static snapshot without documentation.
- Do not claim motion is "obvious from design" without probing: call `get_node_motion` (figma-bridge) when available; otherwise cite structure + requirement + designer notes in the dynamics inventory.
- Do not embed **product** animation bytes (Lottie JSON, Spine, GIF, video) inside `ui-contract.html` — freeze poster/placeholder geometry and specify runtime motion via `meta.dynamics[]` + the **Motion and transitions** table. CSS **motion preview hints** are allowed only per “Motion preview hints” above.
- Do not put API field-binding tables, `data-ui-binding` legends, or motion-spec callouts on `[data-ui-state-host]` or above it — binding belongs in implementation specs, not the visual acceptance canvas.
- Do not conflate **motion / UI effects** (motion table) with **content-bound** placeholders in the same table row without labeling — server-filled copy/avatars go under **Canvas placeholder / Copy** notes.
- Do not write `1:1` next to digits in review-panel prose — the validator may parse `\d+:\d+` as a Figma node id; write "pixel-level" instead.
- Do not treat designer copy / stickies that describe motion, placeholders, or "resource attached separately" as `ignore` — they are dynamics hints for §2c unless clearly unrelated meta.
- Do not infer which UI node a text hint refers to when multiple candidates exist — ask the user to point at the target node or provide the asset.
- Do not declare a contract **frozen** while any `meta.dynamics[]` entry or asset note has `asset_status: "pending-user"` (or equivalent `pending:` wording) **unless** the user explicitly waives that item in chat — then set `asset_status: "waived"` and quote their waiver in the review panel.
- Do not silently skip missing Lottie/GIF/video because it is "probably on the designer's drive" — **actively ask the user** to attach or path the file (§2d).
- Do not require perfectly named layers (`animate`, `lottie`) as the only discovery signal — **always run the text-hint sweep** in §2c step 0.
- Do not declare a contract frozen without **explicit per-contract user confirmation**. Every generated or patched `ui-contract.html` must be presented to the user for manual review; skip this gate only when the user explicitly waives re-review.
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
- Do not write an unverified `delivery.implemented.target`. A target is a claim about the code and needs **two code checks**: ① the implementing symbol is defined; ② a reference/usage search (findReferences or call-site grep) confirms where the unit is **actually mounted/instantiated**. Declaring `implemented` with an unverified target is a forged truth, on the same level as a hand-drawn icon — including targets copied from memory or inherited from an older contract.
- Do not claim `frozen` / 1:1 fidelity from validator `OK` alone — `OK` means schema passed; browser-hydrated default preview and scope alignment are also required before calling the contract frozen.

## Locate: requirement lookup and implementation lookup

Before deciding to create or patch, run an implementation lookup: check whether a matching `ui-contract.html` already exists for this unit.

- Prefer an explicit path the user or the requirement-slice already names.
- **Route by the in-scope artifact's physical Figma container, not by the requirement's owning route.** A tiny change (red dot, badge, single control) often physically lives inside another unit's `source_node` subtree — e.g. an unread badge on a shared tab bar, a disabled state on a button inside an existing page. In that case **patch** the contract whose `unit.source_node` contains the artifact, even if the requirement nominally belongs to a different route. Routing by requirement-route here would fork the artifact into the wrong contract and fragment the shared component's truth. If no such contract exists yet, create a `component` for the artifact subtree only (see Quick Reference) — never a whole-page stand-in.
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

**Rebuild/split metadata rule:** mechanical transfer governs DOM, never metadata assertions. When rebuilding or splitting an existing contract, a `delivery` object inherited from the old contract must be **re-verified against the current code** (§8 two-step target check) before it is carried over; otherwise reset `delivery.status` to the pre-implementation value (e.g. `"frozen"`) and drop `implemented` — re-fill it after the new implementation is located.

## Workflow

### 1. Confirm upstream, scope inventory, and locate

Read the requirement-slice **In Scope** / **Out of Scope** (or equivalent) and build a short **scope inventory** before touching design data:

1. **Must-freeze artifacts** — every visual product the slice accepts (components, tips, CTAs, sheets…).
2. **Context-only chrome** — surrounding page pieces useful for orientation but not accepted against.
3. **Ignored** — notes, annotations, device chrome.

Then run the Locate step above. Record the decision (create / incremental patch / rebuild) before querying TemPad.

Contract `unit.source_node` / `source.root_node` must be the **minimal ancestor covering the must-freeze artifacts that belong to this one unit** — never default to the full-screen page frame when the slice only hits a subtree. **If the must-freeze artifacts are disconnected** (smallest common ancestor is the whole page), do not enlarge one unit's root to swallow them all: split into multiple `component` / `modal` units and give each its own local minimal-ancestor root. The "smallest ancestor" rule is per-unit, never per-requirement-global. Artifacts that share one local subtree (e.g. red-bang + tip under the same message-row cluster) stay **one** unit — split only when clusters are disconnected.

### 1b. Unit Split Plan (REQUIRED before any `get_code` or HTML)

Publish this plan in the session (chat is enough — do **not** create a companion mapping file) and do not copy the template until every must-freeze artifact has a row:

```
| artifact (node id + label) | unit id | type (page\|component\|modal\|shared-component) | action (create\|patch\|rebuild) | source_node (scoped root) | states (or "element-patch") | dynamics (static \| content-bound \| variant \| motion \| animation-asset) | get_code target (= source_node) |
```

Rules for filling the plan:
- Match the Quick Reference row for the requirement size first.
- `get_code target` **must equal** that unit's `source_node`. Never list the full-screen page as `get_code target` "for context" when the unit is a subtree.
- Connected artifacts under one local ancestor → one row / one unit. Disconnected artifacts → multiple rows.
- Tiny badge with no container contract → `type=component`, `source_node`=badge minimal ancestor — not a new shell `page`/`shared-component`.

### 2. Enumerate frames to classify — not to freeze

**Enumerate frames to discover states and overlays**, not to decide contract scope. Query the parent/selection only long enough to list sibling frames (id, name, type, position) that might be states/modals of the units already planned in §1b. Skipping discovery still causes missed states — but **enumeration never expands freeze scope beyond the Unit Split Plan**. Frames that are not states of a planned unit are `context` or `ignore`, not new acceptance units.

Classify each frame:

| Classification | Meaning | Action |
|---|---|---|
| `page` | A full-screen **route** change that is itself in In Scope | One `ui-contract.html` with `unit.type: "page"` |
| `component` | A requirement-scoped subtree / control / tip / inline module (not a full route) | One `ui-contract.html` with `unit.type: "component"` — prefer this over copying the whole page |
| `page-state` / `component-state` | An alternative state of an already-classified unit (loading, empty, error, selected, unselected) | A `<template data-ui-state>` block inside that unit's file — do NOT create a separate contract |
| `modal` | A modal dialog, bottom sheet, popover, or overlay | One `ui-contract.html` with `unit.type: "modal"` — never nested inside a page |
| `shared-component` | A shared navigation shell, tab bar, or persistent frame wrapping pages | One `ui-contract.html` with `unit.type: "shared-component"`; referenced via `unit.dependencies` from pages that use it |
| `context` | Page chrome needed only to locate the in-scope subtree | Omit from acceptance DOM, or include with `data-ui-scope="context"` — never treat as freeze truth |
| `ignore` | Non-UI content (unrelated designer credit, version stamps) or out-of-scope chrome | Exclude from contracts entirely |
| `dynamics-hint` | Designer **TEXT / sticky / callout** describing motion, placeholders, or off-Figma resources — **including notes that are siblings of the unit frames on the parent SECTION**, not nested in `source_node` | **Not** frozen as UI truth — feed §2c; cite `hint_node` + verbatim **full** text; map to target UI node / transition |

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

### 2c. Dynamics & motion scan (REQUIRED per unit, after §2 frame list)

Before the first `get_code` for this unit:

0. **Text-hint sweep (do this even when layers look messy)** — list every TEXT / sticky / callout whose copy **or layer name** matches dynamics keywords. Sweep **two rings**, not only the freeze root:
   1. **Scoped subtree** (`unit.source_node` and each state `source_node`).
   2. **Parent canvas / SECTION siblings (REQUIRED)** — designer notes often sit **outside** the unit root as siblings of the page frames (same SECTION / parent FRAME, not nested under `source_node`). `get_structure` the parent SECTION (or the smallest common ancestor that also contains the unit frames) at shallow depth and collect TEXT / sticky / callout children that are **not** inside any `source_node`. Spatial proximity (near the unit frames), arrows, or copy that names a unit state (load complete, transition, typewriter) maps the hint to this unit.
   - Keywords (match equivalent wording in the designer's language), e.g.: motion, animation, transition, typewriter, shimmer, Lottie, GIF, video, skeleton, placeholder, sample image, API-returned, asset attached separately, send later, external link, pulse, loading
   - Classify each as `dynamics-hint` (§2 table); record `hint_node`, **verbatim full** `hint_text` (do not truncate multi-line notes), and your best **target UI node** hypothesis.
   - A hint that describes a **state-to-state transition** (e.g. after loading completes…) is `prototype-transition`, **not** a per-state loop. Do not replay it on every state template.
   - If one hint could attach to multiple UI nodes **or** multiple units → **stop and ask the user** before freezing.
   - Do **not** mark these canvas notes `ignore` just because they are outside `source_node`.
1. **Candidate sweep** — on the unit's scoped `source_node`, use `get_structure` (and requirement-slice keywords: avatar, animation, Lottie, GIF, skeleton, loading, pulse, badge count…) to list nodes that are likely dynamic:
   - `INSTANCE` / `COMPONENT` with variant siblings or property-like frame names (when present — **absence of variants does not mean static**)
   - Image fills on user/content fields (avatar, cover, UGC)
   - Layers named like `animate`, `lottie`, `gif`, `motion`, `loading`, `skeleton` (bonus signal only)
2. **Motion probe** — for each candidate (including text-hint targets), when figma-bridge MCP is available call `get_node_motion` on the node id. Record `animationStyles`, `manualKeyframeTracks`, and timeline hints. TemPad-only: record "motion: not probed (no figma-bridge)" — **text hints and requirement slice still count**.
3. **Design animation assets** — when `get_code` or designer exports expose Lottie/GIF/video/sprite bytes, **persist** under the project asset directory and set `asset_status: "resolved"` with path + hash. When hints/requirements mention an asset but **Figma has no bytes** → `asset_status: "pending-user"`, `design_asset: null`, poster frame only — **do not invent the file**.
4. **Classify** each row with the taxonomy table (`content-bound`, `component-variant`, `motion-preset`, `design-animation-asset`, `prototype-transition`) and set `evidence_source`.
5. **Map to contract artifacts:**
   - Variant values that change the whole unit → additional `meta.states[]` entries **and** `component-variant` dynamics linking state id ↔ property values.
   - Time-based effects → static **poster** frame in HTML + `motion-preset` or `design-animation-asset` entry; implementation replays the asset at runtime.
   - Content fields → placeholder DOM + `content-bound` with `implementation_notes` naming the API/binding field.

Publish a **Dynamics inventory** in chat (no side file) **and** mirror motion rows into the review-panel **Motion and transitions** table before HTML authoring:

```
| dynamic-id | target node | kind | evidence_source | hint (if any) | asset_status | static preview | implementation hint |
```

Chat inventory alone is **not** sufficient for user audit — reviewers open the HTML, not the session log.

If the unit has no dynamic behavior after **steps 0–1 and requirement pass**, set `"dynamics": []` and write `none — static Figma snapshots only` in the review panel.

### 2d. Missing-resource escalation (REQUIRED before freeze)

When any dynamics row or asset note has `asset_status: "pending-user"` (or `pending:` in review panel), **stop and message the user** with a structured request before claiming frozen — unless they already waived in this session.

Write the request in the **user's language**. English skeleton (translate before sending):

```
[ui-truth-mapping pending assets] <unit-id>
These items have motion or resource notes in Figma/requirements, but no usable file in the repo yet. Provide the asset or an explicit waiver before freeze:

1. <dynamic-id> — <kind>
   - Evidence: <evidence_source> / verbatim: "<hint_text>"
   - Related node: <figma_node>
   - Need: <.json|.gif|.mp4|… or in-repo path>
   - Contract now: static poster frame / placeholder geometry only

(repeat for each item)
```

After the user provides a file: persist it, update `design_asset`, set `asset_status: "resolved"`, re-run validator. After explicit waiver: set `asset_status: "waived"` and quote the waiver in `[data-ui-dynamics-inventory]`.

**Dispatch:** for more than one independent unit, spawn a per-unit subagent so evidence gathering and DOM authoring stay isolated — no cross-unit contamination. Skip subagent dispatch only when the user explicitly requests no subagent usage, or there is exactly one unit with ≤2 states.

### 3. Gather minimal TemPad evidence *(runs inside per-unit subagent when dispatched)*

For each **planned unit** (and each of its state frames), one at a time:

1. Call `get_code` on that unit's **scoped** `source_node` / state `source_node` from the Unit Split Plan — never on the full-screen page "to prune later". Full-page `get_code` then carve-down is a process failure even if you mark leftovers `context`.
2. Transfer only the markup returned for that scoped node into the unit's `<template>`. Do not paste a whole-page DOM dump and delete/hide siblings.
3. Call `get_structure` on the same scoped node only when hierarchy, geometry, or overlap remains ambiguous after `get_code`. Do not call it by default.
4. Record every `data-figma-node` you intend to cite before writing DOM — no node id may be invented.
5. **Resolve every asset reference** returned by `get_code` (`<svg data-src="...">`, image fills, asset URLs) before writing DOM. For each one:
   1. **Classify first:** static design icon, **dynamic content** (`content-bound`), **component variant**, or **motion/animation asset**? Requirement context + §2c inventory decide — the Figma picture may be only an example or a static keyframe. Dynamic content → placeholder + `content-bound` dynamic entry; motion → poster frame + `design-animation-asset` / `motion-preset`.
   2. **Reuse check:** search the target project's existing asset directories (whatever layout that project uses) for the same icon. If it exists → reference it and record the existing asset path in the review panel instead of duplicating bytes.
   3. **Simple vector** → fetch the asset bytes and inline the SVG verbatim into the contract, annotated with the asset hash. Treat every asset URL as **ephemeral** (some TemPad environments serve assets from a temporary local server that dies after the session) — persist the bytes now, never reference the URL later.
   4. **Complex/raster asset** → download the original image and persist it into the project asset directory; reference the persisted path in the contract (a project-root-relative path, never an asset URL).
   5. **Cannot fetch** (MCP returns no bytes, fetch fails, format unsupported) → record it as a pending item in the review panel and raise it to the user for a decision (provide the asset, substitute, or defer); if it blocks freezing, record `blocked_missing_visual_truth` (key asset). Do **not** redraw it as a fallback — guess-drawing an icon is a process failure. If a `data-src` shell must stay in the contract for a deferred asset, it must carry `data-ui-asset` metadata — the validator rejects any `data-src` element without it.

   Note: `get_code` may return an entire subtree as **one** vector asset (e.g. a sheet drag handle). The asset bytes are the only complete truth — do not reconstruct child elements from `get_structure`, which carries geometry but silently loses paint attributes (fill-opacity, gradients, strokes).

### 4. Copy the template verbatim (create) or open the matched file (patch)

**Create:** locate `templates/ui-contract-template.html` and copy it verbatim to `<output-dir>/<unit-id>/ui-contract.html`. All four regions (`#ui-contract-meta`, `<style>`, `<main data-ui-contract>`, `[data-ui-review-panel]`) stay intact; keep `[data-ui-state-switcher]`, `[data-ui-state-host]`, and `script[data-ui-state-preview]` from the template; never add a fifth free-form region.

**Incremental patch:** open the located file directly. Do not recopy the template over an existing contract. If the matched file lacks the preview infrastructure (older v2 file or pre-preview draft), backfill it in this order without rewriting unrelated truth DOM:
1. Move existing truth-bearing DOM (every `data-ui-id` subtree) into a new `<template data-ui-state="default">` inside `<main>`. This is a structural relocation, not a rewrite — preserve nodes, attributes, and order verbatim.
2. Add empty `[data-ui-state-host]` and `[data-ui-state-switcher]` from the current template, and copy `script[data-ui-state-preview]` verbatim.
3. Backfill `meta.states` with one entry `{ "id": "default", "source_node": <unit.source_node>, "default": true }` and set `data-ui-state-default="default"` on `<main>`.
4. Leave the four regions intact; do not introduce a fifth.

### 5. Fill or patch the one-unit HTML

- `#ui-contract-meta` — fill `schema_version: 2`, `contract_id`, `source` (`requirement`/`design_file`/`root_node`), `unit` (`id`/`type`/`title`/`route_or_trigger`/`requirements`/`source_node`/`dependencies`), `states` (one entry per frame, exactly one `default: true`), optional `dynamics` (array from §2c; `[]` when static), `revision`, `delivery.status`. `unit.type` is `page` | `modal` | `shared-component` | `component`. `unit.source_node` is the scoped root from §1. **State ids must be kebab-case lowercase ASCII** (`^[a-z][a-z0-9-]*$`, e.g. `loading`, `empty-state`) — the preview script builds CSS selectors from state ids and breaks on spaces, quotes, or brackets. **Default state** = the state a reviewer sees on first page load (typically `loaded`/`success`, not transient `loading`/`error`), so the hydrated preview matches the screen's primary visual, not a flicker frame.
- `<style>` — **mechanical transfer** of evidence-backed CSS from `get_code` (including geometry: width/height, position, inset, gap, padding, margin, display, flex/grid, z-index, typography, color). Prefer `var(--token)` when TemPad returns a canonical token binding; otherwise keep the literal value TemPad returned. Do not replace get_code layout with a rewritten semantic stylesheet.
- `<main data-ui-contract>` —
  - Keep `[data-ui-state-switcher]` and empty `[data-ui-state-host]`.
  - Put **every** declared state (including default) into `<template data-ui-state="<id>">`. Transfer get_code DOM into the template; only add annotation attributes.
  - Shared identical chrome across all states may sit outside the host **only** when it is in scope and identical across every state; otherwise duplicate it inside each state template.
  - Out-of-scope positioning chrome (context) may sit outside the host to preserve geometry, but must be marked `data-ui-scope="context"` and must **not** carry `data-ui-id` / `data-ui-kind` / `data-figma-node`. Context is not truth; the validator rejects truth-annotated context.
  - `data-ui-unit-id`/`data-ui-unit-type`/`data-ui-state-default` on `<main>` must match meta.
  - Every truth-bearing element carries unique `data-ui-id`, `data-ui-kind`, and `data-figma-node`.
  - Nodes listed in `meta.dynamics[]` also carry `data-ui-dynamic="<kind>"` and `data-ui-dynamic-id="<dynamics[].id>"` when they appear in the frozen DOM.
  - Keep `script[data-ui-state-preview]` verbatim so open-in-browser hydrates the default state and enables switching.
- `[data-ui-review-panel]` — human-readable audit sections in the **user's language** (see “Two acceptance surfaces”):
  - `<summary>` — local equivalent of `Review notes (not product UI)` (template English is an example, not a language lock).
  - `dt[data-ui-scope="in_scope"]` — **what the canvas accepts** (short labels; Figma node ids optional in `dd`).
  - `dt[data-ui-scope="out_of_scope"]` — what is explicitly not accepted here (outer shell, real Spine/Lottie runtime, etc.).
  - **When motion dynamics exist:** plain `dt` + `dd` with **Motion and transitions** `<table class="effect-table">` (columns equivalent to State | Where | Effect | Reference, in the user's language). Lead sentence: motion and transitions, not data binding.
  - `dt[data-ui-asset-inventory]` — every icon/image resolution (inline hash, reused path, placeholder, pending).
  - `dt[data-ui-dynamics-inventory]` — mirrors `meta.dynamics[]` (or points to the table above); `none — static Figma snapshots only` when `dynamics` is `[]`; list every `pending-user` item explicitly.
  - `dt[data-ui-evidence-for]` — **Canvas placeholder / Copy** for `inferred` nodes and `content-bound` fields; merge duplicate pet/avatar placeholder notes when possible (hidden duplicate `dt` entries are OK if the validator requires one `data-ui-evidence-for` per `inferred` id).
  - Style the panel for readability: `[data-ui-review-panel]` spacing, `.effect-table` borders, `.tag-motion` / `.tag-static` for effect types — copy patterns from `templates/ui-contract-template.html`.
  - Every `data-figma-node` cited in `in_scope` must still appear on a non-context DOM node (validator cross-check).
- Incremental patch: touch only the subtree, states, and metadata fields the requirement actually changes. Leave unrelated `data-ui-id` subtrees, unrelated states, and other units' `unit.dependencies` untouched.

Process one frame at a time — never batch every frame into a single query or a single edit pass.

### 6. Browser review

Open the contract HTML in a browser (or the IDE's rendered preview). The preview script must hydrate the default state into `[data-ui-state-host]` without opening the review panel:

- Confirm the **hydrated default** layout matches the Figma scoped root (geometry + content), not an empty host or a hand-rewritten approximation.
- If the host looks blank: check (1) preview script present, (2) default template non-empty, (3) `--color-text` / `--color-surface` are real CSS colors (never the invalid token `#PLACEHOLDER`), and (4) `html, body` keep the template's light preview base — IDE dark canvases otherwise show black text on a transparent page. Overwrite tokens with evidence colors, not placeholder strings.
- Use `[data-ui-state-switcher]` to step through **every** declared state; each activated host contents must match its source frame.
- Compare **every icon/image** against its evidence: inlined bytes must match the fetched asset payload; reused assets must match the project file; server-provided placeholders must visibly be placeholders. A "looks like the right icon" redraw fails this check even when geometry is perfect.
- Expand `[data-ui-review-panel]` and confirm scope inventory, asset notes, every cited `data-figma-node`, and inference notes are legible and accurate.
- When `meta.dynamics[]` has motion entries: confirm the **Motion and transitions** table is present, lists every motion the requirement expects, and explicitly states it is **not** a data-binding spec.
- The hydrated HTML **is** the review medium. Do not generate or save preview screenshot artifacts (no `contract-preview-*.png` etc.) — humans review the HTML directly, and screenshots drift from the contract.
- Never assume "validator OK ⇒ looks like Figma."
- **User confirmation gate:** present each contract to the user for manual confirmation (path + how to open it + review-panel summary). When motion dynamics exist, **call out the Motion and transitions table by name** and ask the user to confirm those effects — not only static layout. If §2d applied, include the pending-resource list (resolved / still waiting / waived). Do not declare the contract frozen until the user explicitly confirms it — unless the user has explicitly waived re-review for this run. **Do not treat confirmation as a substitute for providing missing assets** — waiving assets must be explicit.

### 7. Run the validator

From the delivery project / kit root (the directory that contains `scripts/validate-ui-contract-html.py`):

```bash
python3 scripts/validate-ui-contract-html.py <path-to-ui-contract.html>
```

Only continue when it prints `OK`. On failure, fix the contract and re-run — never claim `acceptance_frozen` on a failing contract. Validator `OK` is necessary but not sufficient: browser-hydrated default preview and requirement-scope alignment from §1/§1b/§6 are still required before freezing.

**What the validator checks automatically:** schema/DOM structure, single unit root, `data-ui-id` uniqueness + `data-figma-node`/`data-ui-kind` presence (placeholder figma nodes rejected), preview infrastructure present, **every** state template non-empty with visible text/media, `in_scope`/`out_of_scope` inventory present, **in_scope node ids cross-checked against `data-figma-node` values frozen in the DOM**, context chrome not truth-annotated, inference notes back every `data-evidence="inferred"`, `data-src` asset shells carry `data-ui-asset` metadata, delivery fields.

**What the validator cannot check (remain §6 process checks):** `unit.source_node` minimality (no Figma tree access — you must verify the scoped root is the local minimal ancestor, not the full page), layout fidelity to Figma (mechanical transfer vs hand-authored rewrite), **icon asset fidelity** (SVG paths vs fetched asset bytes — the validator cannot see Figma assets), browser hydration fidelity (open it and look), and semantic correctness of state/default choices. `OK` ≠ "looks like Figma" and ≠ "scope matches the slice" — those are human/§6 gates.

### 8. After implementation — backfill delivery and revalidate

Once the unit is implemented, edit the same file's `#ui-contract-meta`:

- set `delivery.status` to `"implemented"` (or `"merged"` once merged);
- fill `delivery.implemented`: `type`, `target` (code location), `requirement`, `version`, `status`.

**Verify `target` before writing it** — two mandatory code checks, run against the current codebase:

1. **Definition check:** confirm the implementing symbol(s) exist (class/widget/component definition).
2. **Reference check:** run a reference/usage search (findReferences, or grep for instantiations/call sites) to locate where the unit is **actually mounted or instantiated**. The mount site is the target — even when it differs from the definition file. A definition-only check is not sufficient (a symbol can be defined in one file and mounted in another).

Write the verified location(s) into `target` (both definition and mount file when they differ). Never fill a target from memory, and never carry one over from a superseded contract without re-running both checks; if the implementation cannot be located yet, keep `delivery.status` at the pre-implementation value instead of guessing a target to complete the object.

Re-run the validator — it enforces that `delivery.implemented` is complete whenever `delivery.status` is `"implemented"` or `"merged"`. Do not create a separate implementation-tracking file; this backfill inside the same HTML is the only implementation record.

### 9. Replace or deprecate — sweep stale pointers in the same change

There is no aggregate index file, so pointers to a contract live scattered across the requirement directory (`status.json` notes, `visual-acceptance.md`, progress/todo records, breakdown summaries). When a contract is **deleted, replaced, or rebuilt under a changed unit id**, the change is not complete until the references are swept:

1. Scan the requirement directory (`.ai-delivery/requirements/<req-id>/`) for every reference to the old unit id / old contract path.
2. Redirect every **active** pointer (`status.json` notes, `visual-acceptance.md` Contract entries, progress/todo, breakdown summaries) to the new contract path / unit id.
3. One historical note line is allowed ("deleted / superseded by `<new unit id>`") — but no active pointer may keep targeting a contract file that no longer exists.
4. Where available, run the requirement status validator (`scripts/validate-delivery-status.py <status.json> --req-root <req-dir>`); it rejects dangling `ui-contract.html` pointers mechanically.

## Component Type Vocabulary

`container`, `card`, `list`, `list-item`, `form`, `text`, `text-input`, `button`, `image`, `icon`, `tab`, `navigation`, `divider`, `badge`, `modal`, `sheet`, `toast`, `custom`

## Anti-patterns (treat as process failure)

- Writing a companion YAML, JSON, or markdown file to hold UI truth alongside `ui-contract.html`.
- **Whole-page dump** of a Figma screen when the slice In Scope only hits a local subtree (reject tip, sheet, badge…).
- **Full-page `get_code` then prune** (or "transfer all, mark leftovers context") instead of calling `get_code` on each planned unit's scoped `source_node`.
- **Skipping the §1b Unit Split Plan** and jumping straight from a whole-page Figma selection into template authoring.
- **Collapsing disconnected in-scope artifacts into one whole-page contract** (root = full screen) instead of splitting them into per-cluster `component` / `modal` units with local minimal-ancestor roots.
- Skipping the §1 scope inventory / §1b plan and freezing unrelated nav / list / composer chrome as acceptance truth.
- **Routing a tiny change (red dot, badge, disabled state) by the requirement's owning route** instead of by the artifact's physical Figma container, forking the artifact into the wrong contract.
- **Inventing a brand-new full `shared-component` / `page` dump** of surrounding chrome solely to host a tiny in-scope artifact when no matching container contract exists — create a scoped `component` instead (or patch an existing container contract).
- **Truth-annotating context chrome** (`data-ui-scope="context"` with `data-ui-id` / `data-ui-kind` / `data-figma-node`) — context is positioning only.
- **Spawning a unit-level state template for a single element's property variant** (button `disabled`, input `readonly`) instead of patching that element's attributes.
- **Putting the modal's trigger button inside the modal contract** instead of patching it into the button's physical container contract.
- Hand-authoring a semantic flex/grid layout instead of mechanically transferring `get_code` geometry.
- **Hand-authoring an icon or image glyph** (redrawing a "close enough" SVG) instead of transferring the design asset bytes or reusing an existing project asset.
- Leaving a `get_code` asset shell (`data-src` / asset URL) unresolved in the frozen contract — asset bytes must be inlined or persisted into the project, with the asset hash noted.
- Reconstructing an asset-shell subtree (a subtree `get_code` exports as one SVG asset, e.g. a drag handle) from `get_structure` geometry and silently dropping paint attributes (fill-opacity, gradient, stroke) — structure is geometry-only evidence.
- Downloading a Figma **example** image as a frozen asset when the requirement context shows the content is server-provided (avatar, user upload, dynamic badge).
- Skipping §2c and leaving `dynamics` undocumented when COMPONENT variants or motion layers are in scope.
- Skipping §2c step 0 (text-hint sweep) because layer names are messy or absent.
- **Scoping the text-hint sweep only to `source_node`** and missing SECTION-level notes / sticky siblings that describe a transition animation for that unit.
- Truncating a multi-line Figma motion note (first line only) instead of recording the full `hint_text`.
- Putting a transition animation (loading→success typewriter / stagger fade) on **every** state template as if it were a per-state loop.
- Review-panel Motion and transitions table present but `meta.dynamics` omitted or `[]`.
- Treating designer callout copy as `ignore` when it describes motion or off-Figma resources.
- Hand-animating in the contract HTML instead of specifying `design-animation-asset` + poster frame (CSS **motion preview hints** with review-panel disclaimer are OK).
- Putting field-binding / API mapping tables on the canvas or above `[data-ui-state-host]`.
- Surfacing §2c motion inventory only in chat while the review panel lacks a **Motion and transitions** table.
- Conflating **motion / UI effects** with **content-bound** data filling in one undifferentiated “dynamic” section.
- Malforming `[data-ui-state-host]` (`data-ui-state-host">`) so hydration fails and the canvas looks broken.
- Using `1:1` in review-panel copy where the validator will mis-read it as a Figma node id.
- Freezing with `pending-user` assets without §2d escalation or explicit user waiver.
- Silently redrawing an unfetchable asset instead of recording a pending item and asking the user to provide it.
- Saving preview screenshots (`contract-preview-*.png` etc.) as delivery artifacts — the hydrated HTML is the review medium.
- Declaring a contract frozen without explicit per-contract user confirmation (unless the user explicitly waived re-review).
- Writing `delivery.implemented.target` from memory or inheriting it from a superseded contract without re-verifying it against the current code.
- Backfilling `target` after a definition-only check — a reference/usage search must first confirm the actual mount/instantiation file, and both locations belong in `target` when they differ.
- Deleting or rebuilding a contract (unit id change) without sweeping the requirement directory for stale pointers — active references in `status.json` notes, `visual-acceptance.md`, progress/todo, or breakdown summaries must be redirected in the same change.
- Putting default (or any) state only in `<template>` and deleting/omitting `script[data-ui-state-preview]` so the browser shows an empty host.
- Claiming browser default-state review without hydration / switcher working, or without stepping through **every** declared state.
- Modeling status bars, navigation bars, keyboards, or device chrome as `data-ui-kind` content instead of using CSS safe-area handling.
- Using `data-evidence="inferred"` with no matching review-panel note.
- Leaving template `PLACEHOLDER-*` values in `data-figma-node` or `unit.source_node` (validator rejects placeholder figma nodes; source_node minimality is a §6 process check).
- Scanning every historical contract file to "find" a unit instead of using requirement id, semantics, or an explicit user-specified path.
- Rewriting an entire matched contract for a small requirement instead of an incremental patch.
- Claiming `acceptance_frozen`/`frozen`/`implemented`/`merged` from validator `OK` alone without hydrated preview + scope alignment.
- Hand-authoring DOM structure without copying the template first.
