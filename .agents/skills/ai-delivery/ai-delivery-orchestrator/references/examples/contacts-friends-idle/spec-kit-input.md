# Spec Kit Input Bundle

- requirement_id: im-contacts-and-add-friends
- subreq_id: contacts-directory
- slice_id: contacts-friends-idle
- slice_type: page-state
- generated_at: 2026-04-21T11:45:00+08:00
- source_of_truth: .ai-delivery

## Source Contracts

- slice_contract_path: .ai-delivery/requirements/im-contacts-and-add-friends/sub-requirements/contacts-directory/delivery-slices/contacts-friends-idle/slice-contract.md
- interaction_design_path: .ai-delivery/requirements/im-contacts-and-add-friends/sub-requirements/contacts-directory/interaction-design.md
- ui_acceptance_contract_path: .ai-delivery/requirements/im-contacts-and-add-friends/sub-requirements/contacts-directory/ui-acceptance-contract.md
- api_contract_mapping_path: .ai-delivery/requirements/im-contacts-and-add-friends/sub-requirements/contacts-directory/api-contract-mapping.md

## Traceability Refs

- requirement_refs:
  - docs/superpowers/requirements/IM私聊功能1.0.md#L55-L60
  - docs/superpowers/requirements/IM私聊功能1.0.md#L143-L143
- api_refs:
  - POST /user/my_friends
- figma_refs:
  - 1342:49565
  - 1342:49751
  - 1342:49792
  - 1342:49796
  - 1342:49567
- ui_acceptance_refs:
  - contacts-friends-idle
- interaction_refs:
  - contacts-switch-tab
  - contacts-open-profile

## Planning Constraints

- official_speckit_skills_unchanged: true
- do_not_reinvent_truth: true
- ui_must_be_acceptance_frozen_before_spec_kit: true
- bind_results_back_to_ai_delivery: true

## Output Targets

- target_spec_path: specs/contacts-directory-slices/contacts-friends-idle/spec.md
- target_plan_path: specs/contacts-directory-slices/contacts-friends-idle/plan.md
- target_tasks_path: specs/contacts-directory-slices/contacts-friends-idle/tasks.md
