# Blocker Catalog

When a blocker occurs, record the narrowest matching blocker, continue other runnable sub-requirements, and pause the entire requirement only when no safe runnable item remains.

## Requirement breakdown

| Blocker | Trigger |
|---------|---------|
| `blocked_missing_requirement` | Critical business fact missing from source |
| `blocked_requirement_conflict` | Two approved sources contradict each other |
| `blocked_dependency` | Upstream sub-requirement not ready |

## UI truth mapping

| Blocker | Trigger |
|---------|---------|
| `blocked_missing_design` | Required visual carrier missing from design evidence |
| `blocked_requirement_figma_conflict` | Requirement and visual truth irreconcilable |
| `blocked_figma_conflict` | Design evidence contradicts itself |
| `blocked_missing_state_code` | Final screen state lacks structured frame evidence |
| `blocked_missing_visual_truth` | Missing default state, row composition, parent shell, or key asset |
| `blocked_verification_failure` | Contract validator failed or evidence cannot be validated |

## Spec Kit and implementation

| Blocker | Trigger |
|---------|---------|
| `blocked_spec_mismatch` | Spec output conflicts with governed truth |
| `blocked_dependency_slice` | Upstream slice not merged |
| `blocked_merge_conflict` | Rebase/integration failed |
| `blocked_verification_failure` | Tests, review, or visual acceptance failed after auto-fix |

## Recording a blocker

Update the sub-requirement entry in `status.json`:

```json
{
  "status": "blocked_missing_design",
  "detail": "Figma file lacks the confirmation dialog frame",
  "blocked_from_status": "acceptance_frozen",
  "blocker_scope": "slice_local",
  "resume_target_status": "acceptance_frozen",
  "notes": null
}
```

## Recovery

When the user resolves the blocker, resume toward `resume_target_status`.

## Narrowest-blocker rule

- Prefer `blocked_missing_state_code` over `blocked_missing_design`.
- Prefer `blocked_requirement_figma_conflict` over `blocked_missing_visual_truth`.
- Never promote to `requirement_global` while any safe runnable queue item exists across all subreqs.

## Blocker scope

- **`slice_local`** — blocks one slice/stage only.
- **`action_level_integration`** — blocks real API wiring for one action; does not block shell, navigation, or read-only paths.
- **`requirement_global`** — only when every derivable queue item is non-runnable.

Default: **continue safest runnable work first**.
