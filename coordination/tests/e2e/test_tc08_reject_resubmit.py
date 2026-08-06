from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from orchestration.models import NodeStatus
from tests.e2e._util import HappyPathDriver


class TestTC08RejectResubmit:
    def test_reject_then_resubmit_success(self, env):
        driver = HappyPathDriver(env)
        ready_roots = driver.create_pipeline("fullstack")
        assert "n1" in ready_roots

        bad_content = b"leaked credentials: AKIAIOSFODNN7EXAMPLE"
        result = driver.reject_reason_expected(
            "n1",
            bad_content,
            "R_SECRET_SCAN",
        )
        assert result.get("verdict") == "reject" or result.get("rejected_by")

        n1_after_reject = driver.get_node("n1")
        s = NodeStatus(n1_after_reject.status) if isinstance(n1_after_reject.status, str) else n1_after_reject.status
        assert s == NodeStatus.READY, f"after reject node should reset to ready, got {s}"

        sha1 = driver.submit_and_approve("n1")
        assert sha1, "resubmit after fix should succeed"

        n1_done = driver.get_node("n1")
        assert NodeStatus(n1_done.status) == NodeStatus.DONE
