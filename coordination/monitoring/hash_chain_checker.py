from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any, Tuple


class HashChainChecker:
    def __init__(self, worm: Any, alert_manager: Any | None = None) -> None:
        self.worm = worm
        self.alert_manager = alert_manager
        self._last_auto_repaired = False

    def run_once(
        self,
        pipeline_id: str | None = None,
        auto_repair: bool = True,
    ) -> Tuple[bool, int | None, bool]:
        from audit.hash_chain import validate_chain, repair_chain

        entries = self._load_entries(pipeline_id=pipeline_id)
        valid, first_bad_index = validate_chain(entries)
        self._last_auto_repaired = False
        if not valid and auto_repair and first_bad_index is not None:
            try:
                repaired = repair_chain(entries)
                self._persist_repaired(repaired)
                self._last_auto_repaired = True
                if self.alert_manager is not None:
                    try:
                        self.alert_manager.fire(
                            "ALR-7",
                            trace_id=f"hash-chain-repair-{int(time.time())}",
                            pipeline_id=pipeline_id,
                            first_bad_index=first_bad_index,
                            auto_repaired=True,
                        )
                    except Exception:
                        pass
                entries_after = self._load_entries(pipeline_id=pipeline_id)
                valid2, _ = validate_chain(entries_after)
                return valid2, (None if valid2 else first_bad_index), True
            except Exception:
                if self.alert_manager is not None:
                    try:
                        self.alert_manager.fire(
                            "ALR-7",
                            trace_id=f"hash-chain-broken-{int(time.time())}",
                            pipeline_id=pipeline_id,
                            first_bad_index=first_bad_index,
                            auto_repaired=False,
                        )
                    except Exception:
                        pass
                return False, first_bad_index, False
        if not valid and not auto_repair and self.alert_manager is not None:
            try:
                self.alert_manager.fire(
                    "ALR-7",
                    trace_id=f"hash-chain-broken-{int(time.time())}",
                    pipeline_id=pipeline_id,
                    first_bad_index=first_bad_index,
                    auto_repaired=False,
                )
            except Exception:
                pass
        return valid, first_bad_index, False

    def _load_entries(self, pipeline_id: str | None = None) -> list:
        if pipeline_id is not None:
            return self.worm.list(pipeline_id=pipeline_id, limit=1_000_000)
        return self.worm.list(limit=1_000_000)

    def _persist_repaired(self, entries: list) -> None:
        if not entries:
            return
        conn = self.worm._raw_connection()
        cur = conn.cursor()
        for entry in entries:
            cur.execute(
                "UPDATE audit_log SET prev_hash = ?, hash = ? WHERE id = ?",
                (entry.prev_hash, entry.hash, entry.id),
            )
        conn.commit()

    def last_auto_repaired(self) -> bool:
        return self._last_auto_repaired
