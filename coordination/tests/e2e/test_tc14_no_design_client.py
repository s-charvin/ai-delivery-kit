from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from orchestration.models import NodeStatus
from tests.e2e._util import HappyPathDriver


class TestTC14NoDesignClient:
    def test_no_design_roles_client_ui_ready_after_n2(self, env):
        driver = HappyPathDriver(env)
        ready_roots = driver.create_pipeline("no_design_client")
        assert "n1" in ready_roots

        from mcp.state_store import STORE
        defn = STORE.get_def(driver.pid)
        node_types = {n.node_type for n in defn.nodes}
        node_ids = {n.node_id for n in defn.nodes}

        assert "design_asset" not in node_types, "design role absent should prune design_asset"
        assert "n3" not in node_ids, "n3 design_asset should be removed after materialize"

        n4_def = None
        for n in defn.nodes:
            if n.node_id == "n4":
                n4_def = n
                break
        if n4_def:
            upstreams = {d.upstream for d in n4_def.deps}
            assert "n3" not in upstreams, (
                "n4 deps should exclude absent n3 after materialize"
            )

        sha1 = driver.submit_and_approve("n1")
        assert sha1

        sha2 = driver.submit_and_approve("n2")
        assert sha2

        n4 = driver.get_node("n4")
        s = NodeStatus(n4.status) if isinstance(n4.status, str) else n4.status
        assert s in {NodeStatus.READY, NodeStatus.PENDING_REVIEW}, (
            f"client_ui n4 should be ready after n2 (design is absent/if_present), got {s}"
        )

        sha4 = driver.submit_and_approve("n4")
        assert sha4, "n4 should approve successfully"

        n4_done = driver.get_node("n4")
        assert NodeStatus(n4_done.status) == NodeStatus.DONE
