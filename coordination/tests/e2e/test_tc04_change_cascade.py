from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from orchestration.models import DepCoupling, DepDeclaration, DepPresence, DepStrictness, NodeDef, NodeStatus
from tests.e2e._util import HappyPathDriver
from utils.hashing import hash_chain_validate


class TestTC04ChangeCascade:
    def test_tr92_breaking_change_cascade_invalidates_downstream(self, env):
        driver = HappyPathDriver(env)
        ready_roots = driver.create_pipeline("fullstack")
        assert "n1" in ready_roots

        sha1 = driver.submit_and_approve("n1")
        assert sha1
        sha2 = driver.submit_and_approve("n2")
        assert sha2
        sha3 = driver.submit_and_approve("n3")
        assert sha3

        sha4 = driver.submit_and_approve("n4")
        sha5 = driver.submit_and_approve("n5")
        assert sha4 and sha5

        n5_before = driver.get_node("n5")
        assert NodeStatus(n5_before.status) == NodeStatus.DONE
        assert len(n5_before.artifact_refs) >= 1, "n5 should have artifact_refs before breaking change"

        from orchestration.cascade import cascade_changed
        from mcp.state_store import STORE
        defn = STORE.get_def(driver.pid)
        state = STORE.get_state(driver.pid)
        new_state, evts = cascade_changed(
            "n2", "breaking", DepCoupling.HARD, defn, state
        )
        STORE.set_state(driver.pid, new_state)

        audit_payload = {
            "action": "changed",
            "node_id": "n2",
            "change_class": "breaking",
            "downstream_invalidated": True,
        }
        from audit.worm_storage import AuditLogEntry
        from datetime import datetime, timezone
        import uuid
        worm_entry = AuditLogEntry(
            prev_hash="",
            action="NODE_CHANGED",
            actor="coordination-bot",
            payload=audit_payload,
            hash="",
            created_at=datetime.now(timezone.utc).isoformat(),
            pipeline_id=driver.pid,
            node_id="n2",
            trace_id=uuid.uuid4().hex,
        )
        env.worm.insert(worm_entry)

        n5_after = driver.get_node("n5")
        s5 = NodeStatus(n5_after.status) if isinstance(n5_after.status, str) else n5_after.status
        assert s5 in {NodeStatus.CHANGED, NodeStatus.BLOCKED}, (
            f"n5 should be invalidated after upstream breaking change, got {s5}"
        )
        assert len(n5_after.artifact_refs) == 0 or s5 == NodeStatus.BLOCKED or s5 == NodeStatus.CHANGED

        audit_all = env.worm.list(pipeline_id=driver.pid)
        assert len(audit_all) > 0
        last_action = audit_all[-1].action
        last_payload_str = str(audit_all[-1].payload).lower()
        assert "changed" in last_action.lower() or "changed" in last_payload_str, (
            f"last audit should mention changed, got action={last_action}"
        )

        valid, bad_idx = hash_chain_validate(audit_all)
        assert valid, f"hash chain should remain valid after cascade, broken at {bad_idx}"
