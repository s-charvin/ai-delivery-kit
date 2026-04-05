# Project-Local AI Delivery Skills

These workflow skills are business-project assets that live inside this repository.

They operate on the host project's `.ai-delivery/` workflow data, especially under:

- `.ai-delivery/requirements/`
- `.ai-delivery/meta/`
- `.ai-delivery/runtime/`
- `.ai-delivery/logs/`

They are not owned by `ai-delivery-admin`, and they must not relocate workflow truth into the admin repository.

When governed logging, status transitions, blocker handling, or artifact mutation are needed, these project-local skills should use the separate admin support surfaces when those surfaces are available.

Shared references and output templates live under this `common/` directory so the three workflow skills stay aligned on truth boundaries, blocker handling, and artifact shapes.

## Usage

Project-local workflow skill packages live under:

- `.codex/skills/ai-delivery/requirement-breakdown`
- `.codex/skills/ai-delivery/ui-requirement-mapping`
- `.codex/skills/ai-delivery/ui-interaction-design`

From the repository root, sync them into the current Codex environment without moving source of truth out of the repository:

```bash
zsh scripts/install-project-ai-delivery-skills.sh
```

`ai-delivery-admin` owns the separate admin support skill and MCP server. These project-local workflow skills should cooperate with those governed support surfaces rather than trying to replace them.
