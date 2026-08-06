from __future__ import annotations

import asyncio
import json
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx


class HTTPStatusError(Exception):
    pass


class LangfuseClient:
    SPAN_CLASSES = {
        "mcp_call",
        "graph_step",
        "review_run",
        "approve_pr",
        "reject_pr",
        "crew_task",
        "crew_agent",
        "platform_core",
    }

    WAL_DIR = Path("data/wal")

    def __init__(
        self,
        base_url: str | None = None,
        public_key: str | None = None,
        secret_key: str | None = None,
    ) -> None:
        self.enabled = bool(base_url and public_key and secret_key)
        self.base_url = base_url
        self.public_key = public_key
        self.secret_key = secret_key
        self.client: httpx.AsyncClient | None = None
        if self.enabled and self.base_url:
            self.client = httpx.AsyncClient(base_url=self.base_url, timeout=5.0)
        self._replay_task: asyncio.Task | None = None
        self.WAL_DIR.mkdir(parents=True, exist_ok=True)

    async def _send(self, span: dict) -> None:
        try:
            if not self.enabled or self.client is None:
                raise ConnectionError("disabled")
            r = await self.client.post(
                "/api/public/ingestion",
                json={"batch": [span]},
            )
            if r.status_code >= 500:
                raise HTTPStatusError(f"5xx: {r.status_code}")
        except Exception:
            self._write_wal(span)

    def _write_wal(self, span: dict, retry_count: int = 0) -> None:
        today = datetime.now().strftime("%Y%m%d")
        p = self.WAL_DIR / f"langfuse-{today}.jsonl"
        p.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(
            {"retry_count": retry_count, "ts": time.time(), "span": span}
        )
        with p.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    def _write_failed_wal(self, entry: dict) -> None:
        today = datetime.now().strftime("%Y%m%d")
        p = self.WAL_DIR / f"langfuse-failed-{today}.jsonl"
        p.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(entry)
        with p.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    def _scan_wal_files(self) -> list[Path]:
        files: list[Path] = []
        for p in self.WAL_DIR.glob("langfuse-*.jsonl"):
            if "failed-" in p.name:
                continue
            files.append(p)
        return sorted(files)

    async def _replay_once(self) -> tuple[int, int]:
        files = self._scan_wal_files()
        total_sent = 0
        total_moved = 0
        for fpath in files:
            if not fpath.exists():
                continue
            lines: list[str] = []
            try:
                with fpath.open("r", encoding="utf-8") as f:
                    lines = f.readlines()
            except Exception:
                continue

            remaining_lines: list[str] = []
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except Exception:
                    continue
                span = entry.get("span", {})
                retry_count = int(entry.get("retry_count", 0))
                try:
                    if not self.enabled or self.client is None:
                        raise ConnectionError("disabled")
                    r = await self.client.post(
                        "/api/public/ingestion",
                        json={"batch": [span]},
                    )
                    if r.status_code >= 500:
                        raise HTTPStatusError(f"5xx: {r.status_code}")
                    total_sent += 1
                except Exception:
                    retry_count += 1
                    if retry_count > 5:
                        self._write_failed_wal(entry)
                        total_moved += 1
                    else:
                        new_entry = {
                            "retry_count": retry_count,
                            "ts": entry.get("ts", time.time()),
                            "span": span,
                        }
                        remaining_lines.append(json.dumps(new_entry))

            with fpath.open("w", encoding="utf-8") as f:
                for l in remaining_lines:
                    f.write(l + "\n")

            try:
                if fpath.stat().st_size == 0:
                    fpath.unlink()
            except Exception:
                pass

        return total_sent, total_moved

    async def start_replay_loop(self, interval_sec: int = 60) -> None:
        async def _loop():
            while True:
                try:
                    await self._replay_once()
                except Exception:
                    pass
                await asyncio.sleep(interval_sec)

        if self._replay_task is None or self._replay_task.done():
            self._replay_task = asyncio.create_task(_loop())

    def stop_replay_loop(self) -> None:
        if self._replay_task is not None and not self._replay_task.done():
            self._replay_task.cancel()
            self._replay_task = None

    def trace_span(
        self,
        name: str,
        span_class: str,
        metadata: dict,
        trace_id: str,
        parent_id: str | None = None,
    ) -> dict:
        if span_class not in self.SPAN_CLASSES:
            span_class = "platform_core"
        span_id = uuid.uuid4().hex
        ts_now = time.time()
        iso_now = datetime.fromtimestamp(ts_now).isoformat()
        default_meta_keys = [
            "pipeline_id",
            "node_id",
            "action",
            "actor",
            "role_instance_id",
            "classification_before",
            "classification_after",
            "change_class",
            "status_before",
            "status_after",
            "cost_usd",
            "token_in",
            "token_out",
            "tool_name",
        ]
        full_meta: dict[str, Any] = {k: None for k in default_meta_keys}
        if metadata:
            for k, v in metadata.items():
                full_meta[k] = v
        span = {
            "span_id": span_id,
            "trace_id": trace_id,
            "parent_id": parent_id,
            "name": name,
            "span_class": span_class,
            "start_time": iso_now,
            "end_time": iso_now,
            "status": "ok",
            "metadata": full_meta,
            "ts": ts_now,
        }
        return span

    async def send_span(self, span: dict) -> None:
        await self._send(span)
