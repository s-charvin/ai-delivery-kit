from __future__ import annotations

import asyncio
import time
import uuid
from datetime import datetime, timezone
from typing import Any

import httpx


class ExternalHealthMonitor:
    def __init__(
        self,
        targets: list[dict],
        worm_storage: Any | None = None,
        alert_manager: Any | None = None,
        node_state_store: Any | None = None,
    ) -> None:
        self.targets: list[dict] = []
        for t in targets or []:
            self.targets.append(
                {
                    "node_id": t.get("node_id"),
                    "url": t.get("url"),
                    "pipeline_id": t.get("pipeline_id"),
                    "consecutive_failures": 0,
                    "last_status": None,
                    "last_check_ts": None,
                    "deprecated": False,
                }
            )
        self.worm_storage = worm_storage
        self.alert_manager = alert_manager
        self.node_state_store = node_state_store
        self._client: httpx.AsyncClient | None = None
        self._stop_event: asyncio.Event | None = None
        self._loop_task: asyncio.Task | None = None
        self._consumer_notifications: list[dict] = []

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=10.0)
        return self._client

    def state_snapshot(self) -> dict:
        return {
            "targets": [
                {
                    "node_id": t["node_id"],
                    "url": t["url"],
                    "pipeline_id": t["pipeline_id"],
                    "consecutive_failures": t["consecutive_failures"],
                    "last_status": t["last_status"],
                    "last_check_ts": t["last_check_ts"],
                    "deprecated": t["deprecated"],
                }
                for t in self.targets
            ]
        }

    async def run_once(self) -> dict:
        results: dict[str, bool] = {}
        client = self._get_client()
        for t in self.targets:
            url = t.get("url") or ""
            ok = False
            status_code: int | None = None
            try:
                r = await client.head(url)
                status_code = r.status_code
                if 200 <= r.status_code < 400:
                    ok = True
            except Exception:
                ok = False
            t["last_check_ts"] = time.time()
            t["last_status"] = status_code
            results[t["node_id"] or ""] = ok
            if ok:
                t["consecutive_failures"] = 0
            else:
                t["consecutive_failures"] = int(t.get("consecutive_failures") or 0) + 1
                if (
                    t["consecutive_failures"] >= 3
                    and not t["deprecated"]
                ):
                    t["deprecated"] = True
                    self._mark_node_deprecated(t)
                    self._publish_cross_pipeline_notification(t)
                    if self.alert_manager is not None:
                        try:
                            self.alert_manager.fire(
                                "ALR-12",
                                trace_id=uuid.uuid4().hex,
                                node_id=t["node_id"],
                                url=t["url"],
                                pipeline_id=t["pipeline_id"],
                                consecutive_failures=t["consecutive_failures"],
                            )
                        except Exception:
                            pass
        return results

    def _mark_node_deprecated(self, target: dict) -> None:
        if self.node_state_store is None:
            return
        try:
            nid = target.get("node_id")
            if not nid:
                return
            if hasattr(self.node_state_store, "set_status"):
                self.node_state_store.set_status(nid, "deprecated")
            elif hasattr(self.node_state_store, "update"):
                self.node_state_store.update(node_id=nid, status="deprecated")
        except Exception:
            pass

    def _publish_cross_pipeline_notification(self, target: dict) -> None:
        evt = {
            "id": uuid.uuid4().hex,
            "event_type": "CrossPipelineReference",
            "action": "source_node_deprecated",
            "source_node_id": target.get("node_id"),
            "pipeline_id": target.get("pipeline_id"),
            "url": target.get("url"),
            "ts": time.time(),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self._consumer_notifications.append(evt)
        if self.worm_storage is not None:
            try:
                from audit.worm_storage import AuditLogEntry

                entry = AuditLogEntry(
                    prev_hash="",
                    action="cross_pipeline_notify",
                    actor="external_health_monitor",
                    payload=evt,
                    hash="",
                    created_at=evt["created_at"],
                    pipeline_id=target.get("pipeline_id"),
                    node_id=target.get("node_id"),
                    trace_id=evt["id"],
                )
                self.worm_storage.insert(entry)
            except Exception:
                pass

    def consumer_notifications(self) -> list[dict]:
        return list(self._consumer_notifications)

    async def loop(
        self,
        interval_min: int = 30,
        stop_event: asyncio.Event | None = None,
    ) -> None:
        self._stop_event = stop_event or asyncio.Event()
        while not self._stop_event.is_set():
            try:
                await self.run_once()
            except Exception:
                pass
            try:
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=float(interval_min) * 60.0,
                )
            except asyncio.TimeoutError:
                pass

    def stop(self) -> None:
        if self._stop_event is not None:
            self._stop_event.set()
        if self._client is not None:
            try:
                asyncio.create_task(self._client.aclose())
            except Exception:
                pass
