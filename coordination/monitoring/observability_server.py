from __future__ import annotations

import asyncio
import json
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any, AsyncIterator, Literal, Optional

from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse, StreamingResponse


SSE_EVENTS: list[str] = [
    "state_changed",
    "pr_created",
    "pr_merged",
    "alert_fired",
    "hash_chain_event",
]

_SSE_QUEUE: asyncio.Queue = asyncio.Queue()

G_ENV: SimpleNamespace = SimpleNamespace(
    pipelines=SimpleNamespace(store={}),
    alert_manager=None,
    cost_aggregator=None,
    hash_chain_checker=None,
    external_health_monitor=None,
    worm_storage=None,
    langfuse_client=None,
)


class ServerSentEvent:
    def __init__(self, event: str | None = None, data: Any = "", id: str | None = None) -> None:
        self.event = event
        self.data = data
        self.id = id

    def encode(self) -> bytes:
        data_str = self.data
        if not isinstance(data_str, str):
            try:
                data_str = json.dumps(data_str, ensure_ascii=False)
            except Exception:
                data_str = str(data_str)
        lines: list[str] = []
        if self.id is not None:
            lines.append(f"id: {self.id}")
        if self.event is not None:
            lines.append(f"event: {self.event}")
        for line in data_str.split("\n"):
            lines.append(f"data: {line}")
        lines.append("")
        lines.append("")
        return ("\n".join(lines)).encode("utf-8")


app = FastAPI(title="Coordination Observability")


def color_for_profile(profile: str | None) -> str:
    if not profile:
        return "#9CA3AF"
    mapping = {
        "product-spec": "#3B82F6",
        "design-handoff": "#A855F7",
        "client-ui": "#EC4899",
        "client-logic": "#F59E0B",
        "client-delivery": "#10B981",
        "server-impl": "#6366F1",
        "server-delivery": "#14B8A6",
        "generic": "#6B7280",
        "api-contract": "#F97316",
        "derived-artifact": "#8B5CF6",
        "research-spike": "#1F2937",
    }
    return mapping.get(profile.lower(), "#64748B")


@app.get("/")
def index() -> dict:
    return {
        "name": "Coordination Observability",
        "version": "0.1.0",
        "sse_events": SSE_EVENTS,
    }


@app.get("/api/pipeline/{pid}/state")
def get_pipeline_state(pid: str) -> dict:
    store = getattr(G_ENV.pipelines, "store", {}) or {}
    if pid in store:
        p = store[pid]
        if isinstance(p, dict):
            return p
        return {
            "id": getattr(p, "id", pid),
            "status": getattr(p, "status", None),
            "profile": getattr(p, "profile", None),
            "data": {},
        }
    return {"id": pid, "status": "unknown", "profile": None, "data": {}}


@app.get("/api/pipelines/overview")
def pipelines_overview(profile_badge: bool = True) -> dict:
    store = getattr(G_ENV.pipelines, "store", {}) or {}
    result: list[dict] = []
    for pid, p in store.items():
        if isinstance(p, dict):
            status = p.get("status", "unknown")
            profile = p.get("profile")
        else:
            status = getattr(p, "status", "unknown")
            profile = getattr(p, "profile", None)
        item: dict[str, Any] = {
            "id": pid,
            "status": status,
            "profile": profile,
        }
        if profile_badge:
            item["profile_badge_color"] = color_for_profile(profile)
        result.append(item)
    return {"pipelines": result}


@app.get("/api/nodes/{nid}/timeline")
def node_timeline(nid: str, pid: str = Query(...)) -> dict:
    worm = G_ENV.worm_storage
    entries: list[dict] = []
    if worm is not None:
        try:
            rows = worm.list(pipeline_id=pid, node_id=nid, limit=1000)
            for r in rows:
                d: dict[str, Any] = {
                    "id": getattr(r, "id", None),
                    "action": getattr(r, "action", ""),
                    "actor": getattr(r, "actor", ""),
                    "payload": getattr(r, "payload", {}),
                    "created_at": getattr(r, "created_at", ""),
                    "prev_hash": getattr(r, "prev_hash", ""),
                    "hash": getattr(r, "hash", ""),
                }
                entries.append(d)
        except Exception:
            entries = []
    return {"node_id": nid, "pipeline_id": pid, "timeline": entries}


@app.get("/api/alerts")
def list_alerts(severity: Optional[str] = None) -> dict:
    if G_ENV.alert_manager is None:
        return {"alerts": []}
    try:
        alerts = G_ENV.alert_manager.list_alerts(severity=severity, limit=1000)
    except Exception:
        alerts = []
    return {"alerts": alerts}


