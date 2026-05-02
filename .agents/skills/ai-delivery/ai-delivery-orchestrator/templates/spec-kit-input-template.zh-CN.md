# Spec Kit 输入包

- requirement_id: <requirement-id>
- subreq_id: <subreq-id>
- slice_id: <slice-id>
- slice_type: <page-state|shared-state|integration>
- generated_at: <ISO8601>
- source_of_truth: .ai-delivery

## 源合约

- slice_contract_path: <path-to-slice-contract.md>
- interaction_design_path: <path-to-interaction-design.md>
- ui_acceptance_contract_path: <path-or-not_applicable>
- api_contract_mapping_path: <path-or-not_applicable>

## 可追溯性引用

- requirement_refs: []
- api_refs: []
- figma_refs: []
- ui_acceptance_refs: []
- interaction_refs: []

## 规划约束

- official_speckit_skills_unchanged: true
- do_not_reinvent_truth: true
- ui_must_be_acceptance_frozen_before_spec_kit: true
- bind_results_back_to_ai_delivery: true
