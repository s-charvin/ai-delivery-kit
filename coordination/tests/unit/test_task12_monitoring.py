from __future__ import annotations

import asyncio
import json
import shutil
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


BASE_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE_DIR))


DATA_ROOT = BASE_DIR / "data" / "test_task12"
if DATA_ROOT.exists():
    shutil.rmtree(DATA_ROOT, ignore_errors=True)
DATA_ROOT.mkdir(parents=True, exist_ok=True)


from audit.worm_storage import AuditLogEntry, WormStorage
from monitoring.alerting import AlertManager, ALERTS
from monitoring.cost import CostAggregator
from monitoring.external_health import ExternalHealthMonitor
from monitoring.hash_chain_checker import HashChainChecker
from monitoring.langfuse_client import LangfuseClient
from monitoring.observability_server import (
    SSE_EVENTS,
    app,
    build_env,
    sse_push,
    _SSE_QUEUE,
)


def _clear_queue(q: asyncio.Queue) -> None:
    while not q.empty():
        try:
            q.get_nowait()
        except Exception:
            break


@pytest.fixture
def temp_dir(tmp_path) -> Path:
    p = tmp_path / "t12"
    p.mkdir(parents=True, exist_ok=True)
    return p


@pytest.fixture
def wal_dir(temp_dir) -> Path:
    p = temp_dir / "wal"
    p.mkdir(parents=True, exist_ok=True)
    with patch.object(LangfuseClient, "WAL_DIR", p):
        yield p


