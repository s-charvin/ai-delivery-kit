# Pause And Retry Policy

- Automatic retries: ordinary stage 2, review repair 2, visual acceptance repair 2, transient tool failure 1.
- Pause only on `CP-001 tasks_ready_user_confirmation` or `CP-002 hard_blocker_pause`.
- `CP-001`: pause only after all executable slices reach `tasks_ready`.
- `CP-002`: pause on hard blocker, non-recoverable gate failure, or missing human decision.
- `review` first failure and visual acceptance first failure must enter auto-fix loops before escalation.
