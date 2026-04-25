<!-- ai-delivery-meta: {"version":1,"updated_at":"2026-04-25T00:00:00.000Z","updated_by":"codex"} -->

# Interaction Design

## Action Chain Matrix

| Action | Start State | Target State | Guard |
| --- | --- | --- | --- |
| Open add-friend entry | contacts-friends-idle | add-friend-entry-focused | UI acceptance contract frozen |
| Refresh contacts | contacts-friends-idle | contacts-friends-loading | API contract mapped |

## Delivery Slice Handoff

The `contacts-friends-idle` slice is ready for Spec Kit context preparation and task binding.
