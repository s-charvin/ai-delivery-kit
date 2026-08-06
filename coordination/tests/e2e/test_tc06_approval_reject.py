from __future__ import annotations

import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from orchestration.models import (
    DepCoupling,
    DepDeclaration,
    DepPresence,
    DepStrictness,
    NodeDef,
    NodeStatus,
)
from tests.e2e._util import HappyPathDriver


class TestTC06ApprovalReject:
    def test_tc06_approval_reject_rollback_upstream(self, env):
        extra_nodes = [
            NodeDef(
                node_id="n1",
                node_type="product_spec",
                role_assignments=[],
                deps=[],
            ),
            NodeDef(
                node_id="n2",
                node_type="approval_control",
                role_assignments=[],
                deps=[
                    DepDeclaration(
                        upstream="n1",
                        presence=DepPresence.REQUIRED,
                        strictness=DepStrictness.STRICT,
                        coupling=DepCoupling.HARD,
                    )
                ],
                requires_human_review=True,
            ),
            NodeDef(
                node_id="n3",
                node_type="server_impl",
                role_assignments=[],
                deps=[
                    DepDeclaration(
                        upstream="n2",
                        presence=DepPresence.REQUIRED,
                        strictness=DepStrictness.STRICT,
                        coupling=DepCoupling.HARD,
                    )
                ],
            ),
        ]

        driver = HappyPathDriver(env)
        _ = driver.create_pipeline(
            "fullstack",
            extra_nodes=extra_nodes,
            pid=f"pipe-tc06-{uuid.uuid4().hex[:8]}",
        )
        pid = driver.pid

        sha1 = driver.submit_and_approve("n1")
        assert sha1, "n1 product_spec should approve ok"

        n1_after_approve = driver.get_node("n1")
        s1 = NodeStatus(n1_after_approve.status) if isinstance(
            n1_after_approve.status, str
        ) else n1_after_approve.status
        assert s1 == NodeStatus.DONE, f"n1 should be DONE, got {s1}"
        assert len(n1_after_approve.artifact_refs) >= 1, (
            "n1 should have artifact refs before approval reject"
        )

        from mcp.tools_phase2 import request_approval, reject_node
        from mcp.auth import ToolContext

        admin_ctx = ToolContext(
            token_payload={"token_type": "admin", "sub": "admin-bot", "node_id": "admin"},
        )

        req_result = request_approval(
            pipeline_id=pid,
            node_id="n2",
            requester_id="product-owner",
            note="please review n2 approval control",
            _ctx=admin_ctx,
        )
        assert req_result, "request_approval should return result"

        n2_after_req = driver.get_node("n2")
        s2 = NodeStatus(n2_after_req.status) if isinstance(
            n2_after_req.status, str
        ) else n2_after_req.status
        assert s2 in {
            NodeStatus.REVIEW, NodeStatus.PENDING_REVIEW, NodeStatus.IN_PROGRESS,
        }, f"n2 should be in review state after request_approval, got {s2}"

        reject_result = reject_node(
            pipeline_id=pid,
            control_node_id="n2",
            reviewer_id="senior-reviewer",
            reason="不通过: 规格描述不清晰，需补充边界条件",
            rollback_ref_artifacts=True,
            _ctx=admin_ctx,
        )
        assert reject_result, "reject_node should return result"

        n1_after_reject = driver.get_node("n1")
        s1_after = NodeStatus(n1_after_reject.status) if isinstance(
            n1_after_reject.status, str
        ) else n1_after_reject.status
        assert s1_after in {
            NodeStatus.CHANGED, NodeStatus.IN_PROGRESS, NodeStatus.READY,
        }, (
            f"upstream n1 should be invalidated (CHANGED/IN_PROGRESS/READY) "
            f"after approval reject, got {s1_after}"
        )

        audit_entries = env.worm.list(pipeline_id=pid)
        has_rollback = any(
            "CODE_ROLLBACK_NEEDED" in (e.action or "")
            for e in audit_entries
        )
        audit_action_strs = [e.action for e in audit_entries]
        assert has_rollback, (
            f"expected CODE_ROLLBACK_NEEDED audit entry for FR2.6 double rollback, "
            f"got actions: {audit_action_strs}"
        )

        n2_final = driver.get_node("n2")
        s2_final = NodeStatus(n2_final.status) if isinstance(
            n2_final.status, str
        ) else n2_final.status
        assert s2_final in {
            NodeStatus.READY, NodeStatus.REVIEW, NodeStatus.PENDING_REVIEW,
            NodeStatus.BLOCKED, NodeStatus.IN_PROGRESS,
        }, f"n2 approval control should be READY/review/blocked after reject, got {s2_final}"

        rollback_entry = None
        for e in audit_entries:
            if "CODE_ROLLBACK_NEEDED" in (e.action or ""):
                rollback_entry = e
                break
        assert rollback_entry is not None
        payload = rollback_entry.payload or {}
        assert payload.get("tracking") == 1 or payload.get("upstream_node_id"), (
            "CODE_ROLLBACK_NEEDED should carry tracking metadata for FR2.6"
        )
