---
description: UI contract gate — template-only YAML, validator required, no bypass fields
paths:
  - "**/ui-acceptance-contract.yaml"
---

# UI Contract Gate

When editing `**/ui-acceptance-contract.yaml`:

1. Read `.agents/skills/ui-truth-mapping/templates/ui-acceptance-contract-template.yaml` first.
2. Copy template structure verbatim — never reuse another requirement's simplified YAML.
3. After every write, run:
   `python3 scripts/validate-ui-contract.py <contract-path>`
   (bootstrapped repos: `python3 .ai-delivery/scripts/validate-ui-contract.py <contract-path>`)
4. Do not claim `acceptance_frozen`, 1:1 fidelity, or `merged` until validator prints `OK`.

Forbidden contract fields: `visual_truth`, `code-baseline`, `layout_note`, `implementation_reference`, `policy`, `screen_states`, top-level `requirement_id`.

UI work enters through `ai-delivery-orchestrator`. TemPad MCP errors → STOP, do not guess.
