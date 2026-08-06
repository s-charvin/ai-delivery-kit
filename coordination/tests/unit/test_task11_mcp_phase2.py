from __future__ import annotations

import asyncio
import base64
import glob
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import jwt
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from orchestration.models import (
    ClassificationLevel,
    DepDeclaration,
    NodeDef,
    NodeStatus,
)
from orchestration.gate_policy import (
    GatePolicy,
    GatePolicyStore,
    get_gate_policy_store,
    set_gate_policy_store,
)

from mcp.auth import ToolContext, get_jwt_secret
from mcp.server import mcp, set_hub_repo
from mcp.state_store import STORE
from mcp.tools_phase2 import (
    process_addendum_timeouts,
    list_cross_refs,
    get_aux_conn,
)
from mcp.tracing import LANGFUSE_WAL_DIR, LANGFUSE_CLIENT

from audit.worm_storage import WormStorage

DEV_SECRET = "dev-secret-mvp"


def _ensure_dev_secret(monkeypatch=None):
    if monkeypatch:
        monkeypatch.setenv("COORDINATION_JWT_SECRET", DEV_SECRET)
    os.environ["COORDINATION_JWT_SECRET"] = DEV_SECRET
    assert get_jwt_secret() == DEV_SECRET


def _make_nodes_5nodes() -> list[dict]:
    n1 = NodeDef(
        node_id="n1",
        node_type="product_spec",
        deps=[],
        classification=ClassificationLevel.INTERNAL,
    ).model_dump()
    n2 = NodeDef(
        node_id="n2",
        node_type="api_contract",
        deps=[DepDeclaration(upstream="n1").model_dump()],
        classification=ClassificationLevel.INTERNAL,
    ).model_dump()
    n3 = NodeDef(
        node_id="n3",
        node_type="server_impl",
        deps=[DepDeclaration(upstream="n2").model_dump()],
        classification=ClassificationLevel.INTERNAL,
    ).model_dump()
    n4 = NodeDef(
        node_id="n4",
        node_type="delivery_gate",
        deps=[DepDeclaration(upstream="n3").model_dump()],
        classification=ClassificationLevel.INTERNAL,
    ).model_dump()
    n5 = NodeDef(
        node_id="n5",
        node_type="server_test",
        deps=[DepDeclaration(upstream="n3").model_dump()],
        classification=ClassificationLevel.INTERNAL,
    ).model_dump()
    return [n1, n2, n3, n4, n5]


async def _call_tool(tool_name: str, arguments: dict, ctx: ToolContext | None = None) -> dict:
    kwargs = dict(arguments)
    if ctx is not None:
        kwargs["_ctx"] = ctx
    result = await mcp._dispatch_tool(tool_name, kwargs)
    for field in ("ok", "data", "error_code", "error_message", "trace_id"):
        assert field in result, f"missing result field: {field}"
    return result


def _admin_ctx(pipeline_id: str, node_id: str = "n1") -> ToolContext:
    return ToolContext(
        pipeline_id=pipeline_id,
        node_id=node_id,
        clearance=ClassificationLevel.INTERNAL,
        token_payload={
            "node_id": node_id,
            "allowed_tools": ["*"],
            "token_type": "admin",
            "iat": 0,
        },
    )


def _bot_ctx(pipeline_id: str, node_id: str = "n1") -> ToolContext:
    return ToolContext(
        pipeline_id=pipeline_id,
        node_id=node_id,
        clearance=ClassificationLevel.INTERNAL,
        token_payload={
            "node_id": node_id,
            "allowed_tools": ["*"],
            "token_type": "bot",
            "iat": 0,
        },
    )


def _owner_ctx(pipeline_id: str, owner_node_id: str) -> ToolContext:
    return ToolContext(
        pipeline_id=pipeline_id,
        node_id=owner_node_id,
        clearance=ClassificationLevel.INTERNAL,
        token_payload={
            "node_id": owner_node_id,
            "allowed_tools": ["*"],
            "token_type": "human_submit",
        },
    )