@pytest.mark.unit
def test_tr12_1_langfuse_normal_and_offline(temp_dir, wal_dir):
    """TR-12.1 两次 TC-01：Langfuse 正常 vs 断网"""
    from monitoring import langfuse_client as lc_module
    original_wal = lc_module.LangfuseClient.WAL_DIR
    try:
        lc_module.LangfuseClient.WAL_DIR = wal_dir

        span_classes = list(LangfuseClient.SPAN_CLASSES)
        assert len(span_classes) == 8

        def _make_spans(client: LangfuseClient, trace_id: str) -> list[dict]:
            spans: list[dict] = []
            for i, sc in enumerate(span_classes):
                meta = {
                    "pipeline_id": "p1",
                    "node_id": f"n{i}",
                    "action": f"action-{sc}",
                    "actor": "actor-x",
                    "cost_usd": 0.1 * (i + 1),
                    "tool_name": f"tool_{sc}",
                }
                s = client.trace_span(
                    name=f"name-{sc}",
                    span_class=sc,
                    metadata=meta,
                    trace_id=trace_id,
                )
                spans.append(s)
            return spans

        mock_client_instance = MagicMock()
        normal_client = LangfuseClient(
            base_url="http://langfuse.example",
            public_key="pk-xxx",
            secret_key="sk-xxx",
        )
        normal_client.client = mock_client_instance

        good_resp = MagicMock()
        good_resp.status_code = 200
        mock_client_instance.post = AsyncMock(return_value=good_resp)

        trace1 = uuid.uuid4().hex
        spans_case1 = _make_spans(normal_client, trace1)
        assert len(spans_case1) == 8
        classes_found = {s["span_class"] for s in spans_case1}
        assert classes_found == set(span_classes)
        for s in spans_case1:
            for k in [
                "pipeline_id",
                "node_id",
                "action",
                "actor",
                "cost_usd",
                "tool_name",
            ]:
                assert k in s["metadata"]
            asyncio.run(normal_client.send_span(s))
        assert mock_client_instance.post.await_count == 8

        for f in wal_dir.glob("langfuse-*.jsonl"):
            if "failed-" in f.name:
                continue
            assert f.stat().st_size == 0, f"Normal 模式不应写入 WAL: {f.name}"

        offline_client = LangfuseClient(
            base_url="http://langfuse.example",
            public_key="pk-xxx",
            secret_key="sk-xxx",
        )
        bad_client = MagicMock()

        async def _bad_post(*args, **kwargs):
            r = MagicMock()
            r.status_code = 503
            raise RuntimeError("network down")

        bad_client.post = _bad_post
        offline_client.client = bad_client

        trace2 = uuid.uuid4().hex
        spans_case2 = _make_spans(offline_client, trace2)
        assert len(spans_case2) == 8
        for s in spans_case2:
            asyncio.run(offline_client.send_span(s))

        wal_files = [
            f for f in wal_dir.glob("langfuse-*.jsonl") if "failed-" not in f.name
        ]
        non_empty = [f for f in wal_files if f.exists() and f.stat().st_size > 0]
        assert len(non_empty) >= 1, "断网情况下应至少有一个非空 WAL 文件"

        total_wal_lines = 0
        for f in non_empty:
            with f.open("r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if line:
                        entry = json.loads(line)
                        assert "span" in entry
                        assert "retry_count" in entry
                        total_wal_lines += 1
        assert total_wal_lines >= 8

        replay_client = LangfuseClient(
            base_url="http://langfuse.example",
            public_key="pk-xxx",
            secret_key="sk-xxx",
        )
        replay_ok = MagicMock()
        replay_ok.status_code = 200
        replay_mock = MagicMock()
        replay_mock.post = AsyncMock(return_value=replay_ok)
        replay_client.client = replay_mock
        asyncio.run(replay_client._replay_once())

        wal_files_after = [
            f for f in wal_dir.glob("langfuse-*.jsonl") if "failed-" not in f.name
        ]
        total_after = 0
        for f in wal_files_after:
            if f.exists():
                total_after += f.stat().st_size
        assert total_after == 0, "replay 成功后 WAL 应该被清空"
    finally:
        lc_module.LangfuseClient.WAL_DIR = original_wal


@pytest.mark.unit
def test_tr12_2_hash_chain_break_and_repair(temp_dir):
    """TR-12.2 hash chain 破坏 + 自动修复"""
    worm_path = temp_dir / "worm-t12.db"
    worm = WormStorage(worm_path)
    alert_db = temp_dir / "alerts.db"
    alert_mgr = AlertManager(sqlite_path=alert_db, worm_storage=worm)
    checker = HashChainChecker(worm=worm, alert_manager=alert_mgr)

    N = 50
    for i in range(N):
        e = AuditLogEntry(
            prev_hash="",
            action="step" if i % 2 == 0 else "review",
            actor=f"actor-{i % 3}",
            payload={"idx": i, "value": str(i)},
            hash="",
            created_at=datetime.now(timezone.utc).isoformat(),
            pipeline_id="pipe-hash",
            node_id=f"n{i % 5}",
        )
        worm.insert(e)

    valid0, bad0, r0 = checker.run_once(auto_repair=False)
    assert valid0 is True
    assert bad0 is None
    assert r0 is False

    conn = worm._raw_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, hash FROM audit_log ORDER BY id ASC LIMIT 1 OFFSET 6")
    row7 = cur.fetchone()
    assert row7 is not None
    id_7 = int(row7["id"])
    cur.execute("UPDATE audit_log SET hash = ? WHERE id = ?", ("tampered-bad", id_7))
    conn.commit()

    valid1, bad1, r1 = checker.run_once(auto_repair=False)
    assert valid1 is False
    assert bad1 is not None
    rows = worm.list(limit=100)
    assert bad1 < len(rows)
    assert r1 is False

    valid2, bad2, r2 = checker.run_once(auto_repair=True)
    assert valid2 is True, "自动修复后 chain 应该 valid"
    assert bad2 is None
    assert r2 is True

    valid3, bad3, r3 = checker.run_once(auto_repair=False)
    assert valid3 is True
    assert bad3 is None
    assert checker.last_auto_repaired() is False

    worm.close()
    alert_mgr.close()


class _SimpleNodeStore:
    def __init__(self) -> None:
        self._state: dict[str, str] = {}

    def set_status(self, node_id: str, status: str) -> None:
        self._state[node_id] = status

    def get(self, node_id: str, default: str = "done") -> str:
        return self._state.get(node_id, default)


class _FakeResp:
    def __init__(self, code: int) -> None:
        self.status_code = code


@pytest.mark.unit
def test_tr12_3_ext_health_3_fail_deprecated(temp_dir):
    """TR-12.3 ExternalHealthMonitor 连续 3 fail → deprecated"""
    worm_path = temp_dir / "worm-ext.db"
    worm = WormStorage(worm_path)
    alert_db = temp_dir / "alerts-ext.db"
    alert_mgr = AlertManager(sqlite_path=alert_db, worm_storage=worm)
    node_store = _SimpleNodeStore()

    targets = [
        {"node_id": "n1", "url": "http://good.example/figma/fileA", "pipeline_id": "pA"},
        {"node_id": "n5", "url": "http://bad.example/figma/fileB", "pipeline_id": "pB"},
    ]
    mon = ExternalHealthMonitor(
        targets=targets,
        worm_storage=worm,
        alert_manager=alert_mgr,
        node_state_store=node_store,
    )

    good_resp = _FakeResp(200)
    notfound_resp = _FakeResp(404)

    async def _fake_head(url: str, *args, **kwargs):
        if "good.example" in url:
            return good_resp
        raise RuntimeError("404 not found mock")

    fake_http_client = MagicMock()
    fake_http_client.head = _fake_head
    mon._client = fake_http_client

    asyncio.run(mon.run_once())
    asyncio.run(mon.run_once())
    snap_before = mon.state_snapshot()
    n5_before = next(t for t in snap_before["targets"] if t["node_id"] == "n5")
    assert n5_before["consecutive_failures"] == 2
    assert n5_before["deprecated"] is False

    asyncio.run(mon.run_once())
    snap_after = mon.state_snapshot()
    n5_after = next(t for t in snap_after["targets"] if t["node_id"] == "n5")
    assert n5_after["consecutive_failures"] >= 3
    assert n5_after["deprecated"] is True
    assert node_store.get("n5") == "deprecated"

    notifications = mon.consumer_notifications()
    assert len(notifications) >= 1
    cross_evt = notifications[0]
    assert cross_evt["event_type"] == "CrossPipelineReference"
    assert cross_evt["source_node_id"] == "n5"

    worm_entries = worm.list(limit=1000)
    cross_in_worm = [
        e for e in worm_entries if getattr(e, "action", None) == "cross_pipeline_notify"
    ]
    assert len(cross_in_worm) >= 1

    all_alerts = alert_mgr.list_alerts()
    alr12 = [a for a in all_alerts if a["alert_id"] == "ALR-12"]
    assert len(alr12) >= 1

    worm.close()
    alert_mgr.close()


@pytest.mark.unit
def test_tr12_4_four_tier_cost_summary(temp_dir):
    """TR-12.4 四级成本 API 汇总"""
    cost_db = temp_dir / "cost.db"
    agg = CostAggregator(cost_db)
    alert_db = temp_dir / "alerts-cost.db"
    alert_mgr = AlertManager(sqlite_path=alert_db)

    pipeline_ids = ["pipe-CA", "pipe-CB"]
    task_ids = ["t1", "t2", "t3"]
    agent_ids = ["a-front", "a-back"]

    cost_usd_list = [500.0, 1500.0, 300.0, 900.0, 1800.0]
    for i, cu in enumerate(cost_usd_list):
        pid = pipeline_ids[i % 2]
        tid = task_ids[i % 3]
        aid = agent_ids[i % 2]
        agg.record(
            task_id=tid,
            agent_id=aid,
            pipeline_id=pid,
            cost_usd=cu,
            tokens_in=1000 * (i + 1),
            tokens_out=500 * (i + 1),
        )

    platform_summary = agg.summary(group_by="platform")
    total_platform = float(platform_summary["total"])
    assert abs(total_platform - 5000.0) < 0.001

    pipeline_summary = agg.summary(group_by="pipeline")
    pipe_total = sum(float(r["cost_usd"]) for r in pipeline_summary["rows"])
    assert abs(total_platform - pipe_total) < 0.01

    agent_summary = agg.summary(group_by="agent")
    agent_total = sum(float(r["cost_usd"]) for r in agent_summary["rows"])
    assert abs(total_platform - agent_total) < 0.01

    task_summary = agg.summary(group_by="task")
    task_total = sum(float(r["cost_usd"]) for r in task_summary["rows"])
    assert abs(total_platform - task_total) < 0.01

    assert total_platform >= 4001.0

    alert_mgr.fire(
        "ALR-15",
        trace_id=uuid.uuid4().hex,
        total_platform_usd=total_platform,
        threshold=4000.0,
    )
    alerts_list = alert_mgr.list_alerts()
    alr15_list = [a for a in alerts_list if a["alert_id"] == "ALR-15"]
    assert len(alr15_list) >= 1

    agg.close()
    alert_mgr.close()


@pytest.mark.asyncio
async def test_tr12_5_sse_events_stream(temp_dir):
    """TR-12.5 SSE 实时端点"""
    _clear_queue(_SSE_QUEUE)

    from fastapi.testclient import TestClient

    cost_db = temp_dir / "cost-sse.db"
    agg = CostAggregator(cost_db)
    alert_db = temp_dir / "alerts-sse.db"
    alert_mgr = AlertManager(sqlite_path=alert_db)

    pipelines_store = {
        "p1": {"id": "p1", "status": "active", "profile": "product-spec"},
        "p2": {"id": "p2", "status": "paused", "profile": "client-ui"},
    }
    build_env(
        alert_manager=alert_mgr,
        cost_aggregator=agg,
        pipelines_store=pipelines_store,
    )

    with TestClient(app) as client:
        overview_resp = client.get("/api/pipelines/overview")
        assert overview_resp.status_code == 200
        overview_json = overview_resp.json()
        assert "pipelines" in overview_json
        pipes = overview_json["pipelines"]
        assert len(pipes) == 2
        for p in pipes:
            assert "profile_badge_color" in p
            assert p["profile_badge_color"].startswith("#")

    from monitoring.observability_server import sse_events as sse_endpoint
    from monitoring.observability_server import ServerSentEvent

    push_trace = uuid.uuid4().hex
    payload = {
        "pipeline_id": "p1",
        "new_status": "in_progress",
        "trace_id": push_trace,
    }

    results: dict[str, list[str]] = {"hello": [], "state_changed": []}
    stop_collect = asyncio.Event()

    async def collect_all():
        resp = await sse_endpoint()
        stream = resp.body_iterator
        buffer = b""
        try:
            while not stop_collect.is_set():
                try:
                    chunk = await asyncio.wait_for(anext(stream), timeout=0.3)
                except asyncio.TimeoutError:
                    continue
                except StopAsyncIteration:
                    break
                if not chunk:
                    continue
                if isinstance(chunk, str):
                    chunk = chunk.encode("utf-8")
                buffer += chunk
                while b"\n\n" in buffer:
                    idx = buffer.index(b"\n\n")
                    raw_block = buffer[:idx]
                    buffer = buffer[idx + 2 :]
                    block = raw_block.decode("utf-8", errors="replace")
                    lines = block.split("\n")
                    event_name = None
                    data_parts: list[str] = []
                    for ln in lines:
                        if ln.startswith("event:"):
                            event_name = ln[len("event:") :].strip()
                        elif ln.startswith("data:"):
                            data_parts.append(ln[len("data:") :].strip())
                    data = "\n".join(data_parts)
                    if event_name in results:
                        results[event_name].append(data)
        finally:
            try:
                await stream.aclose()
            except Exception:
                pass

    collector = asyncio.create_task(collect_all())
    try:
        deadline = time.time() + 4.0
        while time.time() < deadline and len(results["hello"]) == 0:
            await asyncio.sleep(0.1)
        assert len(results["hello"]) >= 1, f"未收到 hello 事件: {results}"

        await sse_push("state_changed", payload)
        deadline2 = time.time() + 4.0
        while time.time() < deadline2 and len(results["state_changed"]) == 0:
            await asyncio.sleep(0.1)
        stop_collect.set()
        await asyncio.sleep(0.2)
    finally:
        stop_collect.set()
        collector.cancel()
        try:
            await asyncio.wait_for(collector, timeout=2.0)
        except Exception:
            pass

    assert len(results["state_changed"]) >= 1, f"未收到 state_changed 事件: {results}"
    first_data = results["state_changed"][0]
    try:
        data_json = json.loads(first_data)
        assert data_json.get("pipeline_id") == "p1"
        assert data_json.get("trace_id") == push_trace
    except json.JSONDecodeError:
        assert "p1" in first_data

    assert "state_changed" in SSE_EVENTS
    assert "pr_created" in SSE_EVENTS
    assert "pr_merged" in SSE_EVENTS
    assert "alert_fired" in SSE_EVENTS
    assert "hash_chain_event" in SSE_EVENTS

    agg.close()
    alert_mgr.close()
