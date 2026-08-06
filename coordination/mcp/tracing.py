from __future__ import annotations

import asyncio
import contextvars
import functools
import json
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import httpx

LANGFUSE_WAL_DIR = Path("data/wal/langfuse")
LANGFUSE_WAL_DIR.mkdir(parents=True, exist_ok=True)

_trace_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("trace_id", default="")


def get_current_trace_id() -> str:
    return _trace_id_var.get("")


class LangfuseClientStub:
    def __init__(self) -> None:
        base_url = os.getenv("LANGFUSE_BASE_URL", "http://localhost:3030")
        public_key = os.getenv("LANGFUSE_PUBLIC_KEY", "")
        self.base_url = base_url.rstrip("/")
        self.public_key = public_key
        self._client: httpx.AsyncClient | None = None

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(base_url=self.base_url, timeout=5.0)
        return self._client

    def _write_wal(self, span: dict) -> None:
        LANGFUSE_WAL_DIR.mkdir(parents=True, exist_ok=True)
        ts = int(time.time() * 1000)
        uid = uuid.uuid4().hex[:8]
        fname = f"{ts}-{uid}.jsonl"
        fpath = LANGFUSE_WAL_DIR / fname
        line = json.dumps(span, ensure_ascii=False)
        with open(fpath, "a", encoding="utf-8") as f:
            f.write(line + "\n")

    async def send_span(self, span: dict) -> None:
        try:
            client = self._get_client()
            headers = {}
            if self.public_key:
                headers["Authorization"] = f"Bearer {self.public_key}"
            resp = await client.post("/api/v2/spans", json=span, headers=headers)
            if resp.status_code >= 500:
                self._write_wal(span)
        except Exception:
            self._write_wal(span)


LANGFUSE_CLIENT = LangfuseClientStub()


def _make_span(
    trace_id: str,
    name: str,
    span_type: str,
    start_time: str,
    end_time: str | None,
    status: str,
    inputs: dict | None,
    outputs: Any,
    error: str | None,
    metadata: dict | None,
) -> dict:
    return {
        "trace_id": trace_id,
        "span_id": uuid.uuid4().hex,
        "name": name,
        "span_type": span_type,
        "start_time": start_time,
        "end_time": end_time,
        "status": status,
        "inputs": inputs,
        "outputs": outputs,
        "error": error,
        "metadata": metadata or {},
    }


def langfuse_trace(name: str | None = None, span_type: str = "tool"):
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            trace_id = kwargs.pop("__trace_id", None) or _trace_id_var.get("") or uuid.uuid4().hex
            _trace_id_var.set(trace_id)

            final_name = name or func.__name__
            start_iso = datetime.now(timezone.utc).isoformat()
            inputs_snapshot = {"args": list(args), "kwargs": {k: v for k, v in kwargs.items() if k != "_ctx"}}

            span: dict | None = None
            try:
                result = await func(*args, **kwargs)
                end_iso = datetime.now(timezone.utc).isoformat()
                span = _make_span(
                    trace_id=trace_id,
                    name=final_name,
                    span_type=span_type,
                    start_time=start_iso,
                    end_time=end_iso,
                    status="ok",
                    inputs=inputs_snapshot,
                    outputs=result,
                    error=None,
                    metadata=None,
                )
                await LANGFUSE_CLIENT.send_span(span)
                return result
            except Exception as exc:
                end_iso = datetime.now(timezone.utc).isoformat()
                span = _make_span(
                    trace_id=trace_id,
                    name=final_name,
                    span_type=span_type,
                    start_time=start_iso,
                    end_time=end_iso,
                    status="error",
                    inputs=inputs_snapshot,
                    outputs=None,
                    error=str(exc),
                    metadata=None,
                )
                try:
                    await LANGFUSE_CLIENT.send_span(span)
                except Exception:
                    pass
                raise

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            trace_id = kwargs.pop("__trace_id", None) or _trace_id_var.get("") or uuid.uuid4().hex
            _trace_id_var.set(trace_id)

            final_name = name or func.__name__
            start_iso = datetime.now(timezone.utc).isoformat()
            inputs_snapshot = {"args": list(args), "kwargs": {k: v for k, v in kwargs.items() if k != "_ctx"}}

            span: dict | None = None
            try:
                result = func(*args, **kwargs)
                end_iso = datetime.now(timezone.utc).isoformat()
                span = _make_span(
                    trace_id=trace_id,
                    name=final_name,
                    span_type=span_type,
                    start_time=start_iso,
                    end_time=end_iso,
                    status="ok",
                    inputs=inputs_snapshot,
                    outputs=result,
                    error=None,
                    metadata=None,
                )
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        loop.create_task(LANGFUSE_CLIENT.send_span(span))
                    else:
                        asyncio.run(LANGFUSE_CLIENT.send_span(span))
                except Exception:
                    LANGFUSE_CLIENT._write_wal(span)
                return result
            except Exception as exc:
                end_iso = datetime.now(timezone.utc).isoformat()
                span = _make_span(
                    trace_id=trace_id,
                    name=final_name,
                    span_type=span_type,
                    start_time=start_iso,
                    end_time=end_iso,
                    status="error",
                    inputs=inputs_snapshot,
                    outputs=None,
                    error=str(exc),
                    metadata=None,
                )
                try:
                    LANGFUSE_CLIENT._write_wal(span)
                except Exception:
                    pass
                raise

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


def write_alr14_span(trace_id: str, tool_name: str, token_payload: dict | None, reason: str) -> None:
    span = {
        "trace_id": trace_id,
        "span_id": uuid.uuid4().hex,
        "name": "ALR-14-permission-denied",
        "span_type": "audit",
        "start_time": datetime.now(timezone.utc).isoformat(),
        "end_time": datetime.now(timezone.utc).isoformat(),
        "status": "ok",
        "inputs": {"tool_name": tool_name, "token_payload": token_payload, "reason": reason},
        "outputs": None,
        "error": None,
        "metadata": {"audit_code": "ALR-14"},
    }
    LANGFUSE_CLIENT._write_wal(span)
