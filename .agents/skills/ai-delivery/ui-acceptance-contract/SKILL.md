---
name: ui-acceptance-contract
description: Use when a UI-bearing sub-requirement already has governed requirement and design mapping artifacts, plus API artifacts when they materially affect the frozen screen contract, and must freeze immutable YAML UI acceptance truth before interaction design, Spec Kit, or implementation.
---

# UI Acceptance Contract

Project-local workflow skill for freezing screen, state, component, layout, and visual-style acceptance truth into a governed YAML artifact inside the host repository.

## Overview

Use this skill after `ui-requirement-mapping` when a UI-bearing sub-requirement already has requirement truth, trustworthy structured design evidence, and API contract truth when that API truth materially changes the executable screen-state contract. This stage writes `ui-acceptance-contract.yaml`, updates `traceability.json.ui_acceptance_contract` in place, and advances `status.json` to `acceptance_frozen` only when the YAML UI truth tree is truly ready.

`ui-acceptance-contract.yaml` is the only canonical UI acceptance truth. Do not create, update, or rely on a Markdown acceptance-contract artifact. Older Markdown acceptance contracts are obsolete and should be removed or replaced with the YAML contract rather than kept as compatibility inputs.

This skill separates two concerns:

- `figma-mapping.md` proves the requirement was bound to structured design evidence.
- `ui-acceptance-contract.yaml` freezes the immutable screen-state UI truth tree that downstream interaction design, Spec Kit, visual acceptance, and implementation must consume without reinterpreting visual truth.

## Hard Boundary

- Do not invent visual truth.
- Do not invent business flow, permission rules, navigation, or API semantics.
- Do not use a top-level `SECTION` as a frozen executable frame target.
- Do not treat `get_structure` as sufficient screen-state truth when `get_code` is still missing.
- Do not overwrite `figma-mapping.md`, `api-contract-mapping.md`, or `interaction-design.md`.
- Do not replace `traceability.json` with a sidecar note or second bridge artifact.
- Do not create a second UI acceptance source beside `ui-acceptance-contract.yaml`.
- Do not hand-edit blocked states to look recovered.

If a required screen state, executable frame, component tree branch, layout, visual style, icon asset, or other 1:1-impacting UI truth cannot be supported by trustworthy evidence, stop and block instead of pushing uncertain truth downstream.

## Use This Skill For

- Freezing immutable screen-state acceptance truth for UI-bearing sub-requirements.
- Writing `ui-acceptance-contract.yaml`.
- Updating `traceability.json.ui_acceptance_contract`.
- Moving a UI-bearing sub-requirement to `acceptance_frozen` when the YAML contract is source-backed.
- Recording 1:1 visual blockers before interaction design, Spec Kit, TDD, or implementation.
- Freezing component tree, layout, box model, component type, typography, icon, image, state, and implementation-mapping truth.

## Do Not Use This Skill For

- Requirement splitting.
- API contract discovery.
- Figma evidence discovery.
- Interaction design.
- Spec Kit generation.
- Implementation code or visual tuning by guesswork.

## Required References

- [Dual Truth Rules](references/dual-truth-rules.md)
- [Blocker Catalog](references/blocker-catalog.md)
- [Logging Checklist](references/logging-checklist.md)
- [UI Acceptance Contract Template](templates/ui-acceptance-contract-template.yaml)

Also match the governed artifact shapes already established under `.ai-delivery/requirements/` instead of inventing a parallel acceptance store.

## Inputs

### Required Inputs

- `subreq-id`
- `requirement-slice.md`
- `figma-mapping.md`
- trustworthy `get_code` evidence for every final executable screen state

### Expected Supporting Inputs

- `api-contract-mapping.md` when action semantics already exist and materially affect the frozen screen contract
- token artifacts from Figma, Tempad, or the compatible structured design provider
- downloaded image or icon assets when the design requires special UI-provided assets
- existing code component props when a preferred implementation component is named or already established
- `traceability.json`
- `status.json`
- `decisions.md`

