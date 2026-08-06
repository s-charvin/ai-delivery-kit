from __future__ import annotations

import asyncio
import json
import sys
import uuid
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from monitoring.langfuse_client import LangfuseClient
from orchestration.models import NodeStatus, PipelineStatus
from tests.e2e._util import HappyPathDriver


class TestTC12LangfuseDegrade:
    """TC-12: Langfuse 降级 WAL — 503 时全链路仍成功，WAL 不丢数据，恢复后 replay 清空。"""

    async def test_tc12_langfuse_degrade_and_replay(self, env):
        import httpx

        wal_dir = env.tmp / "wal"
        wal_dir.mkdir(parents=True, exist_ok=True)

        # LangfuseClient with mock 503 transport
        def mock_503(request: httpx.Request) -> httpx.Response:
            return httpx.Response(503, text="Service Unavailable")

        client_503 = httpx.AsyncClient(
            base_url="http://mock-langfuse",
            transport=httpx.MockTransport(mock_503),
        )
        langfuse = LangfuseClient(
            base_url="http://mock-langfuse",
            public_key="pk-test",
            secret_key="sk-test",
        )
        langfuse.client = client_503
        langfuse.WAL_DIR = wal_dir

        assert langfuse.enabled, "LangfuseClient should be enabled"

        # Run happy path; after each approve send a span that will fail → WAL
        driver = HappyPathDriver(env)
        driver.create_pipeline("fullstack")
        pid = driver.pid

        span_names = ["submit", "review", "approve", "cascade", "audit_write"]
        for i, node_id in enumerate(["n1", "n2", "n3", "n5", "n4"]):
            sha = driver.submit_and_approve(node_id)
            assert sha, f"{node_id} approve should succeed even with Langfuse down"

            span = langfuse.trace_span(
                name=span_names[i],
                span_class="mcp_call",
                metadata={
                    "pipeline_id": pid,
                    "node_id": node_id,
                    "action": "submit_approve",
                },
                trace_id=uuid.uuid4().hex,
            )
            await langfuse.send_span(span)

        # Assert pipeline still active and progressing
        state = driver.get_state()
        assert state.status in {PipelineStatus.ACTIVE, PipelineStatus.COMPLETED}

        # Assert WAL file non-empty (>= 5 lines)
        wal_files = list(wal_dir.glob("langfuse-*.jsonl"))
        assert len(wal_files) >= 1, f"expected WAL file, got {wal_files}"
        total_lines = 0
        for wf in wal_files:
            with wf.open("r") as f:
                total_lines += sum(1 for line in f if line.strip())
        assert total_lines >= 5, (
            f"expected >= 5 WAL lines during degrade, got {total_lines}"
        )

        lines_before = total_lines

        # Restore network (mock 200) → replay
        def mock_200(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"status": "ok"})

        client_200 = httpx.AsyncClient(
            base_url="http://mock-langfuse",
            transport=httpx.MockTransport(mock_200),
        )
        langfuse.client = client_200

        sent, moved = await langfuse._replay_once()

        assert sent >= 5, (
            f"expected >= 5 spans replayed, got sent={sent}, moved={moved}"
        )

        # Assert WAL decreased or emptied
        wal_files_after = list(wal_dir.glob("langfuse-*.jsonl"))
        total_lines_after = 0
        for wf in wal_files_after:
            with wf.open("r") as f:
                total_lines_after += sum(1 for line in f if line.strip())
        assert total_lines_after < lines_before, (
            f"WAL should decrease after replay: before={lines_before}, after={total_lines_after}"
        )

        await client_503.aclose()
        await client_200.aclose()
