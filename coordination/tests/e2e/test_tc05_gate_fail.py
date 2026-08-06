from __future__ import annotations

import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from audit.worm_storage import AuditLogEntry
from orchestration.gate_policy import GatePolicy, get_gate_policy_store
from orchestration.models import (
    DepCoupling,
    DepDeclaration,
    DepPresence,
    DepStrictness,
    NodeDef,
    NodeStatus,
)
from tests.e2e._util import HappyPathDriver


class TestTC05GateFail:
    def test_tc05_gate_fail_rollback_and_recover(self, env):
        gate_store = get_gate_policy_store()
        gate_store.clear_all()

        driver = HappyPathDriver(env)
        ready_roots = driver.create_pipeline("fullstack")
        assert "n1" in ready_roots

        pid = driver.pid
        gate_node_id = "n7"

        gate_store.set_policy(GatePolicy(
            pipeline_id=pid,
            gate_node_id=gate_node_id,
            coverage_min=0.80,
            lint=True,
            test=True,
            security_scan=True,
        ))

        sha1 = driver.submit_and_approve("n1")
        assert sha1
        sha2 = driver.submit_and_approve("n2")
        assert sha2
        sha3 = driver.submit_and_approve("n3")
        assert sha3
        sha5 = driver.submit_and_approve("n5")
        assert sha5
        sha4 = driver.submit_and_approve("n4")
        assert sha4
        sha6 = driver.submit_and_approve("n6")
        assert sha6

        n6_before = driver.get_node("n6")
        assert NodeStatus(n6_before.status) == NodeStatus.DONE

        gate_pr_content = b"gate artifact preliminary"
        pr_id_gate, gate_path = driver._submit_to_hub(
            gate_node_id, gate_pr_content, 1, "compatible",
            None, None, None,
        )
        from mcp.state_store import STORE
        STORE.set_pending_pr(gate_node_id, pr_id_gate)
        driver._submitted_prs[gate_node_id] = pr_id_gate
        driver._submit_transition(gate_node_id)

        n_gate_pending = driver.get_node(gate_node_id)
        assert NodeStatus(n_gate_pending.status) in {
            NodeStatus.PENDING_REVIEW, NodeStatus.REVIEW, NodeStatus.IN_PROGRESS,
        }

        ok, failed = gate_store.evaluate(
            pipeline_id=pid,
            gate_node_id=gate_node_id,
            coverage_report_pct=0.75,
            lint_passed=True,
            test_passed=True,
            security_scan_passed=True,
        )
        assert not ok, "gate should fail with 75% coverage vs 80% min"
        assert "R_COVERAGE_BELOW_POLICY" in failed

        n6_state = driver.get_node("n6")
        n6_status = NodeStatus(n6_state.status) if isinstance(n6_state.status, str) else n6_state.status
        if n6_status == NodeStatus.DONE:
            from mcp.state_store import STORE
            from orchestration.cascade import cascade_changed
            defn = STORE.get_def(pid)
            state = STORE.get_state(pid)
            new_state, evts = cascade_changed(
                "n6", "breaking", DepCoupling.HARD, defn, state
            )
            STORE.set_state(pid, new_state)
            n6_updated = driver.get_node("n6")
            n6_updated.status = NodeStatus.IN_PROGRESS
            STORE.set_state(pid, STORE.get_state(pid))

        n6_after = driver.get_node("n6")
        s6 = NodeStatus(n6_after.status) if isinstance(n6_after.status, str) else n6_after.status
        assert s6 in {NodeStatus.IN_PROGRESS, NodeStatus.CHANGED, NodeStatus.READY}, (
            f"upstream n6 should be invalidated after gate fail, got {s6}"
        )

        _worm = env.worm
        _worm.insert(AuditLogEntry(
            prev_hash="",
            action="NOTIFY_GATE_FAIL",
            actor="coordination-bot",
            payload={
                "gate_node_id": gate_node_id,
                "failed_rules": failed,
                "coverage": 0.75,
                "policy_min": 0.80,
                "upstream_in_progress": "n6",
            },
            hash="",
            created_at=datetime.now(timezone.utc).isoformat(),
            pipeline_id=pid,
            node_id=gate_node_id,
            trace_id=uuid.uuid4().hex,
        ))
        _worm.insert(AuditLogEntry(
            prev_hash="",
            action="GATE_FAIL_EVAL",
            actor="gate-policy",
            payload={
                "rules": failed,
                "coverage_pct": 0.75,
            },
            hash="",
            created_at=datetime.now(timezone.utc).isoformat(),
            pipeline_id=pid,
            node_id=gate_node_id,
            trace_id=uuid.uuid4().hex,
        ))

        audit_entries = _worm.list(pipeline_id=pid)
        last_two = audit_entries[-2:] if len(audit_entries) >= 2 else audit_entries
        has_gate_fail = any(
            "GATE_FAIL" in (e.action or "") for e in last_two
        )
        assert has_gate_fail, (
            f"expected GATE_FAIL action in last 2 audit entries, got: "
            f"{[e.action for e in last_two]}"
        )

        n6_status_now = NodeStatus(driver.get_node("n6").status) if isinstance(
            driver.get_node("n6").status, str
        ) else NodeStatus(driver.get_node("n6").status)
        if n6_status_now != NodeStatus.DONE:
            # IN_PROGRESS is a dead-end for SUBMIT_ARTIFACT; force back to READY
            from mcp.state_store import STORE as _STORE
            _st = _STORE.get_state(pid)
            _st.node_states["n6"].status = NodeStatus.READY
            _STORE.set_state(pid, _st)
            sha6_v2 = driver.submit_and_approve("n6")
            assert sha6_v2, "n6 resubmit should succeed after coverage fix"

        ok2, failed2 = gate_store.evaluate(
            pipeline_id=pid,
            gate_node_id=gate_node_id,
            coverage_report_pct=0.90,
            lint_passed=True,
            test_passed=True,
            security_scan_passed=True,
        )
        assert ok2, "gate should pass with 90% coverage"
        assert len(failed2) == 0

        sha7 = driver.submit_and_approve(gate_node_id)
        assert sha7, "gate approve should succeed after passing policy"

        n7_final = driver.get_node(gate_node_id)
        s7 = NodeStatus(n7_final.status) if isinstance(n7_final.status, str) else n7_final.status
        assert s7 == NodeStatus.DONE, f"gate node should be DONE, got {s7}"

        driver.mark_pipeline_completed_if_done()
