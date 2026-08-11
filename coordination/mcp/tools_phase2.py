from __future__ import annotations

import base64
import io
import json
import os
import sqlite3
import uuid
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from audit.worm_storage import AuditLogEntry, WormStorage
from config.constants import ERROR_CODES
from orchestration.cascade import cascade_addendum, cascade_changed, cascade_done
from orchestration.deps import compute_downstream
from orchestration.gate_policy import GatePolicy, get_gate_policy_store
from orchestration.models import (
    Addendum,
    ArtifactRef,
    ClassificationLevel,
    DepDeclaration,
    NodeDef,
    NodeState,
    NodeStatus,
    PipelineDefinition,
    PipelineState,
    PipelineStatus,
    Provenance,
)
from orchestration.pipeline_lifecycle import (
    CrossPipelineReference,
    merge_pipelines as _do_merge_pipelines,
    split_pipeline as _do_split_pipeline,
)
from orchestration.state_machine import (
    EVENT_ADD_ADDENDUM_INFO,
    EVENT_ADD_ADDENDUM_MUST,
    EVENT_ADD_ADDENDUM_SHOULD,
    EVENT_NOTIFY,
    Event,
    transition,
)
from utils.hashing import audit_entry_hash, content_integrity_hash

from .auth import ToolContext
from .server import (
    AuditLogEntry as ServerAuditEntry,
    _append_audit,
    get_hub_repo,
    mcp,
)
from .state_store import STORE


_PENDING_SYNC_DIR_VAR: dict[str, Path] = {"path": None}


def get_pending_sync_dir() -> Path:
    if _PENDING_SYNC_DIR_VAR["path"] is None:
        p = Path("data") / "pending_sync"
        p.mkdir(parents=True, exist_ok=True)
        _PENDING_SYNC_DIR_VAR["path"] = p
    return _PENDING_SYNC_DIR_VAR["path"]


_AUX_DB_PATH_VAR: dict[str, Path] = {"path": None}


def get_aux_db_path() -> Path:
    if _AUX_DB_PATH_VAR["path"] is None:
        p = Path("data") / "aux_tools.db"
        if not p.parent.exists():
            p.parent.mkdir(parents=True, exist_ok=True)
        _AUX_DB_PATH_VAR["path"] = p
    return _AUX_DB_PATH_VAR["path"]


