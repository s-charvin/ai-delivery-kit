from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from monitoring.observability_server import (
    _SSE_QUEUE,
    app as obs_app,
    build_env,
    sse_push,
)
from tests.e2e._util import HappyPathDriver


class TestTC11SSERealtime:
    """TC-11: SSE 实时推送 <1s — push 10 state_changed events, assert P95 < 1s."""

    async def test_tc11_sse_p95_under_1s(self, env):
        from httpx import ASGITransport, AsyncClient

        driver = HappyPathDriver(env)
        driver.create_pipeline("fullstack")
        pid = driver.pid

        build_env(
            worm_storage=env.worm,
            pipelines_store=__import__("mcp.state_store", fromlist=["STORE"]).STORE.states,
        )

        # Clear any residual queue items
        while not _SSE_QUEUE.empty():
            try:
                _SSE_QUEUE.get_nowait()
            except Exception:
                break

        push_count = 10
        received: list[dict] = []
        latencies: list[float] = []

        transport = ASGITransport(app=obs_app)

        async with AsyncClient(transport=transport, base_url="http://obs.local") as client:
            async with client.stream("GET", "/api/sse/events") as resp:
                assert resp.status_code == 200

                async def push_events():
                    """Simulate 10 MCP state changes, each pushing an SSE event."""
                    for i in range(push_count):
                        push_time = time.time()
                        await sse_push("state_changed", {
                            "seq": i,
                            "pipeline_id": pid,
                            "node_id": f"n{i % 7 + 1}",
                            "push_time": push_time,
                        })
                        await asyncio.sleep(0.02)

                push_task = asyncio.create_task(push_events())

                buf = ""
                try:
                    async for chunk in resp.aiter_text():
                        buf += chunk
                        while "\n\n" in buf:
                            raw_msg, buf = buf.split("\n\n", 1)
                            data_payload = None
                            for line in raw_msg.split("\n"):
                                if line.startswith("data: "):
                                    data_payload = line[6:]
                                    break
                            if data_payload is None:
                                continue
                            try:
                                data = json.loads(data_payload)
                            except Exception:
                                continue
                            if not isinstance(data, dict) or "push_time" not in data:
                                continue
                            recv_time = time.time()
                            latency = recv_time - float(data["push_time"])
                            latencies.append(latency)
                            received.append(data)
                            if len(received) >= push_count:
                                raise asyncio.CancelledError
                except asyncio.CancelledError:
                    pass

                try:
                    await asyncio.wait_for(push_task, timeout=5)
                except asyncio.TimeoutError:
                    pass

        assert len(received) >= push_count, (
            f"expected >= {push_count} SSE events, got {len(received)}"
        )

        assert len(latencies) >= push_count, (
            f"expected >= {push_count} latency samples, got {len(latencies)}"
        )

        latencies.sort()
        p95_idx = min(int(len(latencies) * 0.95), len(latencies) - 1)
        p95 = latencies[p95_idx]
        assert p95 < 1.0, f"P95 SSE latency {p95:.4f}s >= 1s threshold"