### Missing Input Handling

If a source or artifact is missing:

- If `requirement-slice.md` is missing or not safe enough to consume, stop and hand work back to `requirement-breakdown`.
- If `figma-mapping.md` is missing or is not backed by trustworthy structured evidence, stop and hand work back to `ui-requirement-mapping`.
- If any required final screen state lacks trustworthy `get_code` evidence, block on `blocked_verification_failure`.
- If a critical 1:1 visual truth gap remains unresolved, block on `blocked_missing_design`.
- If Requirement truth and Figma truth conflict inside the executable screen contract, block on `blocked_requirement_figma_conflict`.
- If API truth is incomplete but does not change the frozen screen-state contract, keep that gap explicit for later interaction or integration work instead of blocking acceptance on API completeness alone.
- If a special UI-provided icon is required and the icon can be downloaded from MCP or another trusted structured provider, download and reference that asset in the YAML contract.
- If a special UI-provided icon is required but cannot be downloaded or otherwise source-backed, block acceptance until the user provides the icon asset or a retrievable design source.
- If `traceability.json` is missing in a legacy folder, repair only the governed contract and record the repair in `decisions.md`.

## Output Goal

Produce an acceptance package that downstream stages can consume directly without reinterpreting visual truth. The output must preserve:

- a source-backed `ui-acceptance-contract.yaml`
- an updated `traceability.json.ui_acceptance_contract` subtree whose path points to the YAML file
- existing non-acceptance traceability fields such as `requirement_refs`, `api_contract_mapping`, `figma_nodes`, and `spec_kit_refs`
- explicit `screen_states`, nested `component_tree`, `verification_targets`, `unresolved_ui_truth`, and frozen screen-state boundaries

## Default Output Paths

```text
.ai-delivery/requirements/<requirement-id>/sub-requirements/<subreq-id>/
├── ui-acceptance-contract.yaml
├── traceability.json
├── status.json
└── decisions.md
```

## Canonical YAML Shape

The contract is a tree rooted at `screen_states`. Each screen state owns one `component_tree`, and every component node carries the UI truth needed to implement and verify it in place.

Required top-level keys:

- `version`
- `updated_at`
- `updated_by`
- `contract`
- `spacing_policy`
- `screen_states`
- `verification_targets`
- `unresolved_ui_truth`

Required `contract` keys:

- `id`
- `status`
- `source_requirements`
- `source_design`
- `api_dependency`

Each `screen_states[*].component_tree` node should include the fields that apply to that component:

- `component_id`
- `node_id`
- `component_type`
- `role`
- `required`
- `layout`
- `box_model`
- `size`
- `component_props`
- `visual_style`
- `content`
- `typography`
- `icon`
- `image`
- `states`
- `implementation_mapping`
- `source_refs`
- `blocking_unknowns`
- `children`

Keep related truth next to the node it governs. Do not split required elements, layout constraints, typography, and component props into separate tables that downstream readers must mentally join.

## Component Tree Contract

Freeze every final screen state's UI hierarchy as a nested tree.

- The root of each state is `screen_states[*].component_tree`.
- Each component node must name its `component_id`, `node_id`, `component_type`, `role`, `required`, and `children`.
- `children` must preserve source-backed visual hierarchy and order.
- Parent, companion, and shared UI relationships may be represented with node-local `source_refs`, `role`, or `implementation_mapping`, but the acceptance truth must still be readable from the tree itself.
- Use stable, implementation-friendly `component_id` values, but do not let invented ids replace the source `node_id`.

Component type vocabulary should be specific enough to guide implementation:

- `screen`
- `container`
- `card`
- `list`
- `list-item`
- `form`
- `text`
- `text-input`
- `button`
- `image`
- `icon`
- `tab`
- `navigation`
- `divider`
- `badge`
- `modal`
- `sheet`
- `toast`
- `custom`