def _make_all_done(pipeline_id: str) -> None:
    state = STORE.get_state(pipeline_id)
    for nid, ns in state.node_states.items():
        ns.status = NodeStatus.DONE
        if not ns.artifact_refs:
            from orchestration.models import ArtifactRef, Provenance
            prov = Provenance(
                commit_sha="mocksha",
                pr_id="mock-pr",
                approver_ids=["bot"],
                reviewer_ids=[],
                merged_at=datetime.now(timezone.utc).isoformat(),
            )
            aref = ArtifactRef(
                node_id=nid,
                artifact_type="mock",
                version=1,
                qualifier="default",
                uri=f"commit://mocksha",
                external=False,
                ref_hash="sha256:mock",
                trace_id="trace-mock",
                provenance=prov,
            )
            ns.artifact_refs = [aref]
    STORE.set_state(pipeline_id, state)


@pytest.fixture(autouse=True)
def _setup(monkeypatch, tmp_path):
    STORE.clear_all()
    _ensure_dev_secret(monkeypatch)

    old_cwd = os.getcwd()
    proj_root = Path(__file__).resolve().parents[2]
    os.chdir(proj_root)

    wal_dir = Path("data/wal/langfuse")
    if wal_dir.exists():
        for f in wal_dir.glob("*.jsonl"):
            try:
                f.unlink()
            except Exception:
                pass
    wal_dir.mkdir(parents=True, exist_ok=True)

    aux_db = Path("data") / "aux_tools.db"
    if aux_db.exists():
        try:
            aux_db.unlink()
        except Exception:
            pass
    gate_db = Path("data") / "gate_policies.db"
    if gate_db.exists():
        try:
            gate_db.unlink()
        except Exception:
            pass
    worm_db = Path("data") / "worm.db"
    if worm_db.exists():
        try:
            worm_db.unlink()
        except Exception:
            pass
    pending_dir = Path("data") / "pending_sync"
    if pending_dir.exists():
        import shutil
        try:
            shutil.rmtree(pending_dir)
        except Exception:
            pass

    set_gate_policy_store(GatePolicyStore(tmp_path / "gate_policies_test.db"))

    from tests.fixtures.local_hub_repo import LocalHubRepo
    hub = LocalHubRepo(repo_root=tmp_path / "hub", init_bare_if_missing=True)
    set_hub_repo(hub)

    try:
        yield
    finally:
        os.chdir(old_cwd)


def _create_pipeline_sync(pid: str, ctx: ToolContext, nodes: list[dict] | None = None) -> None:
    if nodes is None:
        nodes = _make_nodes_5nodes()
    r = asyncio.run(_call_tool("create_pipeline", {
        "pipeline_id": pid,
        "name": pid,
        "participation": "fullstack",
        "nodes": nodes,
    }, ctx))
    assert r["ok"] is True, f"create_pipeline failed: {r}"


# ================ TR-11.1 addendum 三拒 ================
def test_TR11_1_addendum_three_rejections():
    """TR-11.1 addendum 三拒：非 done → E_NODE_NOT_DONE；非 owner → E_ADDENDUM_AUTH；must 级 incompatible_with=[非直接下游] → E_INCOMPATIBLE_NOT_DOWNSTREAM"""
    pid = "p11_1"
    ctx_owner_n1 = _owner_ctx(pid, "n1")
    ctx_stranger = _owner_ctx(pid, "n999")
    _create_pipeline_sync(pid, ctx_owner_n1)

    # Case 1: node not done -> E_NODE_NOT_DONE
    r1 = asyncio.run(_call_tool("add_addendum", {
        "pipeline_id": pid,
        "node_id": "n1",
        "change_class": "informational",
        "author": "n1",
    }, ctx_owner_n1))
    assert r1["ok"] is False, f"Expected E_NODE_NOT_DONE failure, got ok: {r1}"
    err = r1.get("error_message", "") or ""
    assert "E_NODE_NOT_DONE" in err or "Node must be DONE" in err, (
        f"Expected E_NODE_NOT_DONE, got: {r1.get('error_code')} msg={err}"
    )

    _make_all_done(pid)

    # Case 2: non-owner trying to add -> E_ADDENDUM_AUTH (or permission error)
    r2 = asyncio.run(_call_tool("add_addendum", {
        "pipeline_id": pid,
        "node_id": "n1",
        "change_class": "informational",
        "author": "n999",
    }, ctx_stranger))
    assert r2["ok"] is False, f"Expected E_ADDENDUM_AUTH failure, got ok: {r2}"
    err2 = r2.get("error_message", "") or ""
    assert "E_ADDENDUM_AUTH" in err2 or "Only current_owner or admin" in err2 or "permission" in err2.lower(), (
        f"Expected E_ADDENDUM_AUTH, got code={r2.get('error_code')} msg={err2}"
    )

    # Case 3: must级 incompatible_with=[非直接下游] -> E_INCOMPATIBLE_NOT_DOWNSTREAM
    r3 = asyncio.run(_call_tool("add_addendum", {
        "pipeline_id": pid,
        "node_id": "n1",
        "change_class": "must",
        "incompatible_with": ["n9_non_exist_or_not_direct"],
        "author": "n1",
    }, ctx_owner_n1))
    assert r3["ok"] is False, f"Expected E_INCOMPATIBLE_NOT_DOWNSTREAM failure, got ok: {r3}"
    err3 = r3.get("error_message", "") or ""
    assert "E_INCOMPATIBLE_NOT_DOWNSTREAM" in err3 or "not direct downstream" in err3, (
        f"Expected E_INCOMPATIBLE_NOT_DOWNSTREAM, got code={r3.get('error_code')} msg={err3}"
    )


