from __future__ import annotations

import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from audit.merge_approve import E_HUMAN_REVIEW_REQUIRED
from audit.worm_storage import AuditLogEntry
from config.constants import PARTICIPATION_PROFILES
from orchestration.materialize import materialize_pipeline
from orchestration.models import (
    ClassificationLevel,
    DepCoupling,
    DepDeclaration,
    DepPresence,
    DepStrictness,
    NodeDef,
    NodeStatus,
    PipelineDefinition,
)
from mcp.server import _bootstrap_state
from mcp.state_store import STORE
from tests.e2e._util import HappyPathDriver


class TestTC16TechDebt:
    """TC-16: tech_debt 热修 — confidential 强制 2 人审批, breaking change needs_human。"""

    def test_tc16_tech_debt_hotfix_human_review(self, env):
        pid = f"pipe-techdebt-{uuid.uuid4().hex[:8]}"

        server_node = NodeDef(
            node_id="s1",
            node_type="server_impl",
            role_assignments=[],
            deps=[],
            classification=ClassificationLevel.CONFIDENTIAL,
        )
        gate_node = NodeDef(
            node_id="g1",
            node_type="delivery_gate",
            role_assignments=[],
            deps=[
                DepDeclaration(
                    upstream="s1",
                    presence=DepPresence.REQUIRED,
                    strictness=DepStrictness.STRICT,
                    coupling=DepCoupling.HARD,
                )
            ],
        )
        profile = PARTICIPATION_PROFILES["tech_debt"].model_copy(deep=True)

        assert profile.allow_non_product_root is True
        assert profile.tech_debt_hotfix_mode is True
        assert "server_impl" in profile.roles_present
        assert "ops" in profile.roles_present

        base_def = PipelineDefinition(
            id=pid,
            name="test-tech-debt-hotfix",
            nodes=[server_node, gate_node],
            profile=profile,
            root_product_node_id="s1",
        )
        mat_def = materialize_pipeline(base_def, profile)

        node_types = [n.node_type for n in mat_def.nodes]
        assert "server_impl" in node_types
        assert "delivery_gate" in node_types
        assert "product_spec" not in node_types, (
            "tech_debt should not have product_spec"
        )

        state, ready_roots = _bootstrap_state(mat_def)
        STORE.register(mat_def, state)

        driver = HappyPathDriver(env)
        driver.pid = pid
        assert "s1" in ready_roots

        # Mark business_source=incident in audit
        env.worm.insert(AuditLogEntry(
            prev_hash="",
            action="INCIDENT_HOTFIX",
            actor="ops-bot",
            payload={
                "pipeline_id": pid,
                "business_source": "incident",
                "hotfix_mode": True,
                "classification": int(ClassificationLevel.CONFIDENTIAL),
            },
            hash="",
            created_at=datetime.now(timezone.utc).isoformat(),
            pipeline_id=pid,
            node_id="s1",
            trace_id=uuid.uuid4().hex,
        ))

        # Submit server_impl with breaking change (hotfix)
        content = b"# Hotfix: patch critical auth bypass\n\nBreaking change to auth module."
        pr_id, final_path = driver._submit_to_hub(
            "s1", content, int(ClassificationLevel.CONFIDENTIAL), "breaking",
            None, None, None,
        )
        STORE.set_pending_pr("s1", pr_id)
        driver._submitted_prs["s1"] = pr_id
        driver._submit_transition("s1")

        ns = driver.get_node("s1")
        s = NodeStatus(ns.status) if isinstance(ns.status, str) else ns.status
        assert s == NodeStatus.PENDING_REVIEW, f"s1 should be pending_review, got {s}"

        driver._transition_node_status("s1", "START_REVIEW")
        cb = {final_path: content}
        review_result = driver._run_engine_review("s1", pr_id, cb)
        verdict = review_result["verdict"]
        assert verdict == "needs_human", (
            f"breaking + confidential should need human review, got verdict={verdict}, "
            f"checks={[c for c in review_result['checks'] if not c['pass']]}"
        )

        # Try approve with 1 human < required 2 → E_HUMAN_REVIEW_REQUIRED
        with pytest.raises(E_HUMAN_REVIEW_REQUIRED):
            driver.merge_service.approve(
                pipeline_id=pid,
                pr_id=pr_id,
                bot_actor="coordination-bot",
                human_approvals=1,
                required_humans=2,
                note="hotfix attempt 1/2",
            )

        # s1 should NOT be done yet
        ns_after_fail = driver.get_node("s1")
        s_after = NodeStatus(ns_after_fail.status) if isinstance(
            ns_after_fail.status, str
        ) else ns_after_fail.status
        assert s_after != NodeStatus.DONE, (
            f"s1 should not be DONE with insufficient human approvals, got {s_after}"
        )

        # Approve with 2 humans → success → done
        result = driver.merge_service.approve(
            pipeline_id=pid,
            pr_id=pr_id,
            bot_actor="coordination-bot",
            human_approvals=2,
            required_humans=2,
            note="hotfix approved 2/2",
        )
        assert result.get("commit_sha"), "approve should return commit_sha"

        ns_done = driver.get_node("s1")
        s_done = NodeStatus(ns_done.status) if isinstance(
            ns_done.status, str
        ) else ns_done.status
        assert s_done == NodeStatus.DONE, f"s1 should be DONE after 2 human approvals, got {s_done}"

        # Audit should have INCIDENT_HOTFIX marker
        audit_entries = env.worm.list(pipeline_id=pid)
        has_incident = any(
            "INCIDENT_HOTFIX" in (e.action or "") for e in audit_entries
        )
        assert has_incident, (
            f"audit should have INCIDENT_HOTFIX marker, actions: "
            f"{[e.action for e in audit_entries]}"
        )
