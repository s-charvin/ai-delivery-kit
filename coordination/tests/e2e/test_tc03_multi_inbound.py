from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from orchestration.models import NodeStatus
from tests.e2e._util import HappyPathDriver


class TestTC03MultiInbound:
    def test_n4_client_ui_multi_deps(self, env):
        driver = HappyPathDriver(env)
        ready_roots = driver.create_pipeline("fullstack")
        assert "n1" in ready_roots

        sha1 = driver.submit_and_approve("n1")
        assert sha1

        sha2 = driver.submit_and_approve("n2")
        assert sha2

        n4 = driver.get_node("n4")
        assert NodeStatus(n4.status) == NodeStatus.BLOCKED, (
            f"n4 should be blocked until n3 also done, got {n4.status}"
        )

        sha3 = driver.submit_and_approve("n3")
        assert sha3

        n4_after = driver.get_node("n4")
        s = NodeStatus(n4_after.status) if isinstance(n4_after.status, str) else n4_after.status
        assert s in {NodeStatus.READY, NodeStatus.PENDING_REVIEW}, (
            f"n4 should be ready after n2+n3 both done, got {s}"
        )

        sha4 = driver.submit_and_approve("n4")
        assert sha4
        n4_final = driver.get_node("n4")
        assert NodeStatus(n4_final.status) == NodeStatus.DONE