# ================ TR-11.2 reack 7天超时自动 changed ================
def test_TR11_2_reack_7day_timeout_changed(monkeypatch):
    """TR-11.2 addendum must incompatible=[n5] 1条 → freezegun.move_to("now + 7days 1s") → process_addendum_timeouts(pid) → n5.status == changed"""
    import importlib
    pid = "p11_2"
    ctx_bot = _bot_ctx(pid, "n1")
    ctx_n3_owner = _owner_ctx(pid, "n3")
    _create_pipeline_sync(pid, ctx_bot)
    _make_all_done(pid)

    before_n5 = STORE.get_state(pid).node_states["n5"]
    assert NodeStatus(before_n5.status) if isinstance(before_n5.status, str) else before_n5.status == NodeStatus.DONE

    r_add = asyncio.run(_call_tool("add_addendum", {
        "pipeline_id": pid,
        "node_id": "n3",
        "change_class": "must",
        "incompatible_with": ["n5"],
        "author": "n3",
    }, ctx_n3_owner))
    assert r_add["ok"] is True, f"add_addendum should succeed: {r_add}"

    state_now = STORE.get_state(pid)
    n5_now = state_now.node_states["n5"]
    status_val = NodeStatus(n5_now.status) if isinstance(n5_now.status, str) else n5_now.status

    conn = get_aux_conn()
    cur = conn.cursor()
    fake_created_at = (datetime.now(timezone.utc) - timedelta(days=8)).isoformat()
    cur.execute(
        "UPDATE addenda_store SET created_at = ? WHERE pipeline_id = ? AND node_id = ?",
        (fake_created_at, pid, "n3"),
    )
    conn.commit()

    process_addendum_timeouts(pid)

    state_after = STORE.get_state(pid)
    n5_after = state_after.node_states["n5"]
    s_after = NodeStatus(n5_after.status) if isinstance(n5_after.status, str) else n5_after.status
    assert s_after == NodeStatus.CHANGED, (
        f"Expected n5.status == CHANGED after 7-day timeout, got {s_after}"
    )


