from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from orchestration.models import NodeStatus, PipelineStatus
from tests.e2e._util import HappyPathDriver
from utils.hashing import hash_chain_validate


class TestTC01HappyPath:
    def test_tr91_tr94_fullstack_happy_path(self, env):
        driver = HappyPathDriver(env)
        ready_roots = driver.create_pipeline("fullstack")
        assert "n1" in ready_roots, "n1 product_spec should be ready root"

        sha1 = driver.submit_and_approve("n1")
        assert sha1, "n1 approve should succeed"
        n1 = driver.get_node("n1")
        assert NodeStatus(n1.status) == NodeStatus.DONE

        n2 = driver.get_node("n2")
        n3 = driver.get_node("n3")
        assert NodeStatus(n2.status) in {NodeStatus.READY, NodeStatus.PENDING_REVIEW}, "n2 api_contract should be ready after n1"
        assert NodeStatus(n3.status) in {NodeStatus.READY, NodeStatus.PENDING_REVIEW}, "n3 design_asset should be ready after n1"

        sha2 = driver.submit_and_approve("n2")
        sha3 = driver.submit_and_approve("n3")
        assert sha2, "n2 approve should succeed"
        assert sha3, "n3 approve should succeed"

        n5 = driver.get_node("n5")
        n4 = driver.get_node("n4")
        assert NodeStatus(n5.status) in {NodeStatus.READY, NodeStatus.PENDING_REVIEW, NodeStatus.BLOCKED}
        assert NodeStatus(n4.status) in {NodeStatus.READY, NodeStatus.PENDING_REVIEW, NodeStatus.BLOCKED}

        sha5 = driver.submit_and_approve("n5")
        assert sha5, "n5 server_impl approve should succeed"
        n6 = driver.get_node("n6")
        assert NodeStatus(n6.status) in {NodeStatus.READY, NodeStatus.PENDING_REVIEW}, "n6 server_test should be ready after n5"

        sha4 = driver.submit_and_approve("n4")
        sha6 = driver.submit_and_approve("n6")
        assert sha4, "n4 client_ui approve should succeed"
        assert sha6, "n6 server_test approve should succeed"

        n7 = driver.get_node("n7")
        assert NodeStatus(n7.status) in {NodeStatus.READY, NodeStatus.PENDING_REVIEW}, "n7 delivery should be ready after n4+n6"

        sha7 = driver.submit_and_approve("n7")
        assert sha7, "n7 approve should succeed"

        driver.mark_pipeline_completed_if_done()
        state = driver.get_state()
        assert state.status in {PipelineStatus.COMPLETED, PipelineStatus.ACTIVE}

        audit_entries = env.worm.list(pipeline_id=driver.pid)
        assert len(audit_entries) >= 7, f"expected 7+ audit entries, got {len(audit_entries)}"

        valid, bad_idx = hash_chain_validate(audit_entries)
        assert valid, f"hash chain invalid at index {bad_idx}"

        for e in audit_entries:
            assert e.trace_id, f"audit entry {e.id} missing trace_id (action={e.action})"
