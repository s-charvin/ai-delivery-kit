from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from orchestration.models import NodeStatus, PipelineStatus
from tests.e2e._util import HappyPathDriver


class TestTC13ServerOnly:
    def test_server_only_no_ghost_nodes(self, env):
        driver = HappyPathDriver(env)
        ready_roots = driver.create_pipeline("server_only")
        assert "n1" in ready_roots or len(ready_roots) >= 1

        from mcp.state_store import STORE
        defn = STORE.get_def(driver.pid)
        node_ids = {n.node_id for n in defn.nodes}
        node_types = {n.node_type for n in defn.nodes}

        fullstack_nodes = {"n1", "n2", "n3", "n4", "n5", "n6", "n7"}
        server_only_count = len(defn.nodes)
        assert server_only_count <= len(fullstack_nodes), (
            f"server_only should have fewer nodes than fullstack, got {server_only_count}"
        )
        assert "design_asset" not in node_types, (
            "server_only profile should remove design_asset node"
        )
        assert "client_ui_impl" not in node_types, (
            "server_only profile should remove client_ui_impl node"
        )

        core_nodes_expected = ["n1", "n2", "n5", "n6", "n7"]
        for nid in core_nodes_expected:
            assert nid in node_ids, f"core node {nid} should remain in server_only"

        sha1 = driver.submit_and_approve("n1")
        assert sha1
        sha2 = driver.submit_and_approve("n2")
        assert sha2
        sha5 = driver.submit_and_approve("n5")
        assert sha5
        sha6 = driver.submit_and_approve("n6")
        assert sha6
        sha7 = driver.submit_and_approve("n7")
        assert sha7

        driver.mark_pipeline_completed_if_done()
        state = driver.get_state()
        assert state.status in {PipelineStatus.COMPLETED, PipelineStatus.ACTIVE}
        assert driver.is_pipeline_completed()