If no listed type fits, use `custom` and explain the source-backed reason in `component_props.custom`.

## Layout Contract

Every non-trivial component must freeze layout behavior, not just visual order.

Record the applicable fields under `layout`:

- `mode`: `vertical-stack`, `horizontal-stack`, `grid`, `absolute`, `overlay`, `list`, `leaf`, or another source-backed mode.
- `primary_axis`
- `cross_axis_alignment`
- `main_axis_alignment`
- `gap`
- `wrap`
- `positioning`
- `constraints`

Record the applicable fields under `size`:

- `width`
- `height`
- `width_behavior`
- `height_behavior`
- `min_width`
- `max_width`
- `min_height`
- `max_height`
- `aspect_ratio`

If auto-layout, flex, grid, or absolute positioning can produce visually similar results, choose the mode that best matches source evidence and component responsibility. Record the decision in `layout.notes` or `box_model.spacing_semantics`.

## Box Model And Spacing Policy

The YAML must include a top-level `spacing_policy`:

```yaml
spacing_policy:
  padding: "Use for internal container breathing room."
  gap: "Use for sibling spacing owned by parent layout."
  margin: "Use only for external placement when parent layout cannot own spacing."
  equivalent_visuals_rule: "If padding and margin can create the same visual result, choose the semantic owner that best matches component responsibility and record that decision."
```

Every component node that affects layout must include `box_model`:

- `padding.top`
- `padding.right`
- `padding.bottom`
- `padding.left`
- `margin.top`
- `margin.right`
- `margin.bottom`
- `margin.left`
- `spacing_semantics`

Spacing ownership rules:

- Container internal breathing room should be `padding`.
- Sibling spacing should be parent-owned `gap`.
- External placement should use `margin` only when the parent layout cannot own the spacing.
- Do not interchange padding, margin, and gap merely because they produce the same pixels.
- If source evidence only gives a visual distance, the contract must choose and record the recommended implementation semantics.

## Component Property Contract

Freeze component-specific props under `component_props`. Use source evidence from `figma-mapping.md`, final-state `get_code`, design tokens, downloaded assets, and existing code component props. Do not invent missing component behavior.

Common fields by type:

- `button`: `variant`, `size`, `height`, `min_width`, `radius`, `state_coverage`, `background`, `content_complexity`.
- `text`: `font_family`, `font_size`, `font_weight`, `line_height`, `color_token`, `max_lines`, `overflow`, `text_source`.
- `list`: `item_component`, `item_spacing`, `divider`, `empty_state_component`, `scroll_behavior`.
- `image`: `aspect_ratio`, `fit`, `fallback`, `mask`, `loading_state`.
- `icon`: `size`, `stroke_width`, `color_token`, `semantic_role`, `asset_ref`, `download_status`.
- `card` or `container`: `background`, `radius`, `border`, `shadow`, `padding`, `layout_mode`.
- `text-input`: `variant`, `height`, `placeholder_source`, `value_source`, `disabled_state`, `validation_surface`.

When a project code component is the preferred implementation target, record it under `implementation_mapping` with `preferred_component`, `allowed_substitution`, and `prop_mapping`.

## Text, Icon, Image, And State Rules

Use node-local fields so each component's contract is readable without cross-table lookup.

Text truth:

- Record `content.text_source`, `content.text_value` when source-backed, `content.max_lines`, and `content.overflow`.
- Record `typography.font_family`, `font_size`, `font_weight`, `line_height`, and `color_token`.
- If text is runtime-provided, record the runtime source and still freeze max-lines and overflow behavior.

Icon truth:

- Use downloaded MCP or structured-provider assets for special UI-provided icons whenever available.
- Record `icon.asset_ref`, `icon.asset_source`, `icon.download_status`, `icon.size`, `icon.color_token`, and `icon.semantic_role`.
- If the design requires a special icon and no asset can be downloaded or verified, add a blocking `unresolved_ui_truth` item with `blocks: acceptance_frozen`.
- Generic system icons may use the existing design-system component only when the source design clearly maps to that component and no special asset is required.

