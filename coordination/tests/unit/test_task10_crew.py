"""Task 10 CrewAI 角色协调验收测试 (TR-10.1 ~ TR-10.5)."""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.constants import PARTICIPATION_PROFILES
from orchestration.models import (
    ClassificationLevel,
    DepDeclaration,
    DepCoupling,
    DepPresence,
    DepStrictness,
    NodeDef,
    NodeState,
    NodeStatus,
    PipelineDefinition,
    PipelineState,
    PipelineStatus,
    RoleInstance,
)

from crew.agents import (
    ClientUIAgent,
    DesignAgent,
    MCPClientWrapper,
    OpsCoordinatorAgent,
    ProductAgent,
    ROLE_TO_CREW_ROLE,
    ServerImplAgent,
    build_client_ui_agent,
)
from crew.behavior_guards import (
    ALR13_SPAN_TYPE,
    ALR14_SPAN_TYPE,
    ALR15_SPAN_TYPE,
    BehaviorGuard,
    ScopeMismatchError,
)
from crew.builder import build_crew_for_ready_nodes
from crew.cost_control import CostController
from crew.role_instances import (
    DEFAULT_ROLE_INSTANCES_YAML,
    get_default_role_instances,
    load_role_instances,
)

from tests.fixtures.llm_mock import LLMMock


WAL_DIR = PROJECT_ROOT / "data" / "wal" / "langfuse"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _make_pipeline(profile_id: str, node_defs: list[NodeDef]) -> PipelineDefinition:
    profile = PARTICIPATION_PROFILES[profile_id]
    return PipelineDefinition(
        id=f"pipe-{profile_id}-test",
        name=f"test {profile_id}",
        nodes=node_defs,
        profile=profile,
        classification=ClassificationLevel.INTERNAL,
    )


def _make_state(pipeline_def: PipelineDefinition, statuses: dict[str, NodeStatus] | None = None) -> PipelineState:
    statuses = statuses or {}
    node_states: dict[str, NodeState] = {}
    for n in pipeline_def.nodes:
        st = statuses.get(n.node_id, NodeStatus.READY)
        node_states[n.node_id] = NodeState(node_id=n.node_id, status=st)
    return PipelineState(
        pipeline_id=pipeline_def.id,
        version=1,
        status=PipelineStatus.ACTIVE,
        created_at=_now_iso(),
        updated_at=_now_iso(),
        node_states=node_states,
        profile_id=pipeline_def.profile.id,
    )


def _make_fullstack_nodes() -> list[NodeDef]:
    return [
        NodeDef(
            node_id="n1",
            node_type="product_spec",
            role_assignments=["team_product"],
            deps=[],
        ),
        NodeDef(
            node_id="n2",
            node_type="api_contract",
            role_assignments=["team_product", "team_a_server"],
            deps=[DepDeclaration(upstream="n1", presence=DepPresence.REQUIRED)],
        ),
        NodeDef(
            node_id="n3",
            node_type="design_asset",
            role_assignments=["team_design"],
            deps=[DepDeclaration(upstream="n1", presence=DepPresence.REQUIRED)],
        ),
        NodeDef(
            node_id="n4",
            node_type="client_ui_impl",
            role_assignments=["team_client_ui"],
            deps=[
                DepDeclaration(upstream="n2", presence=DepPresence.REQUIRED),
                DepDeclaration(upstream="n3", presence=DepPresence.IF_PRESENT),
            ],
        ),
        NodeDef(
            node_id="n5",
            node_type="server_impl",
            role_assignments=["team_a_server"],
            deps=[DepDeclaration(upstream="n2", presence=DepPresence.REQUIRED)],
        ),
        NodeDef(
            node_id="n6",
            node_type="server_test",
            role_assignments=["team_a_server"],
            deps=[DepDeclaration(upstream="n5", presence=DepPresence.REQUIRED)],
        ),
        NodeDef(
            node_id="n7",
            node_type="delivery_gate",
            role_assignments=["team_ops"],
            deps=[
                DepDeclaration(upstream="n4", presence=DepPresence.IF_PRESENT),
                DepDeclaration(upstream="n6", presence=DepPresence.REQUIRED),
            ],
        ),
    ]


