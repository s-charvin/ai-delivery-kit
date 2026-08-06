from __future__ import annotations

from typing import Any

import warnings

with warnings.catch_warnings():
    warnings.filterwarnings("ignore")
    from crewai import Agent


ROLE_TO_CREW_ROLE: dict[str, str] = {
    "product": "Product Manager",
    "design": "UX Designer",
    "client_ui": "Client UI Implementer",
    "server_impl": "Backend Engineer",
    "ops": "Ops Delivery Coordinator",
    "server_test": "Backend Engineer",
    "client_test": "Client UI Implementer",
}

ROLE_TO_GOAL: dict[str, str] = {
    "product": "分析业务需求并产出清晰可执行的产品规格说明文档，协调上下游理解一致。",
    "design": "基于产品规格产出高质量的 UI/UX 设计稿和设计系统资产交付，保证视觉一致性。",
    "client_ui": "按设计稿和 API 契约实现客户端 UI 组件与交互逻辑，通过测试后交付产物。",
    "server_impl": "按 API 契约实现后端服务逻辑、数据模型和接口，编写单元测试保证稳定。",
    "ops": "审核所有交付产物，协调 review 和 approve 流程，执行部署与交付确认。",
    "server_test": "为后端实现编写测试用例，保证接口正确性、稳定性和性能指标达标。",
    "client_test": "为客户端 UI 实现编写测试用例，保证组件交互正确和渲染稳定。",
}

BASE_BACKSTORY_TEMPLATES: dict[str, str] = {
    "product": (
        "资深产品经理，10+ 年经验，擅长将模糊需求拆解为结构化规格。"
        "负责与客户沟通、定义验收标准、协调各角色进度。"
        "提交协调员不执行开发，仅产出规格与推进。"
    ),
    "design": (
        "资深 UX/UI 设计师，精通设计系统与 Figma 高保真稿。"
        "关注用户体验、可访问性、视觉一致性，与产品和前端紧密协作。"
        "提交协调员不执行开发，仅交付设计资产。"
    ),
    "client_ui": (
        "资深前端工程师，精通 React/Vue、组件化开发与视觉还原。"
        "严格遵守设计稿和 API 契约，重视可维护性与性能。"
        "提交协调员不执行开发，仅实现客户端 UI。"
    ),
    "server_impl": (
        "资深后端工程师，精通 API 设计、领域建模与数据库优化。"
        "重视代码质量、可测试性和运行稳定性。"
        "提交协调员不执行开发，仅实现服务端逻辑。"
    ),
    "ops": (
        "交付协调员与运维专家，负责 review 质量把关、PR 批准与部署执行。"
        "掌握全链路交付流程，确保每一步产物完整合规。"
        "提交协调员不执行开发，仅审查与交付。"
    ),
    "server_test": (
        "后端测试工程师，擅长接口测试、集成测试与性能测试。"
        "保证服务端质量稳定，与后端开发密切协作。"
        "提交协调员不执行开发，仅编写与执行测试。"
    ),
    "client_test": (
        "前端测试工程师，擅长 E2E、组件单测与视觉回归测试。"
        "保证客户端交互与渲染稳定，与前端开发协作。"
        "提交协调员不执行开发，仅编写与执行测试。"
    ),
}

CLIENTUI_DESIGN_CONSTRAINT_APPEND = (
    "必须遵守设计约束，不得擅自更改 Figma 视觉。"
)


class MCPClientWrapper:
    def __init__(self, mcp_server: Any, tool_names: list[str] | None = None) -> None:
        self._server = mcp_server
        self._tool_names = tool_names or [
            "submit_artifact",
            "approve_pr",
            "get_status",
            "list_tools",
            "materialize_node",
        ]
        self.last_calls: list[tuple[str, dict]] = []

    def _make_tool(self, name: str) -> Any:
        wrapper = self

        def _tool_fn(**kwargs: Any) -> dict:
            wrapper.last_calls.append((name, kwargs))
            import asyncio

            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    from threading import Thread
                    import queue
                    q: queue.Queue = queue.Queue()

                    def _run():
                        try:
                            r = asyncio.run(wrapper._server._dispatch_tool(name, kwargs))
                            q.put(r)
                        except Exception as e:
                            q.put({"ok": False, "error_message": str(e)})

                    t = Thread(target=_run, daemon=True)
                    t.start()
                    t.join(timeout=5)
                    if q.empty():
                        return {"ok": False, "error_message": "dispatch timeout"}
                    return q.get()
                else:
                    return loop.run_until_complete(wrapper._server._dispatch_tool(name, kwargs))
            except RuntimeError:
                return asyncio.run(wrapper._server._dispatch_tool(name, kwargs))

        _tool_fn.__name__ = f"mcp_{name}"
        _tool_fn.__doc__ = f"MCP tool: {name}"
        return _tool_fn

    def as_tools(self) -> list[Any]:
        from crewai.tools import tool as crewai_tool

        tools = []
        for tn in self._tool_names:
            fn = self._make_tool(tn)

            @crewai_tool(tn)
            def _wrapped(*, _name: str = tn, **kwargs: Any) -> dict:
                return self._make_tool(_name)(**kwargs)

            _wrapped.name = tn
            _wrapped.description = f"MCP dispatch tool: {tn}"
            tools.append(_wrapped)
        return tools

    def as_simple_tools(self) -> list[Any]:
        tools = []
        for tn in self._tool_names:
            fn = self._make_tool(tn)
            fn.name = tn
            fn.description = f"MCP dispatch tool: {tn}"
            tools.append(fn)
        return tools


