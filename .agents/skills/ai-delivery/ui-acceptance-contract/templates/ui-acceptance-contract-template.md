<!-- ai-delivery-meta: {"version":1,"updated_at":"<ISO8601>","updated_by":"<agent>"} -->

# UI Acceptance Contract

## Screen State Inventory

### Screen State 1

- `screen_state_id`:
- `state_type`:
- `executable_frame_node_id`:
- `parent_shell_node_id`:

## Executable Frame Contract

- `screen_state_id`:
- `artifact_refs`:
- `evidence_basis`:

## Required Structure Order

### Structure Item 1

- `position`:
- `node_id`:
- `role`:
- `required`:

## Required Elements

### Element Item 1

- `node_id`:
- `role`:
- `required`: `true | false`
- `notes`:

## Layout Constraints

- `constraint`:
- `screen_state_id`:

## Content Constraints

- `constraint`:
- `screen_state_id`:

## Asset Contract

- `asset_rule`:
- `screen_state_id`:

## Reuse Policy

- `component_or_region`:
- `reuse_rule`:
- `notes`:

## Blocking Unknowns

- `unknown`:
- `impact`:
- `resolution_path`:

## Verification Targets

### Verification Item 1

- `screen_state_id`:
- `golden_name`:
- `screenshot_size`:
- `artifact_refs`:
- `manual_side_by_side_points`:

---

## Template Authoring Rules

1. `ui-acceptance-contract.md` is the governed freeze artifact for immutable screen-state acceptance truth.
2. Every frozen screen state must name its executable frame, parent shell, and verification targets.
3. `Blocking Unknowns` must explicitly capture every unresolved 1:1-impacting issue instead of hiding it in free-form prose.
4. `Verification Targets` should give downstream TDD and visual acceptance stages exact names and artifact refs to consume.
5. Do not copy the `Template Authoring Rules` section into generated acceptance artifacts.
