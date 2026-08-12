# Changelog

## Unreleased — unified artifact layout refactor

**Applies only to new `ai-delivery init` repositories.** No automatic migration for existing layouts.

### Added

- Canonical artifact home under `.ai-delivery/requirements/<req-id>/sub-requirements/<SR>/` (`design.md`, `verification.md`, `spec/{spec,plan,tasks}.md`, `contracts/ui-contract-index.json`, `archive/<ISO-ts>/` + `MANIFEST.json`)
- `project-binding.json` → `layout` path constants (skill `layout.py`; mirror in coordination repo `config/paths.py`)
- `scripts/validate-artifact-layout.py`, `scripts/archive-subrequirement.py`
- Spec persistence policy (`living` / `flow_forward`) and `verification.md` gate at `merged` / `archived`
- OpenSpec-style closure: `merged` → `archive` action → `archived` terminal state, CP-ARCHIVE, `delivery-report.md`
- Coordination: [`s-charvin/ai-delivery-coordination`](https://github.com/s-charvin/ai-delivery-coordination) is a **separate skill + MCP service** (not vendored in this repo); install separately when multi-party work is needed

### Changed

- **`merged` vs `archived`**: `merged` = code integrated; `archived` = immutable freeze; requirement `completed` when all executable subreqs are `archived`
- Reconcile terminal status is `archived` (not `merged`)
- `native` tier: separate `spec/plan.md` and `spec/tasks.md` (no `plan_path → tasks.md` shortcut)
- Coordination MCP (optional, separate install) uses write-through SQLite STORE — see ai-delivery-coordination repo

### Coordination

Independent repository + MCP service only. **Removed** git submodule from ai-delivery-kit. `.ai-delivery/` does not contain coordination code or config.

### Completed in this refactor

- Moved `.ai-delivery/requirements/example-requirement/` → `tests/ai-delivery-contracts/fixtures/example-requirement/`; `zero-based-flow.test.sh` copies the fixture into a temp dir before asserting.
- IDE hooks 4× → 1 canonical + bootstrap-generated 2-line wrappers (`.cursor` / `.claude` / `.codex`)
- Reconcile dependency-graph-only path + `layout.resolve_validator_script` single entry
- Coordination MCP: lightweight `hub://` artifact pointers + claim/status tools (`register_artifact_ref`, `claim_node`, `report_node_status`, …); parties self-manage storage