Image truth:

- Record `image.asset_ref`, `image.aspect_ratio`, `image.fit`, `image.mask`, `image.fallback`, and `image.loading_state` when applicable.
- Do not substitute a placeholder image for acceptance truth unless the source explicitly defines it as a placeholder state.

State truth:

- Record `states.required_states` for visible component states such as `default`, `disabled`, `loading`, `pressed`, `error`, `empty`, or `selected`.
- Record `states.state_style_refs` for source-backed visual state evidence.
- If a required state lacks structured visual evidence, record a blocking unknown instead of inventing style.

## Visual Token And Source Contract

Every 1:1-impacting style value should be traceable:

- Figma or Tempad token
- final-state `get_code`
- downloaded asset
- design-system token
- existing code component prop
- explicit unresolved blocker

Use `source_refs` at the smallest useful scope. For component-level values, place refs on the component. For property-level values, place refs under `visual_style`, `typography`, `icon`, `image`, or `component_props`.

Do not allow fallback tokens when the source requires exact UI truth unless the contract explicitly records `fallback_allowed: true` and why that fallback does not affect 1:1 acceptance.

## Unresolved UI Truth

`unresolved_ui_truth` is for blocking or explicitly bounded UI unknowns. It must not become a soft note bucket.

Each unresolved item should include:

- `unknown`
- `affected_component`
- `impact`
- `resolution_path`
- `blocks`

Set `blocks: acceptance_frozen` when the missing truth affects 1:1 implementation or verification. Examples:

- Required component lacks final-state `get_code`.
- Component hierarchy or layout mode is ambiguous.
- Padding, margin, or gap ownership cannot be determined and affects implementation semantics.
- Required typography, token, visual style, image, or special icon asset is missing.
- Required component state lacks structured visual evidence.
- Requirement and design conflict inside the frozen screen contract.

If an API gap does not change the visible screen-state contract, do not block acceptance on API completeness alone. Record the API dependency in `contract.api_dependency` and leave action integration to later governed stages.

## Workflow

### 1. Confirm the upstream contract

- Read `requirement-slice.md`, `api-contract-mapping.md` when present and when it affects screen-state meaning, `figma-mapping.md`, `traceability.json`, `status.json`, and `decisions.md` before drafting the YAML acceptance contract.
- Prefer starting from `figma_mapped`.
- Confirm the sub-requirement is UI-bearing and that downstream execution still depends on 1:1 visual truth.

### 2. Inventory executable screen states

- Read the executable-state evidence already established upstream.
- Require a trustworthy executable frame node for every final screen state.
- Require trustworthy `get_code` evidence for every final screen state before freezing the contract.
- Record frozen state ids, parent shells, required hierarchy, component tree roots, and verification targets.

### 3. Freeze the YAML UI truth tree

- Use `templates/ui-acceptance-contract-template.yaml`.
- Write `screen_states[*].component_tree` as the primary artifact shape.
- Freeze component identity, hierarchy, layout, box model, spacing semantics, size behavior, component type, component props, typography, visual tokens, content, icons, images, states, implementation mapping, and source refs.
- Treat every 1:1-impacting unknown as either resolved or blocked.
- Do not let visual unknowns degrade into soft notes.

### 4. Update traceability and status conservatively

- Update only `traceability.json.ui_acceptance_contract`.
- Set `traceability.json.ui_acceptance_contract.path` to `ui-acceptance-contract.yaml`.
- Preserve `api_contract_mapping`, `figma_nodes`, `spec_kit_refs`, and other non-acceptance fields.
- Advance `status.json` to `acceptance_frozen` only when each frozen page-state contract is source-backed and the remaining unknowns do not compromise 1:1 delivery.
- Use the separate admin support surface only for governed logging, blocker handling, and status transitions when available.