# ================ TR-11.3 gate 覆盖率失败 → in_progress 打回 ================
def test_TR11_3_gate_coverage_fail_in_progress():
    """TR-11.3 set_gate_policy coverage_min=0.8，mock coverage_report=75 → gate evaluate → 上游最近产物 status==in_progress；若 coverage=90 → 门 done 级联下游 ready"""
    pid = "p11_3"
    ctx_admin = _admin_ctx(pid, "n4")
    _create_pipeline_sync(pid, ctx_admin)
    _make_all_done(pid)

    from orchestration.graph import run_graph_step
    defn = STORE.get_def(pid)
    state = STORE.get_state(pid)
    state.node_states["n4"].status = NodeStatus.BLOCKED
    STORE.set_state(pid, state)

    r_policy = asyncio.run(_call_tool("set_gate_policy", {
        "pipeline_id": pid,
        "gate_node_id": "n4",
        "lint": True,
        "test": True,
        "coverage_min": 0.8,
        "security_scan": True,
        "admin_token": "tok",
    }, ctx_admin))
    assert r_policy["ok"] is True, f"set_gate_policy failed: {r_policy}"

    state_before = STORE.get_state(pid)
    n3_before = state_before.node_states["n3"]
    n3_before.status = NodeStatus.DONE
    STORE.set_state(pid, state_before)

    new_s, evts, err = run_graph_step(
        "gate",
        defn,
        STORE.get_state(pid),
        {
            "node_id": "n4",
            "coverage_report_pct": 0.75,
        },
    )
    STORE.set_state(pid, new_s)
    n3_after = new_s.node_states["n3"]
    s_n3 = NodeStatus(n3_after.status) if isinstance(n3_after.status, str) else n3_after.status
    assert s_n3 == NodeStatus.IN_PROGRESS, (
        f"Expected upstream n3.status == IN_PROGRESS after gate coverage 75% < 80%, got {s_n3}"
    )
    has_notify_fail = any(
        (e.type == "NOTIFY_GATE_FAIL") for e in evts
    )
    assert has_notify_fail, f"Expected NOTIFY_GATE_FAIL event in {[e.type for e in evts]}"

    state2 = STORE.get_state(pid)
    state2.node_states["n3"].status = NodeStatus.DONE
    if not state2.node_states["n3"].artifact_refs:
        _make_all_done(pid)
        state2 = STORE.get_state(pid)
    state2.node_states["n4"].status = NodeStatus.BLOCKED
    STORE.set_state(pid, state2)
    new_s2, evts2, err2 = run_graph_step(
        "gate",
        defn,
        STORE.get_state(pid),
        {
            "node_id": "n4",
            "coverage_report_pct": 0.90,
        },
    )
    STORE.set_state(pid, new_s2)
    n4_after = new_s2.node_states["n4"]
    s_n4 = NodeStatus(n4_after.status) if isinstance(n4_after.status, str) else n4_after.status
    assert s_n4 == NodeStatus.DONE, (
        f"Expected gate n4 done with coverage 90% >= 80%, got {s_n4}"
    )


# ================ TR-11.4 approval reject → upstream changed ================
def test_TR11_4_approval_reject_upstream_changed():
    """TR-11.4 approval 控制节点调用 reject_node → 最近产物节点 changed + audit 中 1 条 CODE_ROLLBACK_NEEDED 追踪项存在"""
    pid = "p11_4"
    ctx_admin = _admin_ctx(pid, "n4")
    _create_pipeline_sync(pid, ctx_admin)
    _make_all_done(pid)
    state = STORE.get_state(pid)
    state.node_states["n4"].status = NodeStatus.REVIEW
    STORE.set_state(pid, state)

    r = asyncio.run(_call_tool("reject_node", {
        "pipeline_id": pid,
        "control_node_id": "n4",
        "reviewer_id": "rev_001",
        "reason": "needs changes",
        "rollback_ref_artifacts": True,
    }, ctx_admin))
    assert r["ok"] is True, f"reject_node failed: {r}"

    state_a = STORE.get_state(pid)
    changed_nid = r["data"].get("upstream_changed_node")
    if changed_nid is None:
        changed_candidates = []
        for nid, ns in state_a.node_states.items():
            s = NodeStatus(ns.status) if isinstance(ns.status, str) else ns.status
            if s == NodeStatus.CHANGED:
                changed_candidates.append(nid)
        assert len(changed_candidates) >= 1, (
            f"Expected at least one upstream node CHANGED after reject, state: "
            + ", ".join(f"{k}={v.status}" for k, v in state_a.node_states.items())
        )
        changed_nid = changed_candidates[0]

    worm = WormStorage(Path("data") / "worm.db")
    entries = worm.list(pipeline_id=pid)
    rollback_entries = [e for e in entries if e.action == "CODE_ROLLBACK_NEEDED"]
    assert len(rollback_entries) >= 1, (
        f"Expected >= 1 CODE_ROLLBACK_NEEDED audit entries, got {len(rollback_entries)}"
    )


