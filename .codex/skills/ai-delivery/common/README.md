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

## Full-Chain Repair Notes

- full-chain closure now depends on governed bootstrap, blocked-state recovery, merge finalization, and traceability-based Spec Kit bridge refs all operating over the same `.ai-delivery/` truth
- `traceability.json` is a first-class governed artifact and the formal cross-layer carrier for both Figma evidence and `spec_kit_refs`
- intake bootstrap does not preseed downstream `figma-mapping.md` or `interaction-design.md`; those files appear on first real write by the matching project-local skill or governed editor
- Figma cache under `.ai-delivery/figma-cache/` is indexed, freshness-checked, and read-oriented; it is not a generic editable document family
- runtime daemon management is an admin-runtime concern and does not replace workflow truth recorded in `.ai-delivery/runtime/`

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
