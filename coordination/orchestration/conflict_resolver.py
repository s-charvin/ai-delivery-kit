from __future__ import annotations

import hashlib
from collections import OrderedDict
from typing import Any, Callable

from orchestration.locks import (
    LOCK_CASCADE,
    LOCK_PR,
    Allocator,
    DistributedLock,
)


class PRConflictError(Exception):
    def __init__(self, error_code: str, detail: str = "") -> None:
        super().__init__(f"{error_code}: {detail}")
        self.error_code = error_code
        self.detail = detail


class LRUCache:
    def __init__(self, capacity: int = 128) -> None:
        self.capacity = capacity
        self._cache: OrderedDict[tuple, Any] = OrderedDict()

    def get(self, key: tuple) -> Any | None:
        if key in self._cache:
            self._cache.move_to_end(key)
            return self._cache[key]
        return None

    def set(self, key: tuple, value: Any) -> None:
        if key in self._cache:
            self._cache.move_to_end(key)
        self._cache[key] = value
        if len(self._cache) > self.capacity:
            self._cache.popitem(last=False)


class ConflictResolver:
    def __init__(
        self,
        locks: DistributedLock,
        allocator: Allocator,
        state_store: Any | None = None,
    ) -> None:
        self.locks = locks
        self.allocator = allocator
        self.state_store = state_store
        self._review_cache = LRUCache(capacity=128)

    def check_open_pr_conflict(
        self, node_id: str, pending_prs: dict
    ) -> None:
        lock_key = LOCK_PR.format(node_id=node_id)
        with self.locks.guard(lock_key) as ok:
            if not ok:
                raise Exception("E_NODE_LOCKED")
            if node_id in pending_prs:
                raise PRConflictError(
                    "E_NODE_PENDING_PR_EXISTS",
                    detail=f"existing pr {pending_prs[node_id]}",
                )

    def need_rerun_review(self, pr_id: str, latest_commit: str) -> bool:
        cache_key = (pr_id, latest_commit)
        cached = self._review_cache.get(cache_key)
        if cached is not None:
            return False
        self._review_cache.set(cache_key, True)
        return True

    def _dedupe_events(self, events: list[dict] | list) -> list:
        seen: set[str] = set()
        deduped: list = []
        for ev in events:
            ev_dict = ev if isinstance(ev, dict) else (
                ev.model_dump() if hasattr(ev, "model_dump") else {"type": str(ev), "payload": {}}
            )
            if "event_id" in ev_dict and ev_dict["event_id"]:
                key = str(ev_dict["event_id"])
            else:
                ev_type = ev_dict.get("type", "")
                node_id = ev_dict.get("payload", {}).get("node_id", ev_dict.get("node_id", ""))
                payload_items = tuple(
                    sorted(
                        (
                            (k, str(v))
                            for k, v in ev_dict.get("payload", {}).items()
                        )
                    )
                )
                raw_key = f"{ev_type}|{node_id}|{payload_items}"
                key = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
            if key not in seen:
                seen.add(key)
                deduped.append(ev)
        return deduped

    def cascade_serialize(
        self,
        pipeline_id: str,
        fn: Callable[..., list],
        *args: Any,
        **kwargs: Any,
    ) -> list:
        lock_key = LOCK_CASCADE.format(pipeline_id=pipeline_id)
        with self.locks.guard(lock_key, timeout_sec=15.0) as ok:
            if not ok:
                raise TimeoutError(
                    f"Failed to acquire cascade lock for pipeline {pipeline_id}"
                )
            events = fn(*args, **kwargs)
            if not isinstance(events, list):
                events = list(events) if hasattr(events, "__iter__") else [events]
            deduped = self._dedupe_events(events)
            return deduped

    def emergency_submit(
        self, node_id: str, payload: dict, expected_version: int
    ) -> tuple[int, bool]:
        return self.allocator.emergency_version_cas(
            node_id, payload, expected_version
        )

    def is_callback_processed(
        self, pr_id: str, action: str, commit: str
    ) -> bool:
        key = f"cb:{pr_id}:{action}:{commit}"
        return self.allocator.is_callback_processed(key)
