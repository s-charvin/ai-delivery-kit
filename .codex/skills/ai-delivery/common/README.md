# Project-Local AI Delivery Skills

These workflow skills are business-project assets that live inside this repository.

They operate on the host project's `.ai-delivery/` workflow data, especially under:

- `/Users/charvin/Projects/Codex/.ai-delivery/requirements/`
- `/Users/charvin/Projects/Codex/.ai-delivery/meta/`
- `/Users/charvin/Projects/Codex/.ai-delivery/runtime/`
- `/Users/charvin/Projects/Codex/.ai-delivery/logs/`

They are not owned by `ai-delivery-admin`, and they must not relocate workflow truth into `/Users/charvin/Projects/ai-delivery-admin`.

When governed logging, status transitions, blocker handling, or artifact mutation are needed, these project-local skills should use the separate admin support surfaces when those surfaces are available.

Shared references and output templates live under this `common/` directory so the three workflow skills stay aligned on truth boundaries, blocker handling, and artifact shapes.
