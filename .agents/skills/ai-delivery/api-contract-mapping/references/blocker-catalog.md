# Blocker Catalog

## Core Blockers

- `blocked_requirement_conflict`: the requirement source contradicts itself or another requirement source.
- `blocked_missing_requirement`: a critical business fact is missing.
- `blocked_figma_conflict`: the design source contradicts itself.
- `blocked_requirement_figma_conflict`: requirement truth and visual truth disagree.
- `blocked_missing_design`: a required visual carrier is missing from design evidence.
- `blocked_dependency`: an upstream sub-requirement is not merged to the main development branch.
- `blocked_merge_conflict`: merge-back to the main development branch failed.
- `blocked_verification_failure`: required checks failed and the output cannot be trusted.

## API Contract Blockers

- `blocked_missing_api_contract`: reserve for cases where the current requested output explicitly depends on contract-backed API truth and no trustworthy client-facing source exists. Do not use this as the default result of missing API material during early frontend stages.
- `blocked_api_contract_conflict`: multiple Swagger, OpenAPI, or exported contract sources disagree on client-facing truth in a way that changes current-stage conclusions.
- `blocked_requirement_api_conflict`: requirement truth and interface-contract truth disagree in a way that changes user-visible behavior or makes the current artifact materially wrong.

## Usage Rule

Choose the narrowest blocker that explains why the next state transition cannot happen, then document the evidence and recovery condition in the matching requirement folder.
