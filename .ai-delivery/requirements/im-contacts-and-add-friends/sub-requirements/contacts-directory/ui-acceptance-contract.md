<!-- ai-delivery-meta: {"version":1,"updated_at":"2026-04-25T00:00:00.000Z","updated_by":"codex"} -->

# UI Acceptance Contract

## Screen State Inventory

### contacts-friends-idle

- `screen_state_id`: `contacts-friends-idle`
- `state_type`: `idle`
- `executable_frame_node_id`: `12:34`
- `parent_shell_node_id`: `10:1`

## Required Structure Order

### Directory Shell

- `position`: `1`
- `node_id`: `12:34`
- `role`: `contacts-directory-shell`
- `required`: `true`

## Required Elements

### Add Friend Entry

- `node_id`: `12:40`
- `role`: `add-friend-entry`
- `required`: `true`
- `notes`: Primary entry remains visible in the idle state.

## Verification Targets

### Idle Golden

- `screen_state_id`: `contacts-friends-idle`
- `golden_name`: `contacts-friends-idle`
- `screenshot_size`: `390x844`
- `artifact_refs`: `figma-mapping.md`, `interaction-design.md`
- `manual_side_by_side_points`: Directory title, grouped contacts, add-friend entry, empty/error affordances.
