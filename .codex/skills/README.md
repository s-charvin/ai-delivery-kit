# Project-Local AI Delivery Skills

This repository carries a vendorable set of project-local AI delivery workflow skills under:

- `.codex/skills/ai-delivery/requirement-breakdown`
- `.codex/skills/ai-delivery/ui-requirement-mapping`
- `.codex/skills/ai-delivery/ui-interaction-design`

These are business-project skills. They operate on `.ai-delivery/` inside whichever host repository owns them.

First-time bootstrap into another repository:

```bash
zsh scripts/bootstrap-ai-delivery-project.sh --target-repo /path/to/target-repo --project-id my-project --main-branch main-dev
```

Refresh an already bootstrapped repository from this one:

```bash
zsh scripts/sync-ai-delivery-project-assets.sh --target-repo /path/to/target-repo
```

Inside any bootstrapped repository, sync the project-local skills into the current Codex environment:

```bash
zsh scripts/install-project-ai-delivery-skills.sh
```
