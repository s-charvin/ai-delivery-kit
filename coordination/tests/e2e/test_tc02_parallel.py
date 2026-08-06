from __future__ import annotations

import asyncio
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from orchestration.models import NodeStatus
from tests.e2e._util import HappyPathDriver


class TestTC02Parallel:
    def test_parallel_submit_no_deadlock(self, env):
        driver = HappyPathDriver(env)
        ready_roots = driver.create_pipeline("fullstack")
        assert "n1" in ready_roots

        sha1 = driver.submit_and_approve("n1")
        assert sha1

        n2 = driver.get_node("n2")
        n3 = driver.get_node("n3")
        assert NodeStatus(n2.status) in {NodeStatus.READY, NodeStatus.PENDING_REVIEW}
        assert NodeStatus(n3.status) in {NodeStatus.READY, NodeStatus.PENDING_REVIEW}

        def _do_n2():
            return driver.submit_and_approve("n2")

        def _do_n3():
            return driver.submit_and_approve("n3")

        with ThreadPoolExecutor(max_workers=2) as pool:
            futs = [pool.submit(_do_n2), pool.submit(_do_n3)]
            results = [f.result(timeout=30) for f in as_completed(futs, timeout=30)]

        for r in results:
            assert r, "parallel submit should both succeed"

        n2_done = driver.get_node("n2")
        n3_done = driver.get_node("n3")
        assert NodeStatus(n2_done.status) == NodeStatus.DONE
        assert NodeStatus(n3_done.status) == NodeStatus.DONE

        n4 = driver.get_node("n4")
        n5 = driver.get_node("n5")
        assert NodeStatus(n5.status) in {NodeStatus.READY, NodeStatus.PENDING_REVIEW, NodeStatus.DONE, NodeStatus.BLOCKED}

        sha5 = driver.submit_and_approve("n5")
        assert sha5
        n6 = driver.get_node("n6")
        assert NodeStatus(n6.status) in {NodeStatus.READY, NodeStatus.PENDING_REVIEW}

        sha4 = driver.submit_and_approve("n4")
        sha6 = driver.submit_and_approve("n6")
        assert sha4 and sha6

        sha7 = driver.submit_and_approve("n7")
        assert sha7