def _make_instances_for_tests() -> dict[str, RoleInstance]:
    return {
        "team_product": RoleInstance(
            instance_id="team_product",
            role="product",
            approvers=["human-pm"],
            clearance=ClassificationLevel.INTERNAL,
        ),
        "team_design": RoleInstance(
            instance_id="team_design",
            role="design",
            approvers=["human-des"],
            clearance=ClassificationLevel.INTERNAL,
        ),
        "team_client_ui": RoleInstance(
            instance_id="team_client_ui",
            role="client_ui",
            approvers=["human-fe"],
            clearance=ClassificationLevel.INTERNAL,
        ),
        "team_a_server": RoleInstance(
            instance_id="team_a_server",
            role="server_impl",
            approvers=["bot-coord", "human-lead"],
            clearance=ClassificationLevel.INTERNAL,
        ),
        "team_b_server": RoleInstance(
            instance_id="team_b_server",
            role="server_impl",
            approvers=["bot-coord", "human-lead-b"],
            clearance=ClassificationLevel.INTERNAL,
        ),
        "team_ops": RoleInstance(
            instance_id="team_ops",
            role="ops",
            approvers=["human-ops"],
            clearance=ClassificationLevel.INTERNAL,
        ),
    }


class _DummyMCPServer:
    def __init__(self) -> None:
        self.last_tool: tuple[str, dict] | None = None

    async def _dispatch_tool(self, name: str, arguments: dict) -> dict:
        self.last_tool = (name, arguments)
        return {"ok": True, "data": {"tool": name, "args": arguments}}


def _make_wrapper() -> MCPClientWrapper | list:
    return []


# ---------- TR-10.1 Crew 角色集合 ----------

def test_tr10_1_crew_roles_fullstack():
    """TR-10.1 场景1：fullstack profile product/design/server → 3 角色."""
    nodes = _make_fullstack_nodes()
    pipeline_def = _make_pipeline("fullstack", nodes)
    pipeline_state = _make_state(pipeline_def)
    instances = _make_instances_for_tests()
    wrapper = _make_wrapper()
    ready_nodes = [
        ("n1", "team_product"),
        ("n2", "team_a_server"),
        ("n7", "team_ops"),
    ]
    crew = build_crew_for_ready_nodes(
        ready_nodes=ready_nodes,
        pipeline_def=pipeline_def,
        pipeline_state=pipeline_state,
        instances=instances,
        mcp_tools_wrapper=wrapper,
    )
    roles = {a.role for a in crew.agents}
    expected = {
        ROLE_TO_CREW_ROLE["product"],
        ROLE_TO_CREW_ROLE["server_impl"],
        ROLE_TO_CREW_ROLE["ops"],
    }
    assert roles == expected, f"fullstack roles mismatch: {roles} vs {expected}"


def test_tr10_1_crew_roles_server_only():
    """TR-10.1 场景2：server_only profile → 无 UX Designer / Client UI Implementer."""
    nodes = [
        NodeDef(node_id="n1", node_type="product_spec", role_assignments=["team_product"], deps=[]),
        NodeDef(
            node_id="n2",
            node_type="api_contract",
            role_assignments=["team_product"],
            deps=[DepDeclaration(upstream="n1")],
        ),
        NodeDef(
            node_id="n5",
            node_type="server_impl",
            role_assignments=["team_a_server"],
            deps=[DepDeclaration(upstream="n2")],
        ),
    ]
    pipeline_def = _make_pipeline("server_only", nodes)
    pipeline_state = _make_state(pipeline_def)
    instances = _make_instances_for_tests()
    ready_nodes = [("n1", "team_product"), ("n5", "team_a_server")]
    crew = build_crew_for_ready_nodes(
        ready_nodes=ready_nodes,
        pipeline_def=pipeline_def,
        pipeline_state=pipeline_state,
        instances=instances,
        mcp_tools_wrapper=_make_wrapper(),
    )
    roles = {a.role for a in crew.agents}
    assert "UX Designer" not in roles
    assert "Client UI Implementer" not in roles
    assert ROLE_TO_CREW_ROLE["product"] in roles
    assert ROLE_TO_CREW_ROLE["server_impl"] in roles


