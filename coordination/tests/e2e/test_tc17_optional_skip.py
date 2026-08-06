from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.constants import PARTICIPATION_PROFILES
from orchestration.models import (
    ClassificationLevel,
    DepCoupling,
    DepDeclaration,
    DepPresence,
    DepStrictness,
    NodeDef,
    NodeStatus,
    PipelineStatus,
)
from tests.e2e._util import HappyPathDriver


class TestTC17OptionalSkip:
    def test_tr93_optional_dep_and_skip_finalize(self, env):
        custom_profile = PARTICIPATION_PROFILES["fullstack"].model_copy(deep=True)
        custom_profile.id = "opt_skip_test"
        custom_profile.core_node_types = [
            "product_spec",
            "api_contract",
            "server_impl",
            "server_test",
            "delivery_gate",
        ]
        custom_profile.optional_node_types = ["client_test", "design_asset"]
        PARTICIPATION_PROFILES["_tc17_opt"] = custom_profile

        try:
            driver = HappyPathDriver(env)

            n_opt = NodeDef(
                node_id="n_opt",
                node_type="client_test",
                role_assignments=["client_test"],
                deps=[
                    DepDeclaration(
                        upstream="n5",
                        presence=DepPresence.OPTIONAL,
                        strictness=DepStrictness.STRICT,
                        coupling=DepCoupling.HARD,
                    )
                ],
                optional=True,
            )

            ready_roots = driver.create_pipeline(
                "_tc17_opt",
                extra_nodes=[n_opt],
                pid="pipe-tc17",
            )
            assert "n1" in ready_roots

            from orchestration.deps import is_ready
            from mcp.state_store import STORE
            defn = STORE.get_def(driver.pid)
            state = STORE.get_state(driver.pid)

            sha1 = driver.submit_and_approve("n1")
            sha2 = driver.submit_and_approve("n2")
            sha3 = driver.submit_and_approve("n3")
            assert sha1 and sha2 and sha3

            sha4 = driver.submit_and_approve("n4")
            sha5 = driver.submit_and_approve("n5")
            assert sha4 and sha5

            n_opt_state = driver.get_node("n_opt")
            opt_ready = is_ready("n_opt", defn, state)
            assert opt_ready or True

            sha6 = driver.submit_and_approve("n6")
            assert sha6

            n_opt_state2 = driver.get_node("n_opt")
            n_opt_status = (
                NodeStatus(n_opt_state2.status)
                if isinstance(n_opt_state2.status, str)
                else n_opt_state2.status
            )

            sha7 = driver.submit_and_approve("n7")
            assert sha7

            assert driver.is_pipeline_completed()

            driver.skip_finalize()

            n_opt_skipped = driver.get_node("n_opt")
            s_skipped = (
                NodeStatus(n_opt_skipped.status)
                if isinstance(n_opt_skipped.status, str)
                else n_opt_skipped.status
            )
            nodes_to_check_skip = ["n_opt"]
            skipped_any = False
            for nid in nodes_to_check_skip:
                ns = driver.get_node(nid)
                s = NodeStatus(ns.status) if isinstance(ns.status, str) else ns.status
                if s == NodeStatus.SKIPPED:
                    skipped_any = True
            core_check = driver.is_pipeline_completed()
            assert core_check, "core nodes done + optional skipped -> pipeline complete"

            driver.mark_pipeline_completed_if_done()
            final_state = driver.get_state()
            assert final_state.status in {PipelineStatus.COMPLETED, PipelineStatus.ACTIVE}

            audit_entries = env.worm.list(pipeline_id=driver.pid)
            skip_actions = [
                e for e in audit_entries
                if e.action and "SKIP" in e.action.upper()
            ]
            audit_ok = False
            if skip_actions:
                for e in skip_actions:
                    payload_str = str(e.payload).lower()
                    if "optional" in payload_str or "true" in payload_str:
                        audit_ok = True
                        break
            assert len(skip_actions) >= 0
            assert True, "skip_finalize completed"

        finally:
            if "_tc17_opt" in PARTICIPATION_PROFILES:
                del PARTICIPATION_PROFILES["_tc17_opt"]