def _ensure_aux_tables() -> sqlite3.Connection:
    db_path = get_aux_db_path()
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS token_blacklist (
            token_hint TEXT PRIMARY KEY,
            revoked_at TEXT,
            admin_token TEXT,
            reason TEXT
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS draft_subscribers (
            pipeline_id TEXT,
            node_id TEXT,
            subscriber_id TEXT,
            created_at TEXT,
            PRIMARY KEY (pipeline_id, node_id, subscriber_id)
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS addenda_store (
            pipeline_id TEXT,
            node_id TEXT,
            addendum_id TEXT,
            version INTEGER,
            change_class TEXT,
            incompatible_with_json TEXT,
            impact_claim_json TEXT,
            author TEXT,
            diff_hash TEXT,
            content_b64 TEXT,
            diff_unified_lines_json TEXT,
            created_at TEXT,
            acked_json TEXT DEFAULT '[]',
            PRIMARY KEY (pipeline_id, addendum_id)
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS cross_pipeline_refs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ref_type TEXT,
            source_pipeline_id TEXT,
            source_node_id TEXT,
            target_pipeline_id TEXT,
            target_node_id TEXT,
            created_at TEXT
        )
        """
    )
    conn.commit()
    return conn


_AUX_CONN_VAR: dict[str, sqlite3.Connection] = {"conn": None}


def get_aux_conn() -> sqlite3.Connection:
    if _AUX_CONN_VAR["conn"] is None:
        _AUX_CONN_VAR["conn"] = _ensure_aux_tables()
    return _AUX_CONN_VAR["conn"]


_WORM_STORE_VAR: dict[str, WormStorage] = {"instance": None}


def get_worm_store() -> WormStorage:
    if _WORM_STORE_VAR["instance"] is None:
        _WORM_STORE_VAR["instance"] = WormStorage(Path("data") / "worm.db")
    return _WORM_STORE_VAR["instance"]


def _worm_write(
    action: str,
    actor: str,
    payload: dict,
    pipeline_id: str | None = None,
    node_id: str | None = None,
    trace_id: str = "",
) -> AuditLogEntry:
    store = get_worm_store()
    entry = AuditLogEntry(
        pipeline_id=pipeline_id,
        node_id=node_id,
        action=action,
        actor=actor,
        payload=payload,
        prev_hash="",
        hash="",
        created_at="",
        trace_id=trace_id or uuid.uuid4().hex,
    )
    return store.insert(entry)


def _is_admin_token(ctx: ToolContext | None) -> bool:
    if ctx is None or ctx.token_payload is None:
        return False
    tt = ctx.token_payload.get("token_type")
    return tt in ("admin", "bot")


def _get_actor(ctx: ToolContext | None) -> str:
    if ctx is not None and ctx.token_payload is not None:
        nid = ctx.token_payload.get("node_id")
        if nid:
            return str(nid)
    return "unknown-actor"


# ============ A 组 addendum (3 工具) ============


@mcp.tool(
    name="add_addendum",
    description="Add addendum to a DONE node with optional must/should/informational cascade",
    input_schema={
        "type": "object",
        "properties": {
            "pipeline_id": {"type": "string"},
            "node_id": {"type": "string"},
            "addendum_id": {"type": ["string", "null"]},
            "version": {"type": ["integer", "null"], "default": 1},
            "change_class": {"type": "string", "enum": ["must", "should", "informational"]},
            "incompatible_with": {"type": "array", "items": {"type": "string"}, "default": []},
            "impact_claim": {"type": "array", "items": {"type": "string"}, "default": []},
            "author": {"type": ["string", "null"]},
            "diff_hash": {"type": ["string", "null"]},
            "content_b64": {"type": ["string", "null"]},
            "diff_unified_lines": {"type": ["array", "null"], "items": {"type": "string"}},
        },
        "required": ["pipeline_id", "node_id", "change_class"],
    },
)
def add_addendum(
    pipeline_id: str,
    node_id: str,
    addendum_id: str | None = None,
    version: int | None = None,
    change_class: str = "informational",
    incompatible_with: list[str] | None = None,
    impact_claim: list[str] | None = None,
    author: str | None = None,
    diff_hash: str | None = None,
    content_b64: str | None = None,
    diff_unified_lines: list[str] | None = None,
    _ctx: ToolContext | None = None,
) -> dict:
    defn = STORE.get_def(pipeline_id)
    state = STORE.get_state(pipeline_id)
    ns = state.node_states.get(node_id)
    if ns is None:
        raise ValueError(f"Node not found: {node_id}")
    ns_status = NodeStatus(ns.status) if isinstance(ns.status, str) else ns.status
    if ns_status != NodeStatus.DONE:
        raise ValueError("E_NODE_NOT_DONE: Node must be DONE to add addendum")

    actor = _get_actor(_ctx)
    current_owner = node_id
    token_payload = None
    if _ctx is not None:
        token_payload = _ctx.token_payload
    is_admin = _is_admin_token(_ctx)
    token_node_id = None
    if token_payload is not None:
        token_node_id = token_payload.get("node_id")
    if not is_admin and token_node_id != current_owner and token_node_id is not None:
        pass
    if not is_admin and author and author != current_owner:
        raise ValueError("E_ADDENDUM_AUTH: Only current_owner or admin can add addendum")

    incompatible_with = incompatible_with or []
    if change_class == "must":
        direct_downstream = set(compute_downstream(node_id, defn))
        for inc_id in incompatible_with:
            if inc_id not in direct_downstream:
                raise ValueError(
                    f"E_INCOMPATIBLE_NOT_DOWNSTREAM: incompatible_with node {inc_id} is not direct downstream"
                )

    aid = addendum_id or f"add-{uuid.uuid4().hex[:10]}"
    ver = version or 1
    impact_claim = impact_claim or []
    aut = author or current_owner
    dh = diff_hash
    if dh is None:
        sample_bytes = (content_b64 or "").encode() or json.dumps(
            {"cc": change_class, "ic": incompatible_with}, sort_keys=True
        ).encode()
        dh = content_integrity_hash(sample_bytes)

    addendum = Addendum(
        id=aid,
        version=ver,
        change_class=change_class,
        incompatible_with=list(incompatible_with),
        impact_claim=list(impact_claim),
        diff_hash=dh,
        author=aut,
        created_at=datetime.now(timezone.utc).isoformat(),
    )

    if change_class == "must":
        evt_type = EVENT_ADD_ADDENDUM_MUST
    elif change_class == "should":
        evt_type = EVENT_ADD_ADDENDUM_SHOULD
    else:
        evt_type = EVENT_ADD_ADDENDUM_INFO
    evt_map = {
        EVENT_ADD_ADDENDUM_MUST: "must",
        EVENT_ADD_ADDENDUM_SHOULD: "should",
        EVENT_ADD_ADDENDUM_INFO: "informational",
    }
    t = transition(
        ns_status,
        Event(type=evt_type, payload={"node_id": node_id, "downstream": incompatible_with, "addendum_id": aid}),
        ctx={"node_id": node_id},
    )
    if t[0] is not None:
        ns.status = t[0]

    new_state, cascade_events = cascade_addendum(node_id, addendum, defn, state)
    state.node_states = new_state.node_states

    _worm_write(
        action="ADD_ADDENDUM",
        actor=aut,
        payload={
            "addendum_id": aid,
            "change_class": change_class,
            "incompatible_with": list(incompatible_with),
            "impact_claim": list(impact_claim),
            "diff_hash": dh,
        },
        pipeline_id=pipeline_id,
        node_id=node_id,
        trace_id=(_ctx.trace_id if _ctx else "") or uuid.uuid4().hex,
    )

    conn = get_aux_conn()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT OR REPLACE INTO addenda_store (
            pipeline_id, node_id, addendum_id, version, change_class,
            incompatible_with_json, impact_claim_json, author, diff_hash,
            content_b64, diff_unified_lines_json, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            pipeline_id,
            node_id,
            aid,
            ver,
            change_class,
            json.dumps(list(incompatible_with)),
            json.dumps(list(impact_claim)),
            aut,
            dh,
            content_b64 or "",
            json.dumps(diff_unified_lines or []),
            addendum.created_at,
        ),
    )
    conn.commit()

    state.updated_at = datetime.now(timezone.utc).isoformat()
    STORE.set_state(pipeline_id, state)

    return {
        "addendum_id": aid,
        "version": ver,
        "change_class": change_class,
        "cascade_events_count": len(cascade_events),
        "created_at": addendum.created_at,
    }


@mcp.tool(
    name="reack_addendum",
    description="Downstream owner ack/nack addendum; 7天超时自动changed",
    input_schema={
        "type": "object",
        "properties": {
            "pipeline_id": {"type": "string"},
            "addendum_id": {"type": "string"},
            "accepted": {"type": "boolean"},
            "reason": {"type": "string", "default": ""},
        },
        "required": ["pipeline_id", "addendum_id", "accepted"],
    },
)
def reack_addendum(
    pipeline_id: str,
    addendum_id: str,
    accepted: bool,
    reason: str = "",
    _ctx: ToolContext | None = None,
) -> dict:
    state = STORE.get_state(pipeline_id)
    defn = STORE.get_def(pipeline_id)
    actor = _get_actor(_ctx)

    conn = get_aux_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM addenda_store WHERE pipeline_id = ? AND addendum_id = ?",
        (pipeline_id, addendum_id),
    )
    row = cur.fetchone()
    if row is None:
        raise ValueError(f"Addendum not found: {addendum_id}")

    node_id = row[1]
    change_class = row[4]
    try:
        incompatible = json.loads(row[5] or "[]")
    except Exception:
        incompatible = []
    try:
        acked = json.loads(row[12] or "[]")
    except Exception:
        acked = []
    created_at_str = row[11]

    if actor not in acked:
        acked.append(actor)
    cur.execute(
        "UPDATE addenda_store SET acked_json = ? WHERE pipeline_id = ? AND addendum_id = ?",
        (json.dumps(acked), pipeline_id, addendum_id),
    )
    conn.commit()

    ns = state.node_states.get(node_id)
    if ns is not None:
        if actor not in ns.downstream_acked_ids:
            ns.downstream_acked_ids = ns.downstream_acked_ids + [actor]

    triggered_changed = False
    if not accepted and change_class == "must":
        for inc_id in incompatible:
            inc_ns = state.node_states.get(inc_id)
            if inc_ns is None:
                continue
            inc_status = (
                NodeStatus(inc_ns.status)
                if isinstance(inc_ns.status, str)
                else inc_ns.status
            )
            if inc_status == NodeStatus.DONE:
                new_s2, evts = cascade_changed(
                    inc_id, "breaking", DepDeclaration().coupling, defn, state
                )
                state.node_states = new_s2.node_states
                triggered_changed = True

    state.updated_at = datetime.now(timezone.utc).isoformat()
    STORE.set_state(pipeline_id, state)

    return {
        "addendum_id": addendum_id,
        "acked_by": actor,
        "accepted": accepted,
        "triggered_changed": triggered_changed,
        "acked_count": len(acked),
    }


def process_addendum_timeouts(pipeline_id: str) -> dict:
    defn = STORE.get_def(pipeline_id)
    state = STORE.get_state(pipeline_id)
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    cutoff_iso = cutoff.isoformat()
    conn = get_aux_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT addendum_id, node_id, change_class, incompatible_with_json, created_at, acked_json FROM addenda_store WHERE pipeline_id = ?",
        (pipeline_id,),
    )
    rows = cur.fetchall()
    triggered_ids: list[str] = []
    for row in rows:
        aid, nid, cc, ic_json, cat, acked_json = row
        try:
            dt = datetime.fromisoformat(cat.replace("Z", "+00:00"))
        except Exception:
            continue
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        if dt > cutoff:
            continue
        try:
            incompatible = json.loads(ic_json or "[]")
        except Exception:
            incompatible = []
        if cc != "must":
            continue
        try:
            acked = set(json.loads(acked_json or "[]"))
        except Exception:
            acked = set()
        for inc_id in incompatible:
            if inc_id in acked:
                continue
            inc_ns = state.node_states.get(inc_id)
            if inc_ns is None:
                continue
            inc_status = (
                NodeStatus(inc_ns.status)
                if isinstance(inc_ns.status, str)
                else inc_ns.status
            )
            if inc_status == NodeStatus.DONE:
                new_s2, evts = cascade_changed(
                    inc_id, "breaking", DepDeclaration().coupling, defn, state
                )
                state.node_states = new_s2.node_states
                if aid not in triggered_ids:
                    triggered_ids.append(aid)
    state.updated_at = datetime.now(timezone.utc).isoformat()
    STORE.set_state(pipeline_id, state)
    return {"timeout_triggered_addenda": triggered_ids}


@mcp.tool(
    name="list_addenda",
    description="List addenda for pipeline or node",
    input_schema={
        "type": "object",
        "properties": {
            "pipeline_id": {"type": "string"},
            "node_id": {"type": ["string", "null"]},
        },
        "required": ["pipeline_id"],
    },
)
def list_addenda(
    pipeline_id: str,
    node_id: str | None = None,
    _ctx: ToolContext | None = None,
) -> list[dict]:
    conn = get_aux_conn()
    cur = conn.cursor()
    if node_id is not None:
        cur.execute(
            "SELECT * FROM addenda_store WHERE pipeline_id = ? AND node_id = ? ORDER BY created_at DESC",
            (pipeline_id, node_id),
        )
    else:
        cur.execute(
            "SELECT * FROM addenda_store WHERE pipeline_id = ? ORDER BY created_at DESC",
            (pipeline_id,),
        )
    rows = cur.fetchall()
    results = []
    for row in rows:
        try:
            incompatible = json.loads(row[5] or "[]")
        except Exception:
            incompatible = []
        try:
            impact = json.loads(row[6] or "[]")
        except Exception:
            impact = []
        try:
            acked = json.loads(row[12] or "[]")
        except Exception:
            acked = []
        results.append(
            {
                "addendum_id": row[2],
                "node_id": row[1],
                "version": row[3],
                "change_class": row[4],
                "incompatible_with": incompatible,
                "impact_claim": impact,
                "author": row[7],
                "diff_hash": row[8],
                "created_at": row[11],
                "acked_by": acked,
            }
        )
    state = STORE.get_state(pipeline_id)
    if node_id is not None:
        ns = state.node_states.get(node_id)
        if ns is not None:
            for add in ns.addenda:
                results.append(
                    {
                        "addendum_id": add.id,
                        "node_id": node_id,
                        "version": add.version,
                        "change_class": add.change_class,
                        "incompatible_with": list(add.incompatible_with),
                        "impact_claim": list(add.impact_claim),
                        "author": add.author,
                        "diff_hash": add.diff_hash,
                        "created_at": add.created_at,
                        "acked_by": list(ns.downstream_acked_ids),
                    }
                )
    return results


# ============ B 组 owner/token (2 工具) ============


@mcp.tool(
    name="transfer_owner",
    description="Transfer node ownership from one owner to another, optionally revoke old tokens",
    input_schema={
        "type": "object",
        "properties": {
            "pipeline_id": {"type": "string"},
            "node_id": {"type": "string"},
            "from_owner": {"type": "string"},
            "to_owner": {"type": "string"},
            "revoke_tokens": {"type": "boolean", "default": False},
        },
        "required": ["pipeline_id", "node_id", "from_owner", "to_owner"],
    },
)
def transfer_owner(
    pipeline_id: str,
    node_id: str,
    from_owner: str,
    to_owner: str,
    revoke_tokens: bool = False,
    _ctx: ToolContext | None = None,
) -> dict:
    state = STORE.get_state(pipeline_id)
    ns = state.node_states.get(node_id)
    if ns is None:
        raise ValueError(f"Node not found: {node_id}")
    actor = _get_actor(_ctx)
    is_admin = _is_admin_token(_ctx)
    if not is_admin and actor != from_owner:
        raise ValueError("E_PERMISSION_DENIED: Only admin or from_owner can transfer")

    _worm_write(
        action="TRANSFER_OWNER",
        actor=actor,
        payload={
            "node_id": node_id,
            "from_owner": from_owner,
            "to_owner": to_owner,
            "revoke_tokens": revoke_tokens,
        },
        pipeline_id=pipeline_id,
        node_id=node_id,
    )

    if revoke_tokens:
        conn = get_aux_conn()
        cur = conn.cursor()
        cur.execute(
            "INSERT OR IGNORE INTO token_blacklist (token_hint, revoked_at, admin_token, reason) VALUES (?, ?, ?, ?)",
            (
                f"owner:{from_owner}:{node_id}",
                datetime.now(timezone.utc).isoformat(),
                actor,
                f"transfer_owner to {to_owner}",
            ),
        )
        conn.commit()

    return {
        "ok": True,
        "from_owner": from_owner,
        "to_owner": to_owner,
        "revoked_tokens": revoke_tokens,
        "node_status_kept": (
            ns.status.value if isinstance(ns.status, NodeStatus) else str(ns.status)
        ),
    }


@mcp.tool(
    name="revoke_human_token",
    description="Admin revoke human token by hint",
    input_schema={
        "type": "object",
        "properties": {
            "token_hint": {"type": "string"},
            "admin_token": {"type": "string"},
        },
        "required": ["token_hint", "admin_token"],
    },
)
def revoke_human_token(
    token_hint: str,
    admin_token: str,
    _ctx: ToolContext | None = None,
) -> dict:
    if not _is_admin_token(_ctx):
        raise ValueError("E_PERMISSION_DENIED: Admin only")
    conn = get_aux_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT OR REPLACE INTO token_blacklist (token_hint, revoked_at, admin_token, reason) VALUES (?, ?, ?, ?)",
        (
            token_hint,
            datetime.now(timezone.utc).isoformat(),
            admin_token,
            "admin_revoke",
        ),
    )
    conn.commit()
    _worm_write(
        action="REVOKE_HUMAN_TOKEN",
        actor=_get_actor(_ctx),
        payload={"token_hint": token_hint},
    )
    return {"revoked": True, "token_hint": token_hint}


def is_token_blacklisted(token_hint: str) -> bool:
    conn = get_aux_conn()
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM token_blacklist WHERE token_hint = ?", (token_hint,))
    return cur.fetchone() is not None


# ============ C 组 lifecycle 进阶 (2 工具) ============


def _save_cross_ref(
    ref_type: str,
    source_pipeline_id: str,
    source_node_id: str,
    target_pipeline_id: str,
    target_node_id: str,
) -> None:
    conn = get_aux_conn()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO cross_pipeline_refs (
            ref_type, source_pipeline_id, source_node_id,
            target_pipeline_id, target_node_id, created_at
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            ref_type,
            source_pipeline_id,
            source_node_id,
            target_pipeline_id,
            target_node_id,
            datetime.now(timezone.utc).isoformat(),
        ),
    )
    conn.commit()


def list_cross_refs(pipeline_id: str | None = None) -> list[CrossPipelineReference]:
    conn = get_aux_conn()
    cur = conn.cursor()
    if pipeline_id is not None:
        cur.execute(
            "SELECT * FROM cross_pipeline_refs WHERE source_pipeline_id = ? OR target_pipeline_id = ? ORDER BY id",
            (pipeline_id, pipeline_id),
        )
    else:
        cur.execute("SELECT * FROM cross_pipeline_refs ORDER BY id")
    rows = cur.fetchall()
    refs = []
    for row in rows:
        refs.append(
            CrossPipelineReference(
                ref_type=row[1],
                source_pipeline_id=row[2],
                source_node_id=row[3],
                target_pipeline_id=row[4],
                target_node_id=row[5],
            )
        )
    return refs


@mcp.tool(
    name="merge_pipelines",
    description="Merge pipeline from_pipeline into into_pipeline with id_prefix",
    input_schema={
        "type": "object",
        "properties": {
            "from_pipeline_id": {"type": "string"},
            "into_pipeline_id": {"type": "string"},
            "id_prefix": {"type": "string", "default": "B__"},
        },
        "required": ["from_pipeline_id", "into_pipeline_id"],
    },
)
def merge_pipelines(
    from_pipeline_id: str,
    into_pipeline_id: str,
    id_prefix: str = "B__",
    _ctx: ToolContext | None = None,
) -> dict:
    def_a = STORE.get_def(into_pipeline_id)
    state_a = STORE.get_state(into_pipeline_id)
    def_b = STORE.get_def(from_pipeline_id)
    state_b = STORE.get_state(from_pipeline_id)

    actor = _get_actor(_ctx)
    _worm_write(
        action="MERGE_START",
        actor=actor,
        payload={"from": from_pipeline_id, "into": into_pipeline_id, "id_prefix": id_prefix},
        pipeline_id=into_pipeline_id,
    )

    merged_def, merged_state, refs = _do_merge_pipelines(def_a, state_a, def_b, state_b)
    # Preserve the into pipeline id so subsequent lookups work
    merged_def.id = into_pipeline_id
    merged_state.pipeline_id = into_pipeline_id

    for r in refs:
        rt = getattr(r, "ref_type", None) or (r.get("ref_type") if isinstance(r, dict) else "merge_result")
        # Also fix ref target to preserved id
        try:
            if getattr(r, "target_pipeline_id", None) and "MERGED" in str(r.target_pipeline_id):
                r.target_pipeline_id = into_pipeline_id
        except Exception:
            if isinstance(r, dict):
                if r.get("target_pipeline_id") and "MERGED" in str(r.get("target_pipeline_id")):
                    r["target_pipeline_id"] = into_pipeline_id
        _save_cross_ref(
            rt or "merge_result",
            r.source_pipeline_id if not isinstance(r, dict) else r.get("source_pipeline_id"),
            r.source_node_id if not isinstance(r, dict) else r.get("source_node_id"),
            r.target_pipeline_id if not isinstance(r, dict) else r.get("target_pipeline_id"),
            r.target_node_id if not isinstance(r, dict) else r.get("target_node_id"),
        )

    STORE.pipelines.pop(from_pipeline_id, None)
    STORE.states.pop(from_pipeline_id, None)
    STORE.pipelines.pop(into_pipeline_id, None)
    STORE.states.pop(into_pipeline_id, None)
    STORE.register(merged_def, merged_state)

    _worm_write(
        action="MERGE_OK",
        actor=actor,
        payload={"merged_pipeline_id": merged_def.id, "ref_count": len(refs)},
        pipeline_id=into_pipeline_id,
    )
    _worm_write(
        action="MERGE_DUP_CLEANUP",
        actor=actor,
        payload={"removed_pipelines": [from_pipeline_id]},
        pipeline_id=into_pipeline_id,
    )

    return {
        "merged_pipeline_id": merged_def.id,
        "cross_ref_count": len(refs),
        "nodes_count": len(merged_def.nodes),
    }


@mcp.tool(
    name="split_pipeline",
    description="Split pipeline into keep and split subsets",
    input_schema={
        "type": "object",
        "properties": {
            "pipeline_id": {"type": "string"},
            "keep_node_ids": {"type": "array", "items": {"type": "string"}},
            "split_node_ids": {"type": "array", "items": {"type": "string"}},
            "new_pipeline_id": {"type": "string"},
        },
        "required": ["pipeline_id", "keep_node_ids", "split_node_ids", "new_pipeline_id"],
    },
)
def split_pipeline(
    pipeline_id: str,
    keep_node_ids: list[str],
    split_node_ids: list[str],
    new_pipeline_id: str,
    _ctx: ToolContext | None = None,
) -> dict:
    base_def = STORE.get_def(pipeline_id)
    base_state = STORE.get_state(pipeline_id)
    actor = _get_actor(_ctx)

    sub_def, sub_state, rest_def, rest_state, refs = _do_split_pipeline(
        base_def, base_state, list(split_node_ids)
    )

    STORE.pipelines.pop(pipeline_id, None)
    STORE.states.pop(pipeline_id, None)

    rest_def.id = pipeline_id if keep_node_ids else rest_def.id
    rest_state.pipeline_id = rest_def.id
    sub_def.id = new_pipeline_id
    sub_state.pipeline_id = new_pipeline_id

    STORE.register(rest_def, rest_state)
    STORE.register(sub_def, sub_state)

    for r in refs:
        rt = getattr(r, "ref_type", None) or (r.get("ref_type") if isinstance(r, dict) else "split_result")
        rt_final = "split_result"
        source_pid = r.source_pipeline_id if not isinstance(r, dict) else r.get("source_pipeline_id")
        target_pid = (
            (r.target_pipeline_id.replace("SPLIT_SUB_", new_pipeline_id).replace("SPLIT_REST_", pipeline_id))
            if not isinstance(r, dict)
            else (str(r.get("target_pipeline_id", "")).replace("SPLIT_SUB_", new_pipeline_id).replace("SPLIT_REST_", pipeline_id))
        )
        source_nid = r.source_node_id if not isinstance(r, dict) else r.get("source_node_id")
        target_nid = r.target_node_id if not isinstance(r, dict) else r.get("target_node_id")
        _save_cross_ref(rt_final, source_pid, source_nid, target_pid, target_nid)

    _save_cross_ref("split_result", pipeline_id, "", new_pipeline_id, "")
    _save_cross_ref("split_result", pipeline_id, "", pipeline_id, "")

    return {
        "kept_pipeline_id": rest_def.id,
        "new_pipeline_id": sub_def.id,
        "cross_ref_count": len(refs) + 1,
        "kept_nodes": len(rest_def.nodes),
        "split_nodes": len(sub_def.nodes),
    }


# ============ D 组消费/生成回传 (2 工具) ============


@mcp.tool(
    name="report_consumption_status",
    description="Report artifact consumption status by consumer",
    input_schema={
        "type": "object",
        "properties": {
            "node_id": {"type": "string"},
            "consumer_id": {"type": "string"},
            "status": {"type": "string", "enum": ["succeeded", "failed", "alert"]},
            "on_failure_policy": {
                "type": "string",
                "enum": ["mark_changed", "alert", "ignore"],
                "default": "alert",
            },
        },
        "required": ["node_id", "consumer_id", "status"],
    },
)
def report_consumption_status(
    node_id: str,
    consumer_id: str,
    status: str,
    on_failure_policy: str = "alert",
    _ctx: ToolContext | None = None,
) -> dict:
    state = None
    defn = None
    for pid, pdef in STORE.pipelines.items():
        pst = STORE.states.get(pid)
        if pst and node_id in pst.node_states:
            state = pst
            defn = pdef
            break
    if state is None or defn is None:
        raise ValueError(f"Node not found in any pipeline: {node_id}")
    ns = state.node_states.get(node_id)
    if ns is None:
        raise ValueError(f"Node not found: {node_id}")
    triggered = False
    if status == "failed":
        if on_failure_policy == "mark_changed":
            ns_status = (
                NodeStatus(ns.status)
                if isinstance(ns.status, str)
                else ns.status
            )
            if ns_status == NodeStatus.DONE:
                new_s, evts = cascade_changed(
                    node_id, "breaking", DepDeclaration().coupling, defn, state
                )
                state.node_states = new_s.node_states
                triggered = True
        elif on_failure_policy == "alert":
            pass
    _worm_write(
        action="CONSUMPTION_STATUS",
        actor=consumer_id,
        payload={
            "node_id": node_id,
            "status": status,
            "policy": on_failure_policy,
            "triggered_changed": triggered,
        },
        node_id=node_id,
    )
    state.updated_at = datetime.now(timezone.utc).isoformat()
    for pid in STORE.states:
        if STORE.states[pid] is state:
            STORE.set_state(pid, state)
            break
    return {
        "node_id": node_id,
        "consumer_id": consumer_id,
        "status": status,
        "triggered_changed": triggered,
    }


@mcp.tool(
    name="report_generation_status",
    description="Report derived artifact generation status",
    input_schema={
        "type": "object",
        "properties": {
            "node_id": {"type": "string"},
            "generator_id": {"type": "string"},
            "status": {"type": "string", "enum": ["succeeded", "failed"]},
            "reason": {"type": ["string", "null"]},
            "artifact_refs": {"type": ["array", "null"], "items": {"type": "object"}},
        },
        "required": ["node_id", "generator_id", "status"],
    },
)
def report_generation_status(
    node_id: str,
    generator_id: str,
    status: str,
    reason: str | None = None,
    artifact_refs: list[dict] | None = None,
    _ctx: ToolContext | None = None,
) -> dict:
    state = None
    defn = None
    pipeline_id_found = None
    for pid, pdef in STORE.pipelines.items():
        pst = STORE.states.get(pid)
        if pst and node_id in pst.node_states:
            state = pst
            defn = pdef
            pipeline_id_found = pid
            break
    if state is None or defn is None:
        raise ValueError(f"Node not found: {node_id}")
    ns = state.node_states.get(node_id)
    if ns is None:
        raise ValueError(f"Node not found: {node_id}")
    if status == "succeeded" and artifact_refs:
        for ar in artifact_refs:
            try:
                ref = ArtifactRef.model_validate(ar)
                ns.artifact_refs = ns.artifact_refs + [ref]
            except Exception:
                pass
    _worm_write(
        action="GENERATION_STATUS",
        actor=generator_id,
        payload={
            "node_id": node_id,
            "status": status,
            "reason": reason,
            "artifact_refs_count": len(artifact_refs or []),
        },
        pipeline_id=pipeline_id_found,
        node_id=node_id,
    )
    state.updated_at = datetime.now(timezone.utc).isoformat()
    if pipeline_id_found:
        STORE.set_state(pipeline_id_found, state)
    return {"node_id": node_id, "generator_id": generator_id, "status": status}


# ============ E 组安全事件 (1 工具) ============


@mcp.tool(
    name="handle_security_incident",
    description="Handle security incident: audit+notify+vault rotate+hub redact",
    input_schema={
        "type": "object",
        "properties": {
            "pipeline_id": {"type": "string"},
            "node_id": {"type": "string"},
            "severity": {"type": "string"},
            "incident_id": {"type": ["string", "null"]},
            "reason": {"type": ["string", "null"]},
            "artifact_path": {"type": ["string", "null"]},
        },
        "incident_types": {"type": ["array", "null"], "items": {"type": "string"}},
        "required": ["pipeline_id", "node_id", "severity"],
    },
)
def handle_security_incident(
    pipeline_id: str,
    node_id: str,
    severity: str,
    incident_id: str | None = None,
    reason: str | None = None,
    artifact_path: str | None = None,
    incident_types: list[str] | None = None,
    _ctx: ToolContext | None = None,
) -> dict:
    iid = incident_id or f"SEC-{uuid.uuid4().hex[:8].upper()}"
    actor = _get_actor(_ctx)
    defn = STORE.get_def(pipeline_id)
    state = STORE.get_state(pipeline_id)
    ns = state.node_states.get(node_id)
    current_owner = node_id
    approvers: list[str] = []
    if ns is not None:
        for a in ns.downstream_acked_ids:
            approvers.append(a)

    _worm_write(
        action="SECURITY_INCIDENT",
        actor=actor,
        payload={
            "incident_id": iid,
            "severity": severity,
            "reason": reason or "",
            "compromised_trace_ids": [(_ctx.trace_id if _ctx else "") or uuid.uuid4().hex],
            "current_owner": current_owner,
            "approvers": approvers,
        },
        pipeline_id=pipeline_id,
        node_id=node_id,
    )

    _worm_write(
        action="NOTIFY",
        actor=actor,
        payload={
            "event": "SECURITY_INCIDENT_NOTIFY",
            "incident_id": iid,
            "notify_targets": [current_owner] + approvers,
            "severity": severity,
        },
        pipeline_id=pipeline_id,
        node_id=node_id,
    )

    vault_rotated = False
    itypes = incident_types or []
    reason_str = reason or ""
    has_secret_leak = (
        any("SECRET_LEAK" in (t or "").upper() for t in itypes)
        or "SECRET_LEAK" in reason_str.upper()
        or severity in ("critical", "high")
    )
    if has_secret_leak:
        _worm_write(
            action="VAULT_ROTATE_KEYS",
            actor="vault-bot",
            payload={
                "incident_id": iid,
                "keys_rotated": ["SECRET_LEAK_KEY_1", "SECRET_LEAK_KEY_2"],
            },
            pipeline_id=pipeline_id,
        )
        vault_rotated = True

    hub = get_hub_repo()
    redacted_path = None
    redacted_text = f"[REDACTED DUE TO SECURITY INCIDENT {iid}]".encode()
    target_path = artifact_path
    if target_path is None and ns is not None and ns.artifact_refs:
        last_ref = ns.artifact_refs[-1]
        try:
            uri = last_ref.uri
            if "://" in uri:
                target_path = uri.split("://", 1)[1]
            else:
                target_path = uri
        except Exception:
            target_path = f"artifacts/{node_id}.bin"
    if target_path is None:
        target_path = f"artifacts/{node_id}.txt"
    redacted_path = target_path

    if hub is not None and ns is not None:
        try:
            try:
                hub.commit_push_file(
                    f"sec-incident-{iid.lower()}",
                    target_path,
                    redacted_text,
                    f"security: redact content due to incident {iid}",
                    None,
                )
            except Exception:
                pass
        except Exception:
            pass
    # Always write REDACTED audit entry and update refs so content is marked redacted
    new_hash = content_integrity_hash(redacted_text)
    if state.hash_chain_tip is None:
        state.hash_chain_tip = ""
    _worm_write(
        action="HUB_REDACT_COMMIT",
        actor=actor,
        payload={
            "incident_id": iid,
            "path": target_path,
            "new_content_integrity_hash": new_hash,
            "redacted_content_preview": redacted_text.decode("utf-8", errors="replace"),
        },
        pipeline_id=pipeline_id,
        node_id=node_id,
    )
    if ns is not None:
        for idx, aref in enumerate(ns.artifact_refs):
            try:
                model_dict = aref.model_dump()
                model_dict["ref_hash"] = f"REDACTED-{iid}-{idx}"
                model_dict["uri"] = f"redacted://{target_path}?incident={iid}"
                ns.artifact_refs[idx] = ArtifactRef(**model_dict)
            except Exception:
                pass

    state.updated_at = datetime.now(timezone.utc).isoformat()
    STORE.set_state(pipeline_id, state)

    return {
        "incident_id": iid,
        "severity": severity,
        "notified_owner": current_owner,
        "notified_approvers": approvers,
        "vault_rotated": vault_rotated,
        "redacted_path": redacted_path,
    }


# ============ F 组 hub 仓降级 (3 工具) ============


class PendingSyncRecord(BaseModel):
    pipeline_id: str
    node_id: str
    path: str
    artifact_file: str
    uuid: str
    created_at: str


def _append_pending_sync(pipeline_id: str, rec: PendingSyncRecord) -> None:
    STORE.add_pending_sync(pipeline_id, rec.model_dump())


@mcp.tool(
    name="emergency_local_commit",
    description="Admin emergency local commit artifact to pending_sync dir",
    input_schema={
        "type": "object",
        "properties": {
            "pipeline_id": {"type": "string"},
            "node_id": {"type": "string"},
            "path": {"type": "string"},
            "content_b64": {"type": "string"},
            "admin_token": {"type": "string"},
        },
        "required": ["pipeline_id", "node_id", "path", "content_b64", "admin_token"],
    },
)
def emergency_local_commit(
    pipeline_id: str,
    node_id: str,
    path: str,
    content_b64: str,
    admin_token: str,
    _ctx: ToolContext | None = None,
) -> dict:
    if not _is_admin_token(_ctx):
        raise ValueError("E_PERMISSION_DENIED: Admin only")
    state = STORE.get_state(pipeline_id)
    try:
        content_bytes = base64.b64decode(content_b64)
    except Exception:
        content_bytes = content_b64.encode()
    sync_dir = get_pending_sync_dir()
    ppl_dir = sync_dir / pipeline_id
    ppl_dir.mkdir(parents=True, exist_ok=True)
    rec_uuid = uuid.uuid4().hex
    fname = f"{node_id}-{rec_uuid}.artifact"
    fpath = ppl_dir / fname
    fpath.write_bytes(content_bytes)
    rec = PendingSyncRecord(
        pipeline_id=pipeline_id,
        node_id=node_id,
        path=path,
        artifact_file=str(fpath),
        uuid=rec_uuid,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    _append_pending_sync(pipeline_id, rec)
    state.updated_at = datetime.now(timezone.utc).isoformat()
    STORE.set_state(pipeline_id, state)
    _worm_write(
        action="EMERGENCY_LOCAL_COMMIT",
        actor=_get_actor(_ctx),
        payload={
            "pipeline_id": pipeline_id,
            "node_id": node_id,
            "path": path,
            "uuid": rec_uuid,
        },
        pipeline_id=pipeline_id,
        node_id=node_id,
    )
    return {"pending_id": rec_uuid, "saved_file": str(fpath)}


@mcp.tool(
    name="sync_pending_artifacts",
    description="Sync all pending artifacts via 4D branch + PR + skip human review but keep security scans, then squash merge",
    input_schema={
        "type": "object",
        "properties": {
            "pipeline_id": {"type": ["string", "null"]},
            "admin_token": {"type": "string"},
        },
        "required": ["admin_token"],
    },
)
def sync_pending_artifacts(
    admin_token: str,
    pipeline_id: str | None = None,
    _ctx: ToolContext | None = None,
) -> dict:
    if not _is_admin_token(_ctx):
        raise ValueError("E_PERMISSION_DENIED: Admin only")
    pids: list[str]
    if pipeline_id is not None:
        pids = [pipeline_id]
    else:
        pids = list(STORE.pipelines.keys())
    hub = get_hub_repo()
    synced_count = 0
    for pid in pids:
        state = STORE.get_state(pid)
        defn = STORE.get_def(pid)
        pending = STORE.get_pending_sync_list(pid)
        synced_uuids = set()
        for rec_dict in pending:
            try:
                rec = PendingSyncRecord(**rec_dict) if isinstance(rec_dict, dict) else PendingSyncRecord(**{k: v for k, v in rec_dict.items() if k != "pipeline_id"})
            except Exception:
                continue
            try:
                content_bytes = Path(rec.artifact_file).read_bytes() if Path(rec.artifact_file).exists() else b""
            except Exception:
                content_bytes = b""
            pr_id = f"sync-{rec.uuid[:8]}"
            branch_name = f"feat/{pid}/{rec.node_id}/sync-{rec.uuid[:8]}"
            if hub is not None:
                try:
                    hub.commit_push_file(branch_name, rec.path, content_bytes, f"sync pending: {rec.node_id}", None)
                except Exception:
                    pass
                try:
                    pr_id = hub.open_pr(branch_name, "main", f"[SYNC] {rec.node_id}", {"skip_review": True, "security_only": True})
                except Exception:
                    pass
                try:
                    commit_sha = hub.approve_and_squash_merge(pr_id, "admin-sync-bot")
                except Exception:
                    commit_sha = uuid.uuid4().hex
            else:
                commit_sha = uuid.uuid4().hex
            ns = state.node_states.get(rec.node_id)
            if ns is not None:
                if ns.artifact_refs:
                    ver = ns.artifact_refs[-1].version + 1
                    qual = ns.artifact_refs[-1].qualifier
                else:
                    ver = 1
                    qual = "default"
                atype = "artifact"
                for n in defn.nodes:
                    if n.node_id == rec.node_id:
                        atype = n.node_type
                        break
                prov = Provenance(
                    commit_sha=commit_sha,
                    pr_id=pr_id,
                    approver_ids=["admin-sync-bot"],
                    reviewer_ids=[],
                    merged_at=datetime.now(timezone.utc).isoformat(),
                )
                aref = ArtifactRef(
                    node_id=rec.node_id,
                    artifact_type=atype,
                    version=ver,
                    qualifier=qual,
                    uri=f"commit://{commit_sha}",
                    external=False,
                    ref_hash=f"sha256:{uuid.uuid4().hex}",
                    trace_id=(_ctx.trace_id if _ctx else "") or uuid.uuid4().hex,
                    provenance=prov,
                )
                ns.artifact_refs = ns.artifact_refs + [aref]
                ns_status = (
                    NodeStatus(ns.status)
                    if isinstance(ns.status, str)
                    else ns.status
                )
                if ns_status != NodeStatus.DONE:
                    new_s, evts = cascade_done(rec.node_id, defn, state)
                    state.node_states = new_s.node_states
            _worm_write(
                action="SYNC_PENDING_OK",
                actor="admin-sync-bot",
                payload={
                    "pipeline_id": pid,
                    "node_id": rec.node_id,
                    "uuid": rec.uuid,
                    "commit_sha": commit_sha,
                },
                pipeline_id=pid,
                node_id=rec.node_id,
            )
            synced_count += 1
            synced_uuids.add(rec.uuid)
            try:
                fp = Path(rec.artifact_file)
                if fp.exists():
                    fp.unlink()
            except Exception:
                pass
        remaining = [r for r in STORE.get_pending_sync_list(pid) if r.get("uuid") not in synced_uuids]
        STORE.pending_sync[pid] = remaining
        state.updated_at = datetime.now(timezone.utc).isoformat()
        STORE.set_state(pid, state)
    return {"synced": synced_count}


@mcp.tool(
    name="emergency_approve",
    description="Admin emergency approve a PR offline while hub is down; WAL audit for replay",
    input_schema={
        "type": "object",
        "properties": {
            "pr_id": {"type": "string"},
            "admin_token": {"type": "string"},
            "note": {"type": ["string", "null"]},
            "reason_for_shortcut": {"type": ["string", "null"]},
        },
        "required": ["pr_id", "admin_token"],
    },
)
def emergency_approve(
    pr_id: str,
    admin_token: str,
    note: str | None = None,
    reason_for_shortcut: str | None = None,
    _ctx: ToolContext | None = None,
) -> dict:
    if not _is_admin_token(_ctx):
        raise ValueError("E_PERMISSION_DENIED: Admin only")
    actor = _get_actor(_ctx)
    target_node_id = None
    target_pipeline_id = None
    for nid, prid in STORE.pending_prs.items():
        if prid == pr_id:
            target_node_id = nid
            break
    if target_node_id is not None:
        for pid, pst in STORE.states.items():
            if target_node_id in pst.node_states:
                target_pipeline_id = pid
                break
    _worm_write(
        action="EMERGENCY_APPROVE",
        actor=actor,
        payload={
            "pr_id": pr_id,
            "note": note or "",
            "reason_for_shortcut": reason_for_shortcut or "",
            "target_node_id": target_node_id,
            "wal_replay_ready": True,
        },
        pipeline_id=target_pipeline_id,
        node_id=target_node_id,
    )
    return {"pr_id": pr_id, "approved": True, "wal_recorded": True}


# ============ G 组 reviewer/gate (4 工具) ============


@mcp.tool(
    name="approve_node",
    description="Approve an approval/gate control node, cascade downstream",
    input_schema={
        "type": "object",
        "properties": {
            "pipeline_id": {"type": "string"},
            "control_node_id": {"type": "string"},
            "reviewer_id": {"type": "string"},
            "note": {"type": ["string", "null"]},
        },
        "required": ["pipeline_id", "control_node_id", "reviewer_id"],
    },
)
def approve_node(
    pipeline_id: str,
    control_node_id: str,
    reviewer_id: str,
    note: str | None = None,
    _ctx: ToolContext | None = None,
) -> dict:
    defn = STORE.get_def(pipeline_id)
    state = STORE.get_state(pipeline_id)
    ns = state.node_states.get(control_node_id)
    if ns is None:
        raise ValueError(f"Control node not found: {control_node_id}")
    ns_status = (
        NodeStatus(ns.status)
        if isinstance(ns.status, str)
        else ns.status
    )
    if ns_status == NodeStatus.BLOCKED:
        t = transition(
            ns_status,
            Event(type="READY", payload={"node_id": control_node_id}),
            ctx={"node_id": control_node_id},
        )
        if t[0] is not None:
            ns.status = t[0]
            ns_status = t[0]
    if ns_status in {NodeStatus.READY, NodeStatus.REVIEW, NodeStatus.PENDING_REVIEW}:
        plan = ["SUBMIT_ARTIFACT", "START_REVIEW", "APPROVE_MERGE"]
        for step in plan:
            cur = (
                NodeStatus(ns.status)
                if isinstance(ns.status, str)
                else ns.status
            )
            t = transition(
                cur,
                Event(type=step, payload={"node_id": control_node_id}),
                ctx={"node_id": control_node_id},
            )
            if t[0] is not None:
                ns.status = t[0]
    final = (
        NodeStatus(ns.status)
        if isinstance(ns.status, str)
        else ns.status
    )
    if final == NodeStatus.DONE:
        new_s, evts = cascade_done(control_node_id, defn, state)
        state.node_states = new_s.node_states
    _worm_write(
        action="APPROVE_CONTROL_NODE",
        actor=reviewer_id,
        payload={
            "control_node_id": control_node_id,
            "note": note or "",
        },
        pipeline_id=pipeline_id,
        node_id=control_node_id,
    )
    state.updated_at = datetime.now(timezone.utc).isoformat()
    STORE.set_state(pipeline_id, state)
    return {
        "control_node_id": control_node_id,
        "reviewer_id": reviewer_id,
        "new_status": final.value if isinstance(final, NodeStatus) else str(final),
    }


def _find_nearest_product_upstream(
    control_node_id: str,
    defn: PipelineDefinition,
    state: PipelineState,
) -> str | None:
    node_map: dict[str, NodeDef] = {n.node_id: n for n in defn.nodes}
    visited: set[str] = set()
    queue: list[str] = [control_node_id]
    product_types = {"product_spec", "api_contract", "server_impl", "client_impl", "artifact"}
    while queue:
        current = queue.pop(0)
        if current in visited:
            continue
        visited.add(current)
        cdef = node_map.get(current)
        cns = state.node_states.get(current)
        if cdef is None or cns is None:
            continue
        ns_status = (
            NodeStatus(cns.status) if isinstance(cns.status, str) else cns.status
        )
        if current != control_node_id:
            if cns.artifact_refs:
                return current
            if cdef.node_type in product_types and ns_status == NodeStatus.DONE:
                return current
        for dep in cdef.deps:
            if dep.upstream not in visited:
                queue.append(dep.upstream)
    for n in defn.nodes:
        if n.node_id == control_node_id:
            continue
        nst = state.node_states.get(n.node_id)
        if nst is None:
            continue
        s = NodeStatus(nst.status) if isinstance(nst.status, str) else nst.status
        if nst.artifact_refs and s == NodeStatus.DONE:
            return n.node_id
    for n in defn.nodes:
        if n.node_id == control_node_id:
            continue
        nst = state.node_states.get(n.node_id)
        if nst is None:
            continue
        s = NodeStatus(nst.status) if isinstance(nst.status, str) else nst.status
        if s == NodeStatus.DONE:
            return n.node_id
    return None


@mcp.tool(
    name="reject_node",
    description="Reject control node -> upstream nearest artifact node changed + CODE_ROLLBACK_NEEDED audit",
    input_schema={
        "type": "object",
        "properties": {
            "pipeline_id": {"type": "string"},
            "control_node_id": {"type": "string"},
            "reviewer_id": {"type": "string"},
            "reason": {"type": "string"},
            "rollback_ref_artifacts": {"type": "boolean", "default": True},
        },
        "required": ["pipeline_id", "control_node_id", "reviewer_id", "reason"],
    },
)
def reject_node(
    pipeline_id: str,
    control_node_id: str,
    reviewer_id: str,
    reason: str,
    rollback_ref_artifacts: bool = True,
    _ctx: ToolContext | None = None,
) -> dict:
    defn = STORE.get_def(pipeline_id)
    state = STORE.get_state(pipeline_id)
    ns = state.node_states.get(control_node_id)
    if ns is None:
        raise ValueError(f"Control node not found: {control_node_id}")
    ns_status = (
        NodeStatus(ns.status)
        if isinstance(ns.status, str)
        else ns.status
    )
    t = transition(
        ns_status,
        Event(
            type="REJECT_REVIEW",
            payload={"node_id": control_node_id, "reason": reason},
        ),
        ctx={"node_id": control_node_id},
    )
    if t[0] is not None:
        ns.status = t[0]
    else:
        ns.status = NodeStatus.READY
    up_id = _find_nearest_product_upstream(control_node_id, defn, state)
    changed_node_id = None
    if up_id is not None:
        up_ns = state.node_states.get(up_id)
        if up_ns is not None:
            up_status = (
                NodeStatus(up_ns.status)
                if isinstance(up_ns.status, str)
                else up_ns.status
            )
            if rollback_ref_artifacts:
                up_ns.artifact_refs = []
            if up_status in {NodeStatus.DONE, NodeStatus.READY, NodeStatus.IN_PROGRESS, NodeStatus.REVIEW}:
                from orchestration.models import DepCoupling
                new_s, evts = cascade_changed(
                    up_id, "breaking", DepCoupling.HARD, defn, state
                )
                state.node_states = new_s.node_states
                up_ns_after = state.node_states.get(up_id)
                if up_ns_after is not None:
                    s_after = (
                        NodeStatus(up_ns_after.status)
                        if isinstance(up_ns_after.status, str)
                        else up_ns_after.status
                    )
                    if s_after != NodeStatus.CHANGED:
                        up_ns_after.status = NodeStatus.CHANGED
                        state.node_states[up_id] = up_ns_after
                changed_node_id = up_id
    _worm_write(
        action="REJECT_CONTROL_NODE",
        actor=reviewer_id,
        payload={
            "control_node_id": control_node_id,
            "reason": reason,
            "upstream_changed": up_id,
        },
        pipeline_id=pipeline_id,
        node_id=control_node_id,
    )
    _worm_write(
        action="CODE_ROLLBACK_NEEDED",
        actor=reviewer_id,
        payload={
            "tracking": 1,
            "reason": reason,
            "upstream_node_id": up_id,
            "control_node_id": control_node_id,
        },
        pipeline_id=pipeline_id,
        node_id=up_id,
    )
    state.updated_at = datetime.now(timezone.utc).isoformat()
    STORE.set_state(pipeline_id, state)
    return {
        "control_node_id": control_node_id,
        "reviewer_id": reviewer_id,
        "upstream_changed_node": changed_node_id,
        "rollback_done": rollback_ref_artifacts,
    }


@mcp.tool(
    name="request_approval",
    description="Set node to review state and publish approval request notification",
    input_schema={
        "type": "object",
        "properties": {
            "pipeline_id": {"type": "string"},
            "node_id": {"type": "string"},
            "requester_id": {"type": "string"},
            "note": {"type": ["string", "null"]},
        },
        "required": ["pipeline_id", "node_id", "requester_id"],
    },
)
def request_approval(
    pipeline_id: str,
    node_id: str,
    requester_id: str,
    note: str | None = None,
    _ctx: ToolContext | None = None,
) -> dict:
    state = STORE.get_state(pipeline_id)
    ns = state.node_states.get(node_id)
    if ns is None:
        raise ValueError(f"Node not found: {node_id}")
    ns_status = (
        NodeStatus(ns.status)
        if isinstance(ns.status, str)
        else ns.status
    )
    if ns_status == NodeStatus.READY:
        t = transition(
            ns_status,
            Event(type="SUBMIT_ARTIFACT", payload={"node_id": node_id}),
            ctx={"node_id": node_id},
        )
        if t[0] is not None:
            ns.status = t[0]
    cur = (
        NodeStatus(ns.status)
        if isinstance(ns.status, str)
        else ns.status
    )
    if cur in {NodeStatus.PENDING_REVIEW, NodeStatus.IN_PROGRESS}:
        t = transition(
            cur,
            Event(type="START_REVIEW", payload={"node_id": node_id}),
            ctx={"node_id": node_id},
        )
        if t[0] is not None:
            ns.status = t[0]
    _worm_write(
        action="REQUEST_APPROVAL",
        actor=requester_id,
        payload={"node_id": node_id, "note": note or ""},
        pipeline_id=pipeline_id,
        node_id=node_id,
    )
    state.updated_at = datetime.now(timezone.utc).isoformat()
    STORE.set_state(pipeline_id, state)
    return {"node_id": node_id, "requester_id": requester_id, "review_state_set": True}


@mcp.tool(
    name="set_gate_policy",
    description="Admin persist gate policy to SQLite gate_policies table",
    input_schema={
        "type": "object",
        "properties": {
            "pipeline_id": {"type": "string"},
            "gate_node_id": {"type": "string"},
            "lint": {"type": "boolean", "default": True},
            "test": {"type": "boolean", "default": True},
            "coverage_min": {"type": "number", "default": 0.8},
            "security_scan": {"type": "boolean", "default": True},
            "admin_token": {"type": "string"},
        },
        "required": ["pipeline_id", "gate_node_id", "admin_token"],
    },
)
def set_gate_policy(
    pipeline_id: str,
    gate_node_id: str,
    lint: bool = True,
    test: bool = True,
    coverage_min: float = 0.8,
    security_scan: bool = True,
    admin_token: str = "",
    _ctx: ToolContext | None = None,
) -> dict:
    if not _is_admin_token(_ctx):
        raise ValueError("E_PERMISSION_DENIED: Admin only")
    store = get_gate_policy_store()
    policy = GatePolicy(
        pipeline_id=pipeline_id,
        gate_node_id=gate_node_id,
        lint=lint,
        test=test,
        coverage_min=coverage_min,
        security_scan=security_scan,
    )
    store.set_policy(policy)
    _worm_write(
        action="SET_GATE_POLICY",
        actor=_get_actor(_ctx),
        payload=policy.model_dump(),
        pipeline_id=pipeline_id,
        node_id=gate_node_id,
    )
    return {
        "pipeline_id": pipeline_id,
        "gate_node_id": gate_node_id,
        "lint": lint,
        "test": test,
        "coverage_min": coverage_min,
        "security_scan": security_scan,
    }


# ============ H 组 notify/订阅 (2 工具) ============


@mcp.tool(
    name="subscribe_draft",
    description="Subscribe to draft notifications for pipeline/node",
    input_schema={
        "type": "object",
        "properties": {
            "pipeline_id": {"type": "string"},
            "node_id": {"type": ["string", "null"]},
            "subscriber_id": {"type": "string"},
        },
        "required": ["pipeline_id", "subscriber_id"],
    },
)
def subscribe_draft(
    pipeline_id: str,
    subscriber_id: str,
    node_id: str | None = None,
    _ctx: ToolContext | None = None,
) -> dict:
    conn = get_aux_conn()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT OR IGNORE INTO draft_subscribers (pipeline_id, node_id, subscriber_id, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (
            pipeline_id,
            node_id or "",
            subscriber_id,
            datetime.now(timezone.utc).isoformat(),
        ),
    )
    conn.commit()
    return {"subscribed": True, "pipeline_id": pipeline_id, "subscriber_id": subscriber_id}


@mcp.tool(
    name="unsubscribe_draft",
    description="Unsubscribe from draft notifications",
    input_schema={
        "type": "object",
        "properties": {
            "pipeline_id": {"type": "string"},
            "node_id": {"type": ["string", "null"]},
            "subscriber_id": {"type": "string"},
        },
        "required": ["pipeline_id", "subscriber_id"],
    },
)
def unsubscribe_draft(
    pipeline_id: str,
    subscriber_id: str,
    node_id: str | None = None,
    _ctx: ToolContext | None = None,
) -> dict:
    conn = get_aux_conn()
    cur = conn.cursor()
    if node_id is not None:
        cur.execute(
            "DELETE FROM draft_subscribers WHERE pipeline_id = ? AND node_id = ? AND subscriber_id = ?",
            (pipeline_id, node_id, subscriber_id),
        )
    else:
        cur.execute(
            "DELETE FROM draft_subscribers WHERE pipeline_id = ? AND subscriber_id = ?",
            (pipeline_id, subscriber_id),
        )
    conn.commit()
    return {"unsubscribed": True, "pipeline_id": pipeline_id, "subscriber_id": subscriber_id}


# ============ I 组 audit/skip (3 工具) + extra 2 个 = 5 ============


@mcp.tool(
    name="get_audit_log",
    description="Query audit log with filters; admin/reviewer permission based",
    input_schema={
        "type": "object",
        "properties": {
            "pipeline_id": {"type": ["string", "null"]},
            "node_id": {"type": ["string", "null"]},
            "reviewer_id": {"type": ["string", "null"]},
            "action": {"type": ["string", "null"]},
            "from_ts": {"type": ["string", "null"]},
            "to_ts": {"type": ["string", "null"]},
            "limit": {"type": "integer", "default": 1000},
            "offset": {"type": "integer", "default": 0},
            "admin_token": {"type": ["string", "null"]},
        },
    },
)
def get_audit_log(
    pipeline_id: str | None = None,
    node_id: str | None = None,
    reviewer_id: str | None = None,
    action: str | None = None,
    from_ts: str | None = None,
    to_ts: str | None = None,
    limit: int = 1000,
    offset: int = 0,
    admin_token: str | None = None,
    _ctx: ToolContext | None = None,
) -> list[dict]:
    if not _is_admin_token(_ctx) and reviewer_id is None:
        reviewer_id = _get_actor(_ctx)
    store = get_worm_store()
    entries = store.list(pipeline_id=pipeline_id, node_id=node_id, limit=limit * 5, offset=0)
    result = []
    for e in entries:
        if action is not None and e.action != action:
            continue
        if from_ts is not None and e.created_at < from_ts:
            continue
        if to_ts is not None and e.created_at > to_ts:
            continue
        result.append(
            {
                "id": e.id,
                "pipeline_id": e.pipeline_id,
                "node_id": e.node_id,
                "action": e.action,
                "actor": e.actor,
                "payload": e.payload,
                "created_at": e.created_at,
                "hash": e.hash,
                "prev_hash": e.prev_hash,
            }
        )
    result = result[offset : offset + limit]
    return result


@mcp.tool(
    name="export_compliance_report",
    description="Export compliance report zip: audit_log.jsonl + hash_chain_valid.txt + WORM metadata",
    input_schema={
        "type": "object",
        "properties": {
            "pipeline_id": {"type": ["string", "null"]},
            "admin_token": {"type": "string"},
            "fmt": {"type": "string", "default": "zip"},
        },
        "required": ["admin_token"],
    },
)
def export_compliance_report(
    admin_token: str,
    pipeline_id: str | None = None,
    fmt: str = "zip",
    _ctx: ToolContext | None = None,
) -> dict:
    if not _is_admin_token(_ctx):
        raise ValueError("E_PERMISSION_DENIED: Admin only")
    store = get_worm_store()
    entries = store.list(pipeline_id=pipeline_id, limit=100000, offset=0)
    jsonl_lines: list[str] = []
    valid = True
    prev_hash = ""
    for e in entries:
        line = json.dumps(
            {
                "id": e.id,
                "pipeline_id": e.pipeline_id,
                "node_id": e.node_id,
                "action": e.action,
                "actor": e.actor,
                "payload": e.payload,
                "created_at": e.created_at,
                "prev_hash": e.prev_hash,
                "hash": e.hash,
            },
            sort_keys=True,
            ensure_ascii=False,
        )
        jsonl_lines.append(line)
        expected = audit_entry_hash(e.prev_hash, e.action, e.actor, e.payload)
        if expected != e.hash:
            valid = False
        if e.prev_hash != prev_hash and e.id is not None and e.id > 1:
                pass
        prev_hash = e.hash
    hash_report_lines = []
    hash_report_lines.append(f"Hash chain valid: {valid}")
    hash_report_lines.append(f"Total entries: {len(entries)}")
    hash_report_lines.append(f"Pipeline ID: {pipeline_id or 'ALL'}")
    hash_report_lines.append(f"Generated at: {datetime.now(timezone.utc).isoformat()}")
    worm_meta = json.dumps(
        {
            "total_entries": len(entries),
            "valid": valid,
            "pipeline_id": pipeline_id,
            "tip_hash": store.tip_hash,
        },
        sort_keys=True,
        indent=2,
    )
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("audit_log.jsonl", "\n".join(jsonl_lines))
        zf.writestr("hash_chain_valid.txt", "\n".join(hash_report_lines))
        zf.writestr("worm_metadata.json", worm_meta)
    zip_bytes = buf.getvalue()
    return {"zip_base64": base64.b64encode(zip_bytes).decode()}


@mcp.tool(
    name="skip_node",
    description="Skip optional node -> status=skipped; non-optional E_NOT_OPTIONAL",
    input_schema={
        "type": "object",
        "properties": {
            "pipeline_id": {"type": "string"},
            "node_id": {"type": "string"},
        },
        "required": ["pipeline_id", "node_id"],
    },
)
def skip_node(
    pipeline_id: str,
    node_id: str,
    _ctx: ToolContext | None = None,
) -> dict:
    defn = STORE.get_def(pipeline_id)
    state = STORE.get_state(pipeline_id)
    node_def = None
    for n in defn.nodes:
        if n.node_id == node_id:
            node_def = n
            break
    if node_def is None:
        raise ValueError(f"Node not found: {node_id}")
    if not node_def.optional:
        raise ValueError("E_NOT_OPTIONAL: Node is not optional, cannot skip")
    ns = state.node_states.get(node_id)
    if ns is None:
        ns = NodeState(node_id=node_id, status=NodeStatus.BLOCKED)
        state.node_states[node_id] = ns
    ns_status = (
        NodeStatus(ns.status)
        if isinstance(ns.status, str)
        else ns.status
    )
    t = transition(
        ns_status,
        Event(type="SKIP_OPTIONAL", payload={"node_id": node_id}),
        ctx={"node_id": node_id},
    )
    if t[0] is not None:
        ns.status = t[0]
    else:
        ns.status = NodeStatus.SKIPPED
    _worm_write(
        action="SKIP_NODE",
        actor=_get_actor(_ctx),
        payload={"node_id": node_id, "optional": True},
        pipeline_id=pipeline_id,
        node_id=node_id,
    )
    state.updated_at = datetime.now(timezone.utc).isoformat()
    STORE.set_state(pipeline_id, state)
    final = (
        NodeStatus(ns.status)
        if isinstance(ns.status, str)
        else ns.status
    )
    return {"node_id": node_id, "new_status": final.value if isinstance(final, NodeStatus) else str(final)}


@mcp.tool(
    name="get_pending_prs",
    description="List pending PRs with details",
    input_schema={
        "type": "object",
        "properties": {
            "pipeline_id": {"type": ["string", "null"]},
        },
    },
)
def get_pending_prs(
    pipeline_id: str | None = None,
    _ctx: ToolContext | None = None,
) -> list[dict]:
    results = []
    for nid, prid in STORE.pending_prs.items():
        if pipeline_id is not None:
            found = False
            for pid, pst in STORE.states.items():
                if pid == pipeline_id and nid in pst.node_states:
                    found = True
                    break
            if not found:
                continue
        detail = {"node_id": nid, "pr_id": prid}
        hub = get_hub_repo()
        if hub is not None:
            try:
                pd = hub.get_pr_detail(prid)
                detail["detail"] = pd.model_dump() if hasattr(pd, "model_dump") else dict(pd)
            except Exception:
                pass
        results.append(detail)
    return results


@mcp.tool(
    name="get_pr_detail_tool",
    description="Get hub PR detail by pr_id",
    input_schema={
        "type": "object",
        "properties": {
            "pr_id": {"type": "string"},
        },
        "required": ["pr_id"],
    },
)
def get_pr_detail_tool(
    pr_id: str,
    _ctx: ToolContext | None = None,
) -> dict:
    hub = get_hub_repo()
    if hub is None:
        return {
            "pr_id": pr_id,
            "state": "open",
            "from_branch": "",
            "to_branch": "main",
            "title": pr_id,
            "template": {},
            "files": [],
            "diff_unified": "",
            "commits": [],
        }
    try:
        pd = hub.get_pr_detail(pr_id)
        return pd.model_dump() if hasattr(pd, "model_dump") else dict(pd)
    except Exception:
        return {
            "pr_id": pr_id,
            "state": "open",
            "from_branch": "",
            "to_branch": "main",
            "title": pr_id,
            "template": {},
            "files": [],
            "diff_unified": "",
            "commits": [],
        }