def test_tr10_1_crew_roles_no_design_client():
    """TR-10.1 场景3：no_design_client profile → 不包含 UX Designer."""
    nodes = [
        NodeDef(node_id="n1", node_type="product_spec", role_assignments=["team_product"], deps=[]),
        NodeDef(
            node_id="n2",
            node_type="api_contract",
            role_assignments=["team_product"],
            deps=[DepDeclaration(upstream="n1")],
        ),
        NodeDef(
            node_id="n5",
            node_type="server_impl",
            role_assignments=["team_a_server"],
            deps=[DepDeclaration(upstream="n2")],
        ),
    ]
    pipeline_def = _make_pipeline("no_design_client", nodes)
    pipeline_state = _make_state(pipeline_def)
    instances = _make_instances_for_tests()
    ready_nodes = [("n1", "team_product"), ("n5", "team_a_server")]
    crew = build_crew_for_ready_nodes(
        ready_nodes=ready_nodes,
        pipeline_def=pipeline_def,
        pipeline_state=pipeline_state,
        instances=instances,
        mcp_tools_wrapper=_make_wrapper(),
    )
    roles = {a.role for a in crew.agents}
    assert "UX Designer" not in roles
    assert ROLE_TO_CREW_ROLE["product"] in roles
    assert ROLE_TO_CREW_ROLE["server_impl"] in roles


# ---------- TR-10.2 RoleInstance team_a vs team_b ----------

def test_tr10_2_role_instance_mapping():
    """TR-10.2 team_a_server=n5 / team_b_server=n8 → Task.agent.instance_id 精确匹配."""
    nodes = [
        NodeDef(node_id="n1", node_type="product_spec", role_assignments=["team_product"], deps=[]),
        NodeDef(
            node_id="n2",
            node_type="api_contract",
            role_assignments=["team_product"],
            deps=[DepDeclaration(upstream="n1")],
        ),
        NodeDef(
            node_id="n5",
            node_type="server_impl",
            role_assignments=["team_a_server"],
            deps=[DepDeclaration(upstream="n2")],
        ),
        NodeDef(
            node_id="n8",
            node_type="server_test",
            role_assignments=["team_b_server"],
            deps=[DepDeclaration(upstream="n5")],
        ),
    ]
    pipeline_def = _make_pipeline("server_only", nodes)
    pipeline_state = _make_state(pipeline_def)
    instances = _make_instances_for_tests()
    ready_nodes = [("n5", "team_a_server"), ("n8", "team_b_server")]
    crew = build_crew_for_ready_nodes(
        ready_nodes=ready_nodes,
        pipeline_def=pipeline_def,
        pipeline_state=pipeline_state,
        instances=instances,
        mcp_tools_wrapper=_make_wrapper(),
    )

    node_to_instance_expected = {"n5": "team_a_server", "n8": "team_b_server"}
    node_to_agent_instance: dict[str, str] = {}
    for task in crew.tasks:
        nid = getattr(task, "node_id", None)
        agent = task.agent
        inst_id = getattr(agent, "instance_id", None) if agent is not None else None
        if nid:
            node_to_agent_instance[nid] = inst_id

    for nid, expected_inst in node_to_instance_expected.items():
        assert node_to_agent_instance.get(nid) == expected_inst, (
            f"node {nid} instance mismatch: {node_to_agent_instance.get(nid)} vs {expected_inst}"
        )


# ---------- TR-10.3 成本计数阈值 ----------

