from __future__ import annotations

from pathlib import Path
import sys
import warnings
from typing import Any

warnings.filterwarnings("ignore")
from crewai import Agent, Crew, Process, Task

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from orchestration.deps import resolve_effective_deps
from orchestration.models import (
    ClassificationLevel,
    NodeDef,
    PipelineDefinition,
    PipelineState,
    RoleInstance,
)

from crew.agents import (
    ClientUIAgent,
    DesignAgent,
    MCPClientWrapper,
    OpsCoordinatorAgent,
    ProductAgent,
    ROLE_TO_AGENT_CLS,
    ROLE_TO_CREW_ROLE,
    ServerImplAgent,
    build_client_ui_agent,
)
from crew.role_instances import get_instance_metadata

from tests.fixtures.llm_mock import LLMMock


NODE_TYPE_TO_ROLE: dict[str, str] = {
    "product_spec": "product",
    "api_contract": "product",
    "design_asset": "design",
    "client_ui_impl": "client_ui",
    "client_test": "client_ui",
    "server_impl": "server_impl",
    "server_test": "server_impl",
    "delivery_gate": "ops",
}

DESIGN_UPSTREAM_TYPES = {"design_asset"}


def _node_type_role(node_type: str) -> str:
    return NODE_TYPE_TO_ROLE.get(node_type, node_type)


def _get_node_def(pipeline_def: PipelineDefinition, node_id: str) -> NodeDef | None:
    for n in pipeline_def.nodes:
        if n.node_id == node_id:
            return n
    return None


def _deps_has_design_asset(
    node_id: str,
    pipeline_def: PipelineDefinition,
    pipeline_state: PipelineState,
) -> bool:
    deps = resolve_effective_deps(node_id, pipeline_def, pipeline_state)
    node_map = {n.node_id: n for n in pipeline_def.nodes}
    for up_id, _ in deps:
        up_node = node_map.get(up_id)
        if up_node is not None and up_node.node_type in DESIGN_UPSTREAM_TYPES:
            return True
    return False


def _build_deps_info(
    node_id: str,
    pipeline_def: PipelineDefinition,
    pipeline_state: PipelineState,
) -> list[tuple[str, str, dict, ClassificationLevel, str]]:
    result: list[tuple[str, str, dict, ClassificationLevel, str]] = []
    deps = resolve_effective_deps(node_id, pipeline_def, pipeline_state)
    node_map = {n.node_id: n for n in pipeline_def.nodes}
    for up_id, dep_decl in deps:
        up_node = node_map.get(up_id)
        up_ns = pipeline_state.node_states.get(up_id) if pipeline_state else None
        classification = ClassificationLevel.INTERNAL
        if up_node is not None:
            try:
                classification = (
                    ClassificationLevel(up_node.classification)
                    if isinstance(up_node.classification, int)
                    else up_node.classification
                )
            except Exception:
                classification = ClassificationLevel.INTERNAL
        stability = "stable"
        if up_ns is not None and up_ns.change_state and up_ns.change_state != "unchanged":
            stability = "volatile"
        content_stub = f"upstream-content-stub-{up_id}"
        key_constraints: dict = {
            "strictness": getattr(dep_decl, "strictness", "strict"),
            "coupling": getattr(dep_decl, "coupling", "hard"),
            "presence": getattr(dep_decl, "presence", "required"),
        }
        result.append((up_id, content_stub, key_constraints, classification, stability))
    return result


def build_crew_for_ready_nodes(
    ready_nodes: list[tuple[str, str]],
    pipeline_def: PipelineDefinition,
    pipeline_state: PipelineState,
    instances: dict[str, RoleInstance],
    mcp_tools_wrapper: Any,
    default_llm: Any | None = None,
) -> Crew:
    profile = pipeline_def.profile
    roles_present = set(profile.roles_present)

    agent_tools = []
    if mcp_tools_wrapper is not None:
        if isinstance(mcp_tools_wrapper, MCPClientWrapper):
            try:
                agent_tools = mcp_tools_wrapper.as_tools()
            except Exception:
                try:
                    agent_tools = mcp_tools_wrapper.as_simple_tools()
                except Exception:
                    agent_tools = []
        else:
            agent_tools = list(mcp_tools_wrapper) if mcp_tools_wrapper else []

    llm = default_llm if default_llm is not None else LLMMock()

    agents: list[Agent] = []
    seen_instance_ids: set[str] = set()

    tasks: list[Task] = []

    for nid, instance_id in ready_nodes:
        if instance_id not in instances:
            continue
        instance = instances[instance_id]
        role = instance.role
        if role not in roles_present:
            continue

        node_def = _get_node_def(pipeline_def, nid)
        node_type = node_def.node_type if node_def is not None else "unknown"

        if instance_id not in seen_instance_ids:
            agent_cls = ROLE_TO_AGENT_CLS.get(role, ServerImplAgent)
            agent_kwargs: dict[str, Any] = {
                "llm": llm,
                "tools": list(agent_tools),
                "instance_id": instance_id,
            }
            if agent_cls is ClientUIAgent:
                deps_has_design = _deps_has_design_asset(nid, pipeline_def, pipeline_state)
                agent = build_client_ui_agent(deps_has_design=deps_has_design, **agent_kwargs)
            else:
                agent = agent_cls(**agent_kwargs)
            agents.append(agent)
            seen_instance_ids.add(instance_id)

        agent = next(a for a in agents if getattr(a, "instance_id", "") == instance_id)

        deps_info = _build_deps_info(nid, pipeline_def, pipeline_state)
        deps_str_parts = []
        for up_id, content_stub, kc, cls, stab in deps_info:
            deps_str_parts.append(
                f"dep[{up_id}]: content={content_stub},"
                f" constraints={kc}, classification={cls}, stability={stab}"
            )
        deps_str = "; ".join(deps_str_parts) if deps_str_parts else "(no deps)"

        context_info = (
            f"NODE_ID={nid}; INSTANCE_ID={instance_id}; NODE_TYPE={node_type}; "
            f"DEPS_INFO=[{deps_str}]"
        )

        description = (
            f"完成节点 {nid}（{node_type}）产物提交。"
            f" Context: {context_info}"
        )
        expected_output = "通过 MCP submit_artifact + approve_pr 将产物交付并使节点 DONE。"

        task = Task(
            description=description,
            expected_output=expected_output,
            agent=agent,
        )
        object.__setattr__(task, "node_id", nid)
        object.__setattr__(task, "instance_id", instance_id)
        object.__setattr__(task, "context_info", context_info)
        object.__setattr__(task, "deps_info", deps_info)
        tasks.append(task)

    crew = Crew(
        agents=agents,
        tasks=tasks,
        process=Process.sequential,
        verbose=0,
    )
    return crew
