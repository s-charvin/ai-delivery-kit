# Project-Local AI Delivery Skills

This repository carries a vendorable set of project-local AI delivery workflow skills under:

- `.codex/skills/ai-delivery/requirement-breakdown`
- `.codex/skills/ai-delivery/ui-requirement-mapping`
- `.codex/skills/ai-delivery/ui-interaction-design`

These are business-project skills. They operate on `.ai-delivery/` inside whichever host repository owns them.

When these managed helper assets are bootstrapped into another repository, the three workflow skills are installed directly into that host repo's `.agents/skills/` directory, while validation/docs artifacts live under `.ai-delivery/`.

First-time bootstrap into another repository:

```bash
zsh scripts/bootstrap-ai-delivery-project.sh --target-repo /path/to/target-repo --project-id my-project --main-branch main-dev
```

Inside any bootstrapped repository, validate the installed project-local skills:

```bash
zsh .ai-delivery/scripts/validate-project-ai-delivery-skills.sh
```
