from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict


def _get_gate_policy_conn() -> sqlite3.Connection:
    import sys
    from pathlib import Path as _Path
    coord_root = _Path(__file__).resolve().parent.parent
    if str(coord_root) not in sys.path:
        sys.path.insert(0, str(coord_root))
    try:
        from mcp.tools_phase2 import get_aux_conn
        return get_aux_conn()
    except Exception:
        _p = _Path("data") / "aux_mcp.db"
        _p.parent.mkdir(parents=True, exist_ok=True)
        c = sqlite3.connect(str(_p), check_same_thread=False)
        c.row_factory = sqlite3.Row
        return c


class GatePolicy(BaseModel):
    model_config = ConfigDict(use_enum_values=True, extra="forbid")

    pipeline_id: str
    gate_node_id: str
    lint: bool = True
    test: bool = True
    coverage_min: float = 0.8
    security_scan: bool = True


class GatePolicyStore:
    def __init__(self, sqlite_path: Path | None = None):
        self._init_schema()
        self._cache: dict[tuple[str, str], GatePolicy] = {}

    def _conn(self) -> sqlite3.Connection:
        return _get_gate_policy_conn()

    def _init_schema(self) -> None:
        conn = self._conn()
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS gate_policies (
                pipeline_id TEXT,
                gate_node_id TEXT,
                lint INTEGER,
                test INTEGER,
                coverage_min REAL,
                security_scan INTEGER,
                payload_json TEXT,
                PRIMARY KEY (pipeline_id, gate_node_id)
            )
            """
        )
        conn.commit()

    def set_policy(self, policy: GatePolicy) -> GatePolicy:
        conn = self._conn()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT OR REPLACE INTO gate_policies (
                pipeline_id, gate_node_id, lint, test, coverage_min, security_scan, payload_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                policy.pipeline_id,
                policy.gate_node_id,
                1 if policy.lint else 0,
                1 if policy.test else 0,
                policy.coverage_min,
                1 if policy.security_scan else 0,
                json.dumps(policy.model_dump(), sort_keys=True),
            ),
        )
        conn.commit()
        key = (policy.pipeline_id, policy.gate_node_id)
        self._cache[key] = policy
        return policy

    def get_policy(self, pipeline_id: str, gate_node_id: str) -> GatePolicy | None:
        key = (pipeline_id, gate_node_id)
        if key in self._cache:
            return self._cache[key]
        conn = self._conn()
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM gate_policies WHERE pipeline_id = ? AND gate_node_id = ?",
            (pipeline_id, gate_node_id),
        )
        row = cur.fetchone()
        if row is None:
            return None
        policy = GatePolicy(
            pipeline_id=row["pipeline_id"],
            gate_node_id=row["gate_node_id"],
            lint=bool(row["lint"]),
            test=bool(row["test"]),
            coverage_min=float(row["coverage_min"]),
            security_scan=bool(row["security_scan"]),
        )
        self._cache[key] = policy
        return policy

    def evaluate(
        self,
        pipeline_id: str,
        gate_node_id: str,
        coverage_report_pct: float | None = None,
        lint_passed: bool = True,
        test_passed: bool = True,
        security_scan_passed: bool = True,
    ) -> tuple[bool, list[str]]:
        policy = self.get_policy(pipeline_id, gate_node_id)
        failed_rules: list[str] = []
        if policy is None:
            return True, failed_rules
        if policy.lint and not lint_passed:
            failed_rules.append("R_LINT_FAIL")
        if policy.test and not test_passed:
            failed_rules.append("R_TEST_FAIL")
        if coverage_report_pct is not None:
            if coverage_report_pct < policy.coverage_min:
                failed_rules.append("R_COVERAGE_BELOW_POLICY")
        if policy.security_scan and not security_scan_passed:
            failed_rules.append("R_SECURITY_SCAN_HIT")
        return len(failed_rules) == 0, failed_rules

    def clear_all(self) -> None:
        try:
            conn = self._conn()
            cur = conn.cursor()
            cur.execute("DELETE FROM gate_policies")
            conn.commit()
        except Exception:
            pass
        self._cache.clear()

    def close(self) -> None:
        pass


_GATE_STORE_VAR: dict[str, GatePolicyStore] = {"instance": None}


def get_gate_policy_store() -> GatePolicyStore:
    if _GATE_STORE_VAR["instance"] is None:
        _GATE_STORE_VAR["instance"] = GatePolicyStore()
    return _GATE_STORE_VAR["instance"]


def set_gate_policy_store(store: GatePolicyStore) -> None:
    _GATE_STORE_VAR["instance"] = store