@app.get("/api/audit/filter")
def audit_filter(
    pipeline_id: Optional[str] = None,
    node_id: Optional[str] = None,
    action: Optional[str] = None,
    reviewer: Optional[str] = None,
    from_ts: Optional[float] = None,
    to_ts: Optional[float] = None,
    limit: int = 1000,
) -> dict:
    worm = G_ENV.worm_storage
    rows: list[dict] = []
    if worm is not None:
        try:
            all_rows = worm.list(pipeline_id=pipeline_id, node_id=node_id, limit=limit * 2)
            for r in all_rows:
                if action is not None and getattr(r, "action", None) != action:
                    continue
                if reviewer is not None and getattr(r, "actor", None) != reviewer:
                    continue
                created_at = getattr(r, "created_at", "") or ""
                ts_val: float | None = None
                if created_at:
                    try:
                        ts_val = datetime.fromisoformat(created_at).timestamp()
                    except Exception:
                        ts_val = None
                if from_ts is not None and ts_val is not None and ts_val < from_ts:
                    continue
                if to_ts is not None and ts_val is not None and ts_val > to_ts:
                    continue
                rows.append(
                    {
                        "id": getattr(r, "id", None),
                        "pipeline_id": getattr(r, "pipeline_id", None),
                        "node_id": getattr(r, "node_id", None),
                        "action": getattr(r, "action", ""),
                        "actor": getattr(r, "actor", ""),
                        "payload": getattr(r, "payload", {}),
                        "created_at": created_at,
                        "hash": getattr(r, "hash", ""),
                    }
                )
                if len(rows) >= limit:
                    break
        except Exception:
            rows = []
    return {"rows": rows, "count": len(rows)}


@app.get("/api/audit/hash_chain_valid")
def audit_hash_chain(pipeline_id: Optional[str] = None) -> dict:
    checker = G_ENV.hash_chain_checker
    if checker is None:
        return {"valid": True, "first_bad_index": None, "auto_repaired": False}
    try:
        valid, first_bad, repaired = checker.run_once(pipeline_id=pipeline_id, auto_repair=True)
    except Exception:
        return {"valid": False, "first_bad_index": None, "auto_repaired": False}
    return {"valid": valid, "first_bad_index": first_bad, "auto_repaired": repaired}


@app.get("/api/cost/summary")
def cost_summary(
    group_by: Literal["task", "agent", "pipeline", "platform"] = "pipeline",
    from_ts: Optional[float] = None,
    to_ts: Optional[float] = None,
) -> dict:
    if G_ENV.cost_aggregator is None:
        return {"rows": [], "total": 0.0}
    try:
        res = G_ENV.cost_aggregator.summary(group_by, from_ts=from_ts, to_ts=to_ts)
    except Exception:
        return {"rows": [], "total": 0.0}
    return res


@app.get("/api/external_health/status")
def ext_health_status() -> dict:
    mon = G_ENV.external_health_monitor
    if mon is None:
        return {"targets": []}
    try:
        snap = mon.state_snapshot()
    except Exception:
        snap = {"targets": []}
    return snap


@app.get("/api/sse/events")
async def sse_events() -> StreamingResponse:
    q: asyncio.Queue = _SSE_QUEUE

    async def gen() -> AsyncIterator[bytes]:
        hello = ServerSentEvent(event="hello", data="ok")
        yield hello.encode()
        while True:
            try:
                item = await asyncio.wait_for(q.get(), timeout=30)
            except asyncio.TimeoutError:
                ping = ServerSentEvent(event="ping", data=time.time())
                yield ping.encode()
                continue
            ev = item.get("event") if isinstance(item, dict) else None
            data = item.get("data") if isinstance(item, dict) else item
            ev_id = item.get("id") if isinstance(item, dict) else None
            sse = ServerSentEvent(event=ev, data=data, id=ev_id)
            yield sse.encode()

    return StreamingResponse(gen(), media_type="text/event-stream")


async def sse_push(event: str, data: Any) -> None:
    item = {"event": event, "data": data, "id": uuid.uuid4().hex}
    await _SSE_QUEUE.put(item)


def build_env(
    alert_manager: Any = None,
    cost_aggregator: Any = None,
    hash_chain_checker: Any = None,
    external_health_monitor: Any = None,
    worm_storage: Any = None,
    langfuse_client: Any = None,
    pipelines_store: dict | None = None,
) -> SimpleNamespace:
    G_ENV.alert_manager = alert_manager
    G_ENV.cost_aggregator = cost_aggregator
    G_ENV.hash_chain_checker = hash_chain_checker
    G_ENV.external_health_monitor = external_health_monitor
    G_ENV.worm_storage = worm_storage
    G_ENV.langfuse_client = langfuse_client
    G_ENV.pipelines = SimpleNamespace(store=pipelines_store or {})
    return G_ENV


def main() -> None:
    import uvicorn

    port = int(os.getenv("OBSERVABILITY_PORT", "8080"))
    uvicorn.run(
        "coordination.monitoring.observability_server:app",
        host="0.0.0.0",
        port=port,
    )


if __name__ == "__main__":
    main()
