from __future__ import annotations

import sys
import uuid
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from mcp.auth import ToolContext
from mcp.tools_phase2 import add_addendum, transfer_owner
from orchestration.models import NodeStatus
from tests.e2e._util import HappyPathDriver


class TestTC18TransferAddendum:
    """TC-18: transfer_owner (零级联) + addendum(should) (不改状态, 下游 notify)。"""

    def test_tc18_transfer_owner_and_should_addendum(self, env):
        driver = HappyPathDriver(env)
        driver.create_pipeline("fullstack")
        pid = driver.pid

        # Run first half: n1 → n2 done
        sha1 = driver.submit_and_approve("n1")
        assert sha1, "n1 should approve"

        sha2 = driver.submit_and_approve("n2")
        assert sha2, "n2 should approve"

        n2 = driver.get_node("n2")
        s2 = NodeStatus(n2.status) if isinstance(n2.status, str) else n2.status
        assert s2 == NodeStatus.DONE, f"n2 should be DONE, got {s2}"

        # Record n5 status before transfer (n5 depends on n2)
        n5_before = driver.get_node("n5")
        s5_before = NodeStatus(n5_before.status) if isinstance(
            n5_before.status, str
        ) else n5_before.status

        admin_ctx = ToolContext(
            token_payload={"token_type": "admin", "sub": "admin-bot", "node_id": "admin"},
        )

        # transfer_owner: n2 from product-bot to server-lead
        transfer_result = transfer_owner(
            pipeline_id=pid,
            node_id="n2",
            from_owner="product-bot",
            to_owner="server-lead",
            revoke_tokens=False,
            _ctx=admin_ctx,
        )
        assert transfer_result["ok"], "transfer_owner should succeed"
        assert transfer_result["from_owner"] == "product-bot"
        assert transfer_result["to_owner"] == "server-lead"

        # n2.status should still be DONE (zero cascade)
        n2_after_transfer = driver.get_node("n2")
        s2_after = NodeStatus(n2_after_transfer.status) if isinstance(
            n2_after_transfer.status, str
        ) else n2_after_transfer.status
        assert s2_after == NodeStatus.DONE, (
            f"n2 should still be DONE after transfer (zero cascade), got {s2_after}"
        )

        # n5 status should not change
        n5_after_transfer = driver.get_node("n5")
        s5_after_transfer = NodeStatus(n5_after_transfer.status) if isinstance(
            n5_after_transfer.status, str
        ) else n5_after_transfer.status
        assert s5_after_transfer == s5_before, (
            f"n5 should not change after transfer, before={s5_before}, after={s5_after_transfer}"
        )

        # Audit should have TRANSFER_OWNER entry
        audit_entries = env.worm.list(pipeline_id=pid)
        has_transfer = any(
            "TRANSFER_OWNER" in (e.action or "") for e in audit_entries
        )
        assert has_transfer, (
            f"audit should have TRANSFER_OWNER, actions: {[e.action for e in audit_entries]}"
        )

        # add_addendum: should class, no incompatible_with, impact_claim=[n5]
        addendum_result = add_addendum(
            pipeline_id=pid,
            node_id="n2",
            change_class="should",
            incompatible_with=[],
            impact_claim=["n5"],
            author="server-lead",
            _ctx=admin_ctx,
        )
        assert addendum_result["addendum_id"], "add_addendum should return addendum_id"
        assert addendum_result["change_class"] == "should"

        # n2.status should still be DONE (addendum doesn't change status)
        n2_after_addendum = driver.get_node("n2")
        s2_after_addendum = NodeStatus(n2_after_addendum.status) if isinstance(
            n2_after_addendum.status, str
        ) else n2_after_addendum.status
        assert s2_after_addendum == NodeStatus.DONE, (
            f"n2 should still be DONE after should-addendum, got {s2_after_addendum}"
        )

        # n5 status should NOT change (should addendum only notifies, no status change)
        n5_after_addendum = driver.get_node("n5")
        s5_after_addendum = NodeStatus(n5_after_addendum.status) if isinstance(
            n5_after_addendum.status, str
        ) else n5_after_addendum.status
        assert s5_after_addendum == s5_before, (
            f"n5 status should not change after should-addendum, "
            f"before={s5_before}, after={s5_after_addendum}"
        )

        # Audit should have both TRANSFER_OWNER and ADD_ADDENDUM entries
        audit_entries_final = env.worm.list(pipeline_id=pid)
        actions = [e.action for e in audit_entries_final]
        has_transfer_final = any("TRANSFER_OWNER" in a for a in actions)
        has_addendum = any("ADD_ADDENDUM" in a for a in actions)
        assert has_transfer_final, f"audit should have TRANSFER_OWNER, actions: {actions}"
        assert has_addendum, f"audit should have ADD_ADDENDUM, actions: {actions}"

        # Count: at least 2 entries (transfer + addendum) beyond the approve entries
        transfer_count = sum(1 for a in actions if "TRANSFER_OWNER" in a)
        addendum_count = sum(1 for a in actions if "ADD_ADDENDUM" in a)
        assert transfer_count >= 1, f"expected >= 1 TRANSFER_OWNER, got {transfer_count}"
        assert addendum_count >= 1, f"expected >= 1 ADD_ADDENDUM, got {addendum_count}"