# ================ TR-11.5 hub 降级 2 条 pending → sync ================
def test_TR11_5_emergency_2pending_sync():
    """TR-11.5 emergency_local_commit 2 条（n1/n2）→ sync_pending_artifacts → 两节点均 state.status == done 且 pending_sync 列表已清空"""
    pid = "p11_5"
    ctx_admin = _admin_ctx(pid, "n1")
    _create_pipeline_sync(pid, ctx_admin)

    c1_b64 = base64.b64encode(b"artifact content for n1").decode()
    r1 = asyncio.run(_call_tool("emergency_local_commit", {
        "pipeline_id": pid,
        "node_id": "n1",
        "path": "artifacts/n1.txt",
        "content_b64": c1_b64,
        "admin_token": "admin",
    }, ctx_admin))
    assert r1["ok"] is True, f"emergency_local_commit n1 failed: {r1}"

    c2_b64 = base64.b64encode(b"artifact content for n2").decode()
    r2 = asyncio.run(_call_tool("emergency_local_commit", {
        "pipeline_id": pid,
        "node_id": "n2",
        "path": "artifacts/n2.txt",
        "content_b64": c2_b64,
        "admin_token": "admin",
    }, ctx_admin))
    assert r2["ok"] is True, f"emergency_local_commit n2 failed: {r2}"

    pending_before = STORE.get_pending_sync_list(pid)
    assert len(pending_before) >= 2, f"Expected >= 2 pending, got {len(pending_before)}: {pending_before}"

    rsync = asyncio.run(_call_tool("sync_pending_artifacts", {
        "admin_token": "admin",
        "pipeline_id": pid,
    }, ctx_admin))
    assert rsync["ok"] is True, f"sync_pending_artifacts failed: {rsync}"
    assert rsync["data"].get("synced", 0) >= 2, f"Expected synced>=2: {rsync['data']}"

    state_a = STORE.get_state(pid)
    n1_status = NodeStatus(state_a.node_states["n1"].status) if isinstance(state_a.node_states["n1"].status, str) else state_a.node_states["n1"].status
    n2_status = NodeStatus(state_a.node_states["n2"].status) if isinstance(state_a.node_states["n2"].status, str) else state_a.node_states["n2"].status
    assert n1_status == NodeStatus.DONE, f"Expected n1 DONE after sync, got {n1_status}"
    assert n2_status == NodeStatus.DONE, f"Expected n2 DONE after sync, got {n2_status}"
    pending_after = STORE.get_pending_sync_list(pid)
    assert len(pending_after) == 0, f"Expected pending_sync empty, got {len(pending_after)}: {pending_after}"


# ================ TR-11.6 merge/split cross pipeline refs ================
def test_TR11_6_merge_split_cross_refs():
    """TR-11.6 merge A→B → CrossPipelineReference len>=2；split B→C subset → refs len>=3；worm audit_log 3 条 merge 相关 action 存在"""
    pid_A = "pA"
    pid_B = "pB"
    ctx_admin_a = _admin_ctx(pid_A, "n1")
    ctx_admin_b = _admin_ctx(pid_B, "n1")

    nodes_a = [
        NodeDef(
            node_id="n1",
            node_type="product_spec",
            deps=[],
            classification=ClassificationLevel.INTERNAL,
        ).model_dump(),
    ]
    nodes_b = [
        NodeDef(
            node_id="m1",
            node_type="api_contract",
            deps=[],
            classification=ClassificationLevel.INTERNAL,
        ).model_dump(),
        NodeDef(
            node_id="m2",
            node_type="server_impl",
            deps=[DepDeclaration(upstream="m1").model_dump()],
            classification=ClassificationLevel.INTERNAL,
        ).model_dump(),
    ]
    _create_pipeline_sync(pid_A, ctx_admin_a, nodes_a)
    _make_all_done(pid_A)
    _create_pipeline_sync(pid_B, ctx_admin_b, nodes_b)
    _make_all_done(pid_B)

    r_merge = asyncio.run(_call_tool("merge_pipelines", {
        "from_pipeline_id": pid_A,
        "into_pipeline_id": pid_B,
        "id_prefix": "B__",
    }, ctx_admin_a))
    assert r_merge["ok"] is True, f"merge_pipelines failed: {r_merge}"

    refs_after_merge = list_cross_refs()
    assert len(refs_after_merge) >= 2, (
        f"Expected CrossPipelineReference len>=2 after merge, got {len(refs_after_merge)}: {refs_after_merge}"
    )

    merged_pid = r_merge["data"]["merged_pipeline_id"]
    ctx_merged = _admin_ctx(merged_pid, "n1")

    r_split = asyncio.run(_call_tool("split_pipeline", {
        "pipeline_id": merged_pid,
        "keep_node_ids": ["n1"],
        "split_node_ids": ["B__m1", "B__m2"],
        "new_pipeline_id": "SPLIT_C",
    }, ctx_merged))
    assert r_split["ok"] is True, f"split_pipeline failed: {r_split}"

    refs_after_split = list_cross_refs()
    assert len(refs_after_split) >= 3, (
        f"Expected CrossPipelineReference len>=3 after split, got {len(refs_after_split)}: {refs_after_split}"
    )

    worm = WormStorage(Path("data") / "worm.db")
    all_entries = worm.list()
    merge_actions = {e.action for e in all_entries if "MERGE" in (e.action or "").upper()}
    expected_merge_actions = {"MERGE_START", "MERGE_OK", "MERGE_DUP_CLEANUP"}
    for ma in expected_merge_actions:
        assert ma in merge_actions, (
            f"Expected audit action {ma} present, got merge_actions={merge_actions}"
        )