def test_tr10_3_cost_thresholds():
    """TR-10.3 成本阈值三级检查 (stateless policy evaluator)."""
    cc = CostController()

    # Task 级: 直接传入累计 token，>= 20000 → needs_human=True
    r_task = cc.evaluate_task_tokens(10_000)
    assert r_task["needs_human"] is False
    r_task2 = cc.evaluate_task_tokens(20_001)
    assert r_task2["needs_human"] is True, f"task threshold expected needs_human: {r_task2}"

    # Pipeline 级: accum_usd=101 → action=pause_pipeline
    r_pipe = cc.evaluate_pipeline_usd(99.0)
    assert r_pipe["action"] is None
    r_pipe2 = cc.evaluate_pipeline_usd(101.0)
    assert r_pipe2["action"] == "pause_pipeline", f"pipe threshold expected pause: {r_pipe2}"

    # Platform 级: $4001 → action=switch_cheap_model
    r_plat = cc.evaluate_platform_usd_daily(3999.0)
    assert r_plat["action"] is None
    r_plat2 = cc.evaluate_platform_usd_daily(4001.0)
    assert r_plat2["action"] == "switch_cheap_model", f"platform threshold expected switch: {r_plat2}"


def test_tr10_3b_cost_controller_is_stateless():
    """CostController must not keep internal running totals (ledger owns those)."""
    cc = CostController()
    # Repeated evaluation with the same input yields identical results; there is no
    # hidden accumulation across calls.
    a = cc.evaluate_task_tokens(5000)
    b = cc.evaluate_task_tokens(5000)
    assert a == b
    assert a["accum_tokens"] == 5000
    assert a["needs_human"] is False

    # Two independent calls with different inputs do not leak state into each other.
    assert cc.evaluate_task_tokens(50_000)["needs_human"] is True
    assert cc.evaluate_task_tokens(1)["needs_human"] is False

    # Where there is no ledger wired, stats are reported empty rather than erroring.
    assert cc.get_task_cost_stats("any-task") == {"mean": 0.0, "std": 0.0, "count": 0}


# ---------- TR-10.4 越权阻断 ----------

def test_tr10_4_scope_mismatch_raises_and_writes_wal(tmp_path, monkeypatch):
    """TR-10.4 check_scope 抛 E_TOKEN_SCOPE_MISMATCH 且 WAL 写入 ALR-14 span."""
    test_wal_dir = tmp_path / "wal" / "langfuse"
    test_wal_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr("mcp.tracing.LANGFUSE_WAL_DIR", test_wal_dir)

    import mcp.tracing as tracing_mod

    monkeypatch.setattr(tracing_mod, "LANGFUSE_WAL_DIR", test_wal_dir)

    bg = BehaviorGuard()
    allowed = ["get_status"]
    trace_id = "trace-10-4-scope"

    with pytest.raises((ScopeMismatchError, Exception)) as exc_info:
        bg.check_scope(allowed, "submit_artifact", trace_id)

    err_msg = str(exc_info.value)
    assert "E_TOKEN_SCOPE_MISMATCH" in err_msg, f"error message missing code: {err_msg}"

    wal_files = list(test_wal_dir.glob("*.jsonl"))
    assert len(wal_files) > 0, f"WAL not written; dir={list(test_wal_dir.iterdir())}"

    span_found = False
    for fp in wal_files:
        for line in open(fp, "r", encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue
            if rec.get("span_type") == ALR14_SPAN_TYPE:
                span_found = True
                break
        if span_found:
            break

    spans_alr14 = [s for s in bg._alr_spans if s.get("span_type") == ALR14_SPAN_TYPE]
    assert spans_alr14 or span_found, (
        f"ALR-14 span not recorded; in-memory spans={bg._alr_spans}"
    )


# ---------- TR-10.5 backstory 正则检查 ----------

def test_tr10_5_backstory_regex():
    """TR-10.5 5 Agent backstory 正则：每个必含「提交协调员不执行开发」."""
    llm = LLMMock()
    pattern = re.compile(r"提交协调员不执行开发")

    agents = [
        ProductAgent(llm=llm),
        DesignAgent(llm=llm),
        ClientUIAgent(llm=llm),
        build_client_ui_agent(deps_has_design=True, llm=llm),
        ServerImplAgent(llm=llm),
        OpsCoordinatorAgent(llm=llm),
    ]
    for a in agents:
        assert pattern.search(a.backstory), (
            f"Agent {a.__class__.__name__} (role={a.role}) backstory 缺少「提交协调员不执行开发」：\n{a.backstory}"
        )
