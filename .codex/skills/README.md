# Codex Skills In This Repository

This repository currently owns the project-local AI delivery workflow skills under:

- `/Users/charvin/Projects/Codex/.codex/skills/ai-delivery/requirement-breakdown`
- `/Users/charvin/Projects/Codex/.codex/skills/ai-delivery/ui-requirement-mapping`
- `/Users/charvin/Projects/Codex/.codex/skills/ai-delivery/ui-interaction-design`

These are business-project skills. They operate on `.ai-delivery/` inside this repository and are not owned by `ai-delivery-admin`.

To sync them into the current Codex environment without moving source of truth out of the repository, use:

```bash
zsh /Users/charvin/Projects/Codex/scripts/install-project-ai-delivery-skills.sh
```

`ai-delivery-admin` separately owns:

- the admin support skill
- the governed MCP server
