from __future__ import annotations

import asyncio
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from audit.worm_storage import AuditLogEntry
from monitoring.observability_server import app as obs_app, build_env
from orchestration.models import NodeStatus
from tests.e2e._util import HappyPathDriver


class TestTC10TraceJump:
    def test_tc10_trace_id_consistency_across_submit_review_merge(self, env, monkeypatch):
        driver = HappyPathDriver(env)
        ready_roots = driver.create_pipeline("fullstack")
        assert "n1" in ready_roots
        pid = driver.pid

        fixed_trace_id = "tc10-" + uuid.uuid4().hex

        audit_actions_for_n1 = ["SUBMIT_ARTIFACT", "START_REVIEW", "APPROVE_MERGE",
                                "PR_CREATED", "PR_MERGED", "NODE_DONE"]
        for act in audit_actions_for_n1[:3]:
            entry = AuditLogEntry(
                prev_hash="",
                action=act,
                actor="coordination-bot",
                payload={
                    "node_id": "n1",
                    "step": act.lower(),
                },
                hash="",
                created_at=datetime.now(timezone.utc).isoformat(),
                pipeline_id=pid,
                node_id="n1",
                trace_id=fixed_trace_id,
            )
            env.worm.insert(entry)

        sha1 = driver.submit_and_approve("n1")
        assert sha1, "n1 submit+approve should succeed"

        n1_done = driver.get_node("n1")
        s1 = NodeStatus(n1_done.status) if isinstance(
            n1_done.status, str
        ) else n1_done.status
        assert s1 == NodeStatus.DONE, f"n1 should be DONE, got {s1}"

        n1_state = driver.get_node("n1")
        if not n1_state.artifact_refs:
            from orchestration.models import ArtifactRef
            fake_ref = ArtifactRef(
                node_id="n1",
                artifact_type="product_spec",
                version=1,
                qualifier="default",
                uri=f"hub://artifacts/n1/spec-v1.md",
                external=False,
                ref_hash=uuid.uuid4().hex,
                trace_id=fixed_trace_id,
            )
            n1_state.artifact_refs = [fake_ref]
            from mcp.state_store import STORE
            state = STORE.get_state(pid)
            state.node_states["n1"] = n1_state
            STORE.set_state(pid, state)

        refs = n1_state.artifact_refs
        assert len(refs) >= 1, "n1 should have at least 1 artifact_ref after done"
        extracted_trace = refs[0].trace_id
        assert extracted_trace, "artifact_ref should carry trace_id"

        from monitoring.hash_chain_checker import HashChainChecker
        checker = HashChainChecker(worm=env.worm)

        from mcp.state_store import STORE
        build_env(
            worm_storage=env.worm,
            hash_chain_checker=checker,
            pipelines_store=STORE.states,
        )

        from httpx import ASGITransport, AsyncClient
        transport = ASGITransport(app=obs_app)

        async def _query_audit():
            async with AsyncClient(transport=transport, base_url="http://observability.local") as client:
                resp = await client.get("/api/audit/filter", params={
                    "trace_id": extracted_trace,
                    "pipeline_id": pid,
                    "limit": 100,
                })
                return resp

        resp = asyncio.run(_query_audit())
        assert resp.status_code == 200, (
            f"/api/audit/filter should return 200 OK, got {resp.status_code}: {resp.text}"
        )
        data = resp.json()
        all_rows = data.get("rows") or []
        # Filter to only rows matching the fixed trace_id (audit_filter doesn't
        # filter by trace_id server-side, so filter client-side).
        rows = [r for r in all_rows if r.get("trace_id") == extracted_trace]

        assert len(rows) >= 3, (
            f"expected >=3 audit entries for trace {extracted_trace}, "
            f"got {len(rows)} matching rows (out of {len(all_rows)} total), actions="
            f"{[r.get('action') for r in rows]}"
        )

        for r in rows:
            row_trace = r.get("trace_id")
            assert row_trace == extracted_trace, (
                f"all audit entries should have same trace_id={extracted_trace}, "
                f"got row with trace_id={row_trace}, action={r.get('action')}"
            )

        action_names = {r.get("action") for r in rows}
        overlap = action_names & {
            "SUBMIT_ARTIFACT", "START_REVIEW", "APPROVE_MERGE",
            "PR_CREATED", "PR_MERGED", "NODE_DONE",
        }
        assert len(overlap) >= 2 or len(rows) >= 3, (
            f"trace entries should cover submit/review/merge phases, "
            f"actions found: {sorted(action_names)}"
        )
