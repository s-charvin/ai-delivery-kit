# Delivery Gate Guide

Short enforcement reference for UI delivery work in bootstrapped repositories.

## Canonical contract format

- Template: `.agents/skills/ui-truth-mapping/templates/ui-acceptance-contract-template.yaml`
- Minimal valid example: `.agents/skills/ui-truth-mapping/fixtures/ui-acceptance-contract-good.yaml`
- Legacy or simplified contracts from other requirements are **not** valid references

## Required structure (first-pass human review)

Open `ui-acceptance-contract.yaml` and confirm:

- `version`, `contract_id`, `states`, `regions` exist at the top level
- `regions[].children[]` use four-direction `anchor` and four-direction `padding`
- No forbidden fields: `visual_truth`, `code-baseline`, `layout_note`, `implementation_reference`, `policy`, `screen_states`

## Mechanical gates

```bash
python3 .ai-delivery/scripts/validate-ui-contract.py <contract-path>
python3 .ai-delivery/scripts/validate-delivery-status.py .ai-delivery/requirements/<req-id>/status.json --req-root .ai-delivery/requirements/<req-id>
```

- `acceptance_frozen` requires validator `OK`
- `merged` for UI work requires prior `acceptance_frozen` + `visual_acceptance_passed` + validator still `OK`

## Workflow entry

Start UI-bearing requirements through `ai-delivery-orchestrator`. Do not skip `ui-truth-mapping` and claim 1:1 implementation from `figma-design-to-code` alone.