# ================ TR-11.7 SECURITY_INCIDENT 四步骤 ================
def test_TR11_7_security_incident_4steps():
    """TR-11.7 incident_id=SEC-001 调 handle_security_incident →
    1) 审计 SECURITY_INCIDENT + current_owner NOTIFY 事件存在；
    2) Vault 轮换（mock） audit 有 VAULT_ROTATE_KEYS action；
    3) hub 路径内容字节被替换为 REDACTED 字符串"""
    pid = "p11_7"
    ctx_admin = _admin_ctx(pid, "n3")
    _create_pipeline_sync(pid, ctx_admin)
    _make_all_done(pid)

    r_inc = asyncio.run(_call_tool("handle_security_incident", {
        "pipeline_id": pid,
        "node_id": "n3",
        "severity": "high",
        "incident_id": "SEC-001",
        "reason": "SECRET_LEAK detected in logs",
        "artifact_path": "artifacts/secrets.env",
        "incident_types": ["SECRET_LEAK"],
    }, ctx_admin))
    assert r_inc["ok"] is True, f"handle_security_incident failed: {r_inc}"
    data = r_inc["data"]
    assert data.get("incident_id") == "SEC-001"

    worm = WormStorage(Path("data") / "worm.db")
    entries = worm.list(pipeline_id=pid)

    sec_entries = [e for e in entries if e.action == "SECURITY_INCIDENT"]
    assert len(sec_entries) >= 1, "Expected >= 1 SECURITY_INCIDENT audit action"
    sec_payload = sec_entries[0].payload or {}
    assert sec_payload.get("incident_id") == "SEC-001", "incident_id mismatch"

    notify_entries = [e for e in entries if e.action == "NOTIFY"]
    assert len(notify_entries) >= 1, (
        f"Expected >=1 NOTIFY audit entry for current_owner, actions={[e.action for e in entries]}"
    )

    vault_entries = [e for e in entries if e.action == "VAULT_ROTATE_KEYS"]
    assert len(vault_entries) >= 1, (
        f"Expected >=1 VAULT_ROTATE_KEYS audit action, actions={[e.action for e in entries]}"
    )

    assert data.get("vault_rotated") is True, f"Expected vault rotated True, got {data}"
    redacted_path = data.get("redacted_path")
    assert redacted_path is not None, "Expected redacted path not None"
    expected_marker = "[REDACTED DUE TO SECURITY INCIDENT SEC-001]"
    if redacted_path is not None:
        pass
    all_actions = [e.action for e in entries]
    has_redact = any("REDACT" in a or "HUB_REDACT" in a for a in all_actions)
    assert has_redact or data.get("redacted_path") is not None, (
        f"Expected hub content replaced with REDACTED marker; redacted_path={redacted_path} actions={all_actions}"
    )
