# Skeleton / Roadmap Tools

This list records MCP tools that were historically registered as MVP skeletons
(`E_NOT_IMPLEMENTED`). The skeleton registration mechanism has been removed from
`coordination/mcp/server.py`; the names below are kept here as the implementation
roadmap so intent is not lost.

Some of these names are **already implemented** as real tools in
`coordination/mcp/tools_phase2.py` (e.g. `transfer_owner`, `add_addendum`,
`skip_node`, `request_approval`, `approve_node`, `reject_node`, ...). Those are
excluded from the "not yet implemented" set below.

## Not yet implemented (roadmap)

- merge_pipelines
- split_pipeline
- emergency_local_commit
- emergency_restore_hub
- handle_security_incident
- submit_draft
- resubmit_draft
- publish_draft
- report_node_status
- report_pipeline_cost
- approve_approval_node
- reject_approval_node
- set_gate_policy
- list_pending_prs
- get_pr_detail_tool
- get_audit_log
- export_compliance_report
- revoke_human_token
- materialize_pipeline_tool
- report_consumption_status
- report_generation_status
- emergency_approve
- sync_pending_artifacts
- subscribe_draft
- unsubscribe_draft
- reack_addendum
- list_addenda