class ProductAgent(Agent):
    def __init__(self, llm: Any | None = None, tools: list[Any] | None = None, **kwargs: Any) -> None:
        role_key = "product"
        role = ROLE_TO_CREW_ROLE[role_key]
        goal = ROLE_TO_GOAL[role_key]
        backstory = BASE_BACKSTORY_TEMPLATES[role_key]
        super().__init__(
            role=role,
            goal=goal,
            backstory=backstory,
            tools=tools or [],
            allow_delegation=False,
            verbose=False,
            llm=llm,
            **kwargs,
        )
        object.__setattr__(self, "instance_id", kwargs.get("instance_id", ""))


class DesignAgent(Agent):
    def __init__(self, llm: Any | None = None, tools: list[Any] | None = None, **kwargs: Any) -> None:
        role_key = "design"
        role = ROLE_TO_CREW_ROLE[role_key]
        goal = ROLE_TO_GOAL[role_key]
        backstory = BASE_BACKSTORY_TEMPLATES[role_key]
        super().__init__(
            role=role,
            goal=goal,
            backstory=backstory,
            tools=tools or [],
            allow_delegation=False,
            verbose=False,
            llm=llm,
            **kwargs,
        )
        object.__setattr__(self, "instance_id", kwargs.get("instance_id", ""))


class ClientUIAgent(Agent):
    def __init__(self, llm: Any | None = None, tools: list[Any] | None = None, deps_has_design: bool = False, **kwargs: Any) -> None:
        role_key = "client_ui"
        role = ROLE_TO_CREW_ROLE[role_key]
        goal = ROLE_TO_GOAL[role_key]
        backstory = BASE_BACKSTORY_TEMPLATES[role_key]
        if deps_has_design:
            backstory = backstory + CLIENTUI_DESIGN_CONSTRAINT_APPEND
        super().__init__(
            role=role,
            goal=goal,
            backstory=backstory,
            tools=tools or [],
            allow_delegation=False,
            verbose=False,
            llm=llm,
            **kwargs,
        )
        object.__setattr__(self, "instance_id", kwargs.get("instance_id", ""))
        object.__setattr__(self, "deps_has_design", deps_has_design)


def build_client_ui_agent(
    deps_has_design: bool,
    llm: Any | None = None,
    tools: list[Any] | None = None,
    **kwargs: Any,
) -> ClientUIAgent:
    return ClientUIAgent(llm=llm, tools=tools, deps_has_design=deps_has_design, **kwargs)


class ServerImplAgent(Agent):
    def __init__(self, llm: Any | None = None, tools: list[Any] | None = None, **kwargs: Any) -> None:
        role_key = "server_impl"
        role = ROLE_TO_CREW_ROLE[role_key]
        goal = ROLE_TO_GOAL[role_key]
        backstory = BASE_BACKSTORY_TEMPLATES[role_key]
        super().__init__(
            role=role,
            goal=goal,
            backstory=backstory,
            tools=tools or [],
            allow_delegation=False,
            verbose=False,
            llm=llm,
            **kwargs,
        )
        object.__setattr__(self, "instance_id", kwargs.get("instance_id", ""))


class OpsCoordinatorAgent(Agent):
    def __init__(self, llm: Any | None = None, tools: list[Any] | None = None, **kwargs: Any) -> None:
        role_key = "ops"
        role = ROLE_TO_CREW_ROLE[role_key]
        goal = ROLE_TO_GOAL[role_key]
        backstory = BASE_BACKSTORY_TEMPLATES[role_key]
        super().__init__(
            role=role,
            goal=goal,
            backstory=backstory,
            tools=tools or [],
            allow_delegation=False,
            verbose=False,
            llm=llm,
            **kwargs,
        )
        object.__setattr__(self, "instance_id", kwargs.get("instance_id", ""))


ROLE_TO_AGENT_CLS: dict[str, type[Agent]] = {
    "product": ProductAgent,
    "design": DesignAgent,
    "client_ui": ClientUIAgent,
    "server_impl": ServerImplAgent,
    "ops": OpsCoordinatorAgent,
    "server_test": ServerImplAgent,
    "client_test": ClientUIAgent,
}
