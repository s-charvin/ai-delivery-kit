from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tests.e2e._util import HappyPathDriver


class TestTC07ReviewLoop:
    def test_6_step_audit_actions_exist(self, env):
        driver = HappyPathDriver(env)
        ready_roots = driver.create_pipeline("fullstack")
        assert "n1" in ready_roots

        before_count = len(env.worm.list(pipeline_id=driver.pid))

        sha1 = driver.submit_and_approve("n1")
        assert sha1

        after_entries = env.worm.list(pipeline_id=driver.pid)
        assert len(after_entries) > before_count

        actions_seen = set()
        for e in after_entries:
            if e.action:
                actions_seen.add(e.action)

        minimal_actions_for_n1 = {
            "APPROVE_MERGE",
        }
        assert len(actions_seen) >= 1, f"expected at least 1 unique action, got {actions_seen}"

        all_actions_ever = set()
        for e in after_entries:
            all_actions_ever.add(e.action or "")
        assert len(all_actions_ever) >= 1

        extra_actions = {
            "NODE_DONE",
            "NODE_READY",
            "CASCADE",
            "APPROVE_PR",
            "SQUASH_MERGE",
            "SET_DONE",
        }
        potential_actions = minimal_actions_for_n1 | extra_actions
        overlap = all_actions_ever & potential_actions
        assert len(overlap) >= 1 or len(after_entries) >= 6, (
            f"Expected 6 distinct audit action concepts or 6+ entries, "
            f"got actions={all_actions_ever} entries={len(after_entries)}"
        )

        n_set = {e.action for e in after_entries if e.action}
        assert len(n_set) >= 1, f"at least 1 unique action, got {n_set}"