### 5. Re-audit before handoff

- Re-open `figma-mapping.md`, `ui-acceptance-contract.yaml`, `traceability.json`, and `status.json`.
- Verify that every frozen screen state has final executable evidence and `verification_targets`.
- Verify that every component node has enough source-backed truth for 1:1 implementation at its level of responsibility.
- Verify that no visual truth was guessed or shifted into interaction design.

## State And Blocker Rules

- If a required final screen state has no trustworthy executable evidence, block on `blocked_verification_failure`.
- If a required visual carrier is missing, block on `blocked_missing_design`.
- If requirement, API, and visual truth conflict in a way that changes the executable screen contract, block on the narrowest matching blocker and stop short of `acceptance_frozen`.
- If a required special UI-provided icon cannot be downloaded from MCP or another trusted provider and the user has not provided it, block on `blocked_missing_design` or the narrowest available visual-evidence blocker.
- Do not block acceptance only because later action semantics or server side effects are still incomplete when those gaps do not alter the frozen screen-state contract.
- Only move the sub-requirement to `acceptance_frozen` when the YAML contract is fully source-backed and safe for downstream consumption.

## Hard Constraints

- Read upstream governed artifacts before writing the acceptance contract.
- Keep workflow truth in `.ai-delivery/`.
- Do not replace `traceability.json`.
- Do not produce a Markdown acceptance contract.
- Do not soften 1:1-impacting unknowns into non-blocking prose.
- Do not allow downstream spec, plan, tasks, or implementation to proceed before `acceptance_frozen`.

## Output Standard

Every YAML acceptance contract must define:

- `contract` metadata and source dependencies
- top-level `spacing_policy`
- frozen `screen_states`
- nested `component_tree` for every final screen state
- component identity, type, role, hierarchy, and requiredness
- layout mode, axis, alignment, gap, positioning, wrap, and constraints
- box model padding, margin, gap ownership, and spacing semantics
- size behavior and key dimensions
- component-specific props
- typography, content, overflow, icon, image, and state rules where applicable
- implementation mapping to preferred code components when source-backed
- source refs for 1:1-impacting values
- `verification_targets`
- `unresolved_ui_truth`

If the separate admin support surface is unavailable, keep artifact truth in `.ai-delivery/` and document the missing governed dependency locally without inventing another truth store.

## Self-Check Checklist

Before reporting completion, confirm all of the following:

- [ ] `requirement-slice.md` and `figma-mapping.md` were read before drafting
- [ ] Every frozen screen state has trustworthy executable evidence
- [ ] Every critical screen state has `get_code` evidence
- [ ] `ui-acceptance-contract.yaml` was written
- [ ] No Markdown acceptance contract remains as a parallel acceptance truth
- [ ] `traceability.json.ui_acceptance_contract` was updated without overwriting other fields
- [ ] `status.json` only moved to `acceptance_frozen` when the YAML contract became source-backed
- [ ] `screen_states[*].component_tree` carries hierarchy, layout, box model, component type, and key style truth
- [ ] `spacing_policy` and node-level `box_model.spacing_semantics` make padding, margin, and gap ownership explicit
- [ ] Special UI-provided icons are downloaded and referenced, or blocked until provided
- [ ] `verification_targets` are explicit
- [ ] No 1:1-impacting unknown was silently left as a soft note

## Handoff

Stop after producing `ui-acceptance-contract.yaml`, updating `traceability.json.ui_acceptance_contract`, and moving the sub-requirement to `acceptance_frozen` or blocked.

If the user wants to continue, hand the downstream stage `requirement-slice.md`, `api-contract-mapping.md` when present, `figma-mapping.md`, `ui-acceptance-contract.yaml`, `traceability.json`, and `decisions.md`. Do not perform interaction design, Spec Kit generation, or implementation inside this skill unless the user explicitly asks for the next stage.
