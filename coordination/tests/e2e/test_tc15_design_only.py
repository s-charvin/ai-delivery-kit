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

from config.constants import PARTICIPATION_PROFILES
from orchestration.materialize import materialize_pipeline
from orchestration.models import (
    ClassificationLevel,
    NodeDef,
    NodeStatus,
    PipelineDefinition,
    PipelineStatus,
)
from mcp.server import _bootstrap_state
from mcp.state_store import STORE
from tests.e2e._util import HappyPathDriver


class TestTC15DesignOnly:
    """TC-15: design_only profile — allow_non_product_root, 仅 design_asset 节点。"""

    def test_tc15_design_only_pipeline(self, env, monkeypatch):
        pid = f"pipe-design-{uuid.uuid4().hex[:8]}"
        design_node = NodeDef(
            node_id="d1",
            node_type="design_asset",
            role_assignments=[],
            deps=[],
        )
        profile = PARTICIPATION_PROFILES["design_only"].model_copy(deep=True)

        assert profile.allow_non_product_root is True
        assert profile.allow_design_as_root is True
        assert "design_asset" in profile.core_node_types
        assert "design" in profile.roles_present

        base_def = PipelineDefinition(
            id=pid,
            name="test-design-only",
            nodes=[design_node],
            profile=profile,
            root_product_node_id="d1",
        )
        mat_def = materialize_pipeline(base_def, profile)

        # After materialize, only design_asset node should remain
        node_types = [n.node_type for n in mat_def.nodes]
        assert node_types == ["design_asset"], (
            f"design_only should keep only design_asset, got {node_types}"
        )

        state, ready_roots = _bootstrap_state(mat_def)
        STORE.register(mat_def, state)

        driver = HappyPathDriver(env)
        driver.pid = pid
        assert "d1" in ready_roots

        # Submit design_asset with figma URL
        figma_url = "https://figma.com/file/xxx/design-v1"
        content = f"# Design Spec\n\nFigma: {figma_url}\n\nWireframes and mockups.".encode("utf-8")

        sha1 = driver.submit_and_approve(
            "d1",
            content=content,
            classification=int(ClassificationLevel.INTERNAL),
            change_class="compatible",
        )
        assert sha1, "d1 design_asset approve should succeed"

        d1 = driver.get_node("d1")
        s1 = NodeStatus(d1.status) if isinstance(d1.status, str) else d1.status
        assert s1 == NodeStatus.DONE, f"d1 should be DONE, got {s1}"

        # Pipeline should be completed (design_asset is the only core node)
        driver.mark_pipeline_completed_if_done()
        state = driver.get_state()
        assert state.status == PipelineStatus.COMPLETED, (
            f"pipeline should be COMPLETED, got {state.status}"
        )

        # Audit should have design_asset done record
        audit_entries = env.worm.list(pipeline_id=pid)
        assert len(audit_entries) >= 1
        has_done = any(
            "APPROVE" in (e.action or "") or "DONE" in (e.action or "")
            for e in audit_entries
        )
        assert has_done, (
            f"audit should have design_asset done record, actions: "
            f"{[e.action for e in audit_entries]}"
        )

        # Verify figma URL HEAD reachable (mock httpx 200) → external_health not degraded
        import httpx

        def mock_figma_200(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, text="OK")

        mock_client = httpx.Client(
            transport=httpx.MockTransport(mock_figma_200),
        )

        resp = mock_client.head(figma_url)
        assert resp.status_code == 200, (
            f"figma URL HEAD should be reachable (mock 200), got {resp.status_code}"
        )
        mock_client.close()

        # external_health monitor should NOT trigger deprecated for reachable URL
        from monitoring.external_health import ExternalHealthMonitor

        mon = ExternalHealthMonitor(
            targets=[{"node_id": "d1", "url": figma_url, "pipeline_id": pid}],
        )
        mon._client = httpx.AsyncClient(
            transport=httpx.MockTransport(mock_figma_200),
        )
        results = asyncio.run(mon.run_once())
        assert results.get("d1") is True, (
            f"external_health should report d1 as healthy, got {results}"
        )
        snap = mon.state_snapshot()
        for t in snap["targets"]:
            assert not t["deprecated"], (
                f"design_asset should not be deprecated when figma URL is reachable"
            )
