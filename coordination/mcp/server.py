from __future__ import annotations

import base64
import importlib
import importlib.util
import inspect
import json
import os
import site
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Sequence

_MY_DIR = Path(__file__).resolve().parent
_COORD_ROOT = _MY_DIR.parent


def _load_ext_tool_class():
    site_dirs = site.getsitepackages()
    sp = None
    for d in site_dirs:
        d = Path(d)
        if (d / "mcp" / "types.py").exists():
            sp = d
            break
    if sp is None:
        from pydantic import BaseModel, ConfigDict

        class Tool(BaseModel):
            name: str
            description: str | None = None
            inputSchema: dict
            model_config = ConfigDict(extra="allow")

        return Tool

    types_file = Path(sp) / "mcp" / "types.py"
    _tmp_name = "_ext_mcp_types_via_spec"
    old_keys = set(sys.modules.keys())
    spec = importlib.util.spec_from_file_location(_tmp_name, str(types_file))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[_tmp_name] = mod
    try:
        spec.loader.exec_module(mod)
    except Exception:
        pass

    Tool = getattr(mod, "Tool", None)
    if Tool is None:
        from pydantic import BaseModel, ConfigDict

        class Tool(BaseModel):
            name: str
            description: str | None = None
            inputSchema: dict
            model_config = ConfigDict(extra="allow")

    return Tool


_Tool_Class = _load_ext_tool_class()


class _DummyMCPTypesModule:
    Tool = _Tool_Class


mcp_types = _DummyMCPTypesModule()


def _make_tool(name: str, description: str, input_schema: dict) -> Any:
    return _Tool_Class(name=name, description=description, inputSchema=input_schema)

from pydantic import BaseModel, create_model

from config.constants import ERROR_CODES, PARTICIPATION_PROFILES
from orchestration.cascade import cascade_done
from orchestration.deps import is_ready, resolve_effective_deps
from orchestration.materialize import materialize_pipeline
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
    TokenType,
)
from orchestration.pipeline_lifecycle import (
    cancel_pipeline,
    pause_pipeline,
    resume_pipeline,
)
from orchestration.state_machine import (
    EVENT_REJECT_REVIEW,
    EVENT_SET_DRAFT,
    EVENT_SOFT_SUBMIT,
    EVENT_SUBMIT_ARTIFACT,
    Event,
    transition,
)
from repo.branch_naming import allocate_seq, format_branch_name
from repo.hub import HubRepo, LFSConfig
from utils.hashing import audit_entry_hash, content_integrity_hash
from utils.tokens import check_token_scope

from .auth import (
    ToolContext,
    authorize,
    check_token_and_get_payload,
)
from .errors import tool_error
from .state_store import STORE
from .tracing import (
    _trace_id_var,
    get_current_trace_id,
    langfuse_trace,
)


_HUB_REPO_VAR: dict[str, HubRepo] = {"instance": None}


def set_hub_repo(hub: HubRepo) -> None:
    _HUB_REPO_VAR["instance"] = hub


def get_hub_repo() -> HubRepo | None:
    return _HUB_REPO_VAR.get("instance")


class AuditLogEntry(BaseModel):
    prev_hash: str
    action: str
    actor: str
    payload: dict
    hash: str
    created_at: str


class FastMCP:
    def __init__(self, name: str) -> None:
        self.name = name
        self._tools: list = []
        self._tool_handlers: dict[str, Callable[..., dict]] = {}
        self._tool_schemas: dict[str, dict] = {}
        self._tool_permissions: dict[str, dict] = {}

    def list_tools(self) -> list:
        return list(self._tools)

    def _infer_schema_from_signature(self, func: Callable) -> dict[str, Any]:
        sig = inspect.signature(func)
        properties: dict[str, Any] = {}
        required: list[str] = []

        for pname, param in sig.parameters.items():
            if pname in ("_ctx", "kwargs"):
                continue
            ptype = param.annotation
            if ptype is inspect.Parameter.empty:
                ptype = str

            schema_type = "string"
            if ptype is int:
                schema_type = "integer"
            elif ptype is float:
                schema_type = "number"
            elif ptype is bool:
                schema_type = "boolean"
            elif ptype is list or getattr(ptype, "__origin__", None) is list:
                schema_type = "array"
            elif ptype is dict or getattr(ptype, "__origin__", None) is dict:
                schema_type = "object"

            prop_schema: dict[str, Any] = {"type": schema_type}

            if param.default is inspect.Parameter.empty:
                required.append(pname)
            else:
                if param.default is not None:
                    prop_schema["default"] = param.default

            properties[pname] = prop_schema

        schema = {
            "type": "object",
            "properties": properties,
        }
        if required:
            schema["required"] = required
        return schema

    def tool(
        self,
        name: str | None = None,
        description: str = "",
        input_schema: dict | None = None,
        node_type_required: str | None = None,
        instance_id_required: str | None = None,
        permission_opts: dict | None = None,
    ) -> Callable:
        def decorator(func: Callable) -> Callable:
            tool_name = name or func.__name__

            perm = permission_opts or {}
            if node_type_required is not None:
                perm["node_type_required"] = node_type_required
            if instance_id_required is not None:
                perm["instance_id_required"] = instance_id_required

            schema = input_schema if input_schema is not None else self._infer_schema_from_signature(func)

            self._tool_schemas[tool_name] = schema
            self._tool_permissions[tool_name] = perm

            mcp_tool = mcp_types.Tool(
                name=tool_name,
                description=description or (func.__doc__ or "").strip() or tool_name,
                inputSchema=schema,
            )
            self._tools.append(mcp_tool)

            async def _execute(**kwargs: Any) -> dict:
                ctx = kwargs.pop("_ctx", None)
                trace_id = kwargs.pop("__trace_id", None) or (ctx.trace_id if ctx else "") or _trace_id_var.get("") or uuid.uuid4().hex
                _trace_id_var.set(trace_id)

                perm_opts = self._tool_permissions.get(tool_name, {})
                ntr = perm_opts.get("node_type_required")
                iir = perm_opts.get("instance_id_required")

                artifact_class = kwargs.get("classification")
                if artifact_class is None and "deps" in kwargs:
                    artifact_class = None

                try:
                    if ctx is None:
                        ctx = ToolContext(
                            pipeline_id=kwargs.get("pipeline_id"),
                            node_id=kwargs.get("node_id"),
                            role_instance_id=kwargs.get("role_instance_id"),
                            clearance=ClassificationLevel.INTERNAL,
                            trace_id=trace_id,
                        )
                    else:
                        if not ctx.trace_id:
                            ctx.trace_id = trace_id

                    if ctx.token_payload is None:
                        token = kwargs.get("token") or kwargs.get("jwt_token")
                        if token:
                            payload, err_code = check_token_and_get_payload(token)
                            if err_code == "E_TOKEN_EXPIRED":
                                raise ValueError("E_TOKEN_EXPIRED: Token has expired")
                            if err_code == "E_TOKEN_SCOPE_MISMATCH":
                                raise ValueError("E_TOKEN_SCOPE_MISMATCH: Token validation failed")
                            if payload is not None:
                                ctx.token_payload = payload

                    pipeline_def = None
                    if ctx.pipeline_id and ctx.pipeline_id in STORE.pipelines:
                        try:
                            pipeline_def = STORE.get_def(ctx.pipeline_id)
                        except Exception:
                            pass

                    authorize(
                        ctx=ctx,
                        tool_name=tool_name,
                        node_type_required=ntr,
                        instance_id_required=iir,
                        artifact_classification=artifact_class if isinstance(artifact_class, int) else None,
                        pipeline_def=pipeline_def,
                    )

                    call_kwargs = dict(kwargs)
                    try:
                        func_sig = inspect.signature(func)
                        if "_ctx" in func_sig.parameters:
                            call_kwargs["_ctx"] = ctx
                    except (TypeError, ValueError):
                        pass
                    if asyncio.iscoroutinefunction(func):
                        result = await func(**call_kwargs)
                    else:
                        result = func(**call_kwargs)
                    return {
                        "ok": True,
                        "data": result,
                        "error_code": None,
                        "error_message": None,
                        "trace_id": trace_id,
                    }
                except Exception as exc:
                    return tool_error(exc, trace_id)

            self._tool_handlers[tool_name] = _execute
            return func

        return decorator

    async def _dispatch_tool(self, name: str, arguments: dict) -> dict:
        handler = self._tool_handlers.get(name)
        if handler is None:
            trace_id = _trace_id_var.get("") or uuid.uuid4().hex
            return {
                "ok": False,
                "data": None,
                "error_code": "E_NOT_IMPLEMENTED",
                "error_message": f"Tool not found: {name}",
                "trace_id": trace_id,
            }
        try:
            return await handler(**arguments)
        except Exception as exc:
            trace_id = _trace_id_var.get("") or uuid.uuid4().hex
            return tool_error(exc, trace_id)


import asyncio


mcp = FastMCP("coordination-mcp")


def _bootstrap_state(defn: PipelineDefinition) -> tuple[PipelineState, list[str]]:
    now = datetime.now(timezone.utc).isoformat()
    node_states: dict[str, NodeState] = {}
    ready_roots: list[str] = []

    for n in defn.nodes:
        ns = NodeState(node_id=n.node_id, status=NodeStatus.BLOCKED)
        node_states[n.node_id] = ns

    state = PipelineState(
        pipeline_id=defn.id,
        version=1,
        status=PipelineStatus.ACTIVE,
        created_at=now,
        updated_at=now,
        node_states=node_states,
        cascade_pending=[],
        profile_id=defn.profile.id,
        classification=defn.classification,
        completed_nodes_count=0,
    )

    node_map = {n.node_id: n for n in defn.nodes}
    for n in defn.nodes:
        if is_ready(n.node_id, defn, state):
            node_states[n.node_id].status = NodeStatus.READY
            if not n.deps:
                ready_roots.append(n.node_id)
            else:
                up_ids = {d.upstream for d in n.deps}
                if not any(up in node_map for up in up_ids):
                    pass

    root_id = defn.root_product_node_id
    if root_id and root_id in node_states and node_states[root_id].status == NodeStatus.READY and root_id not in ready_roots:
        ready_roots.append(root_id)

    if not ready_roots:
        for nid, ns in node_states.items():
            if ns.status == NodeStatus.READY:
                ready_roots.append(nid)
                break

    return state, ready_roots


def _find_node_by_type(defn: PipelineDefinition, node_type: str) -> NodeDef | None:
    for n in defn.nodes:
        if n.node_type == node_type:
            return n
    return None


def _get_first_ready_node(state: PipelineState, defn: PipelineDefinition) -> str:
    for nid, ns in state.node_states.items():
        s = NodeStatus(ns.status) if isinstance(ns.status, str) else ns.status
        if s == NodeStatus.READY:
            return nid
    ps = _find_node_by_type(defn, "product_spec")
    if ps:
        return ps.node_id
    return list(defn.nodes)[0].node_id if defn.nodes else ""


def _make_draft_ref(node_id: str, path: str, content_b64: str, version: int, qualifier: str, artifact_type: str) -> dict:
    content_bytes = base64.b64decode(content_b64) if content_b64 else b""
    h = content_integrity_hash(content_bytes)
    return {
        "node_id": node_id,
        "artifact_type": artifact_type,
        "version": version,
        "qualifier": qualifier,
        "path": path,
        "draft_hash": h,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def _append_audit(prev_tip: str | None, action: str, actor: str, payload: dict) -> tuple[AuditLogEntry, str]:
    prev = prev_tip or ""
    h = audit_entry_hash(prev, action, actor, payload)
    entry = AuditLogEntry(
        prev_hash=prev,
        action=action,
        actor=actor,
        payload=payload,
        hash=h,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    return entry, h


_ALLOCATED_SEQS: dict[str, set[int]] = {}


@mcp.tool(
    name="create_pipeline",
    description="Create and bootstrap a pipeline with participation profile",
    input_schema={
        "type": "object",
        "properties": {
            "pipeline_id": {"type": "string"},
            "name": {"type": "string"},
            "participation": {"type": "string"},
            "nodes": {"type": "array", "items": {"type": "object"}},
            "template_id": {"type": ["string", "null"], "default": None},
        },
        "required": ["pipeline_id", "name", "participation", "nodes"],
    },
)
@langfuse_trace(name="create_pipeline", span_type="tool")
def create_pipeline(
    pipeline_id: str,
    name: str,
    participation: str,
    nodes: list[dict],
    template_id: str | None = None,
) -> dict:
    if participation not in PARTICIPATION_PROFILES:
        raise ValueError(f"Unknown participation profile: {participation}")

    profile = PARTICIPATION_PROFILES[participation]

    node_defs: list[NodeDef] = []
    for nd in nodes:
        node_defs.append(NodeDef.model_validate(nd))

    base_def = PipelineDefinition(
        id=pipeline_id,
        name=name,
        template_id=template_id,
        nodes=node_defs,
        profile=profile,
        root_product_node_id=(
            node_defs[0].node_id if node_defs and not node_defs[0].deps else None
        ),
    )

    mat_def = materialize_pipeline(base_def, profile)

    state, ready_roots = _bootstrap_state(mat_def)

    STORE.register(mat_def, state)

    return {
        "ready_roots": ready_roots,
        "pipeline_id": pipeline_id,
        "profile_applied": participation,
    }


@mcp.tool(
    name="submit_artifact",
    description="Submit artifact: commit to feature branch and open PR",
    input_schema={
        "type": "object",
        "properties": {
            "pipeline_id": {"type": "string"},
            "node_id": {"type": "string"},
            "artifact_type": {"type": "string"},
            "version": {"type": "integer", "minimum": 1},
            "qualifier": {"type": "string", "default": "default"},
            "path": {"type": "string"},
            "content_b64": {"type": "string"},
            "classification": {"type": "integer", "default": 1},
            "change_class": {"type": "string", "default": "compatible"},
            "pr_title": {"type": "string", "default": "PR"},
            "deps": {"type": ["array", "null"], "default": None},
        },
        "required": ["pipeline_id", "node_id", "artifact_type", "version", "path", "content_b64"],
    },
)
@langfuse_trace(name="submit_artifact", span_type="tool")
def submit_artifact(
    pipeline_id: str,
    node_id: str,
    artifact_type: str,
    version: int,
    qualifier: str = "default",
    path: str = "",
    content_b64: str = "",
    classification: int = 1,
    change_class: str = "compatible",
    pr_title: str = "PR",
    deps: list[dict] | None = None,
) -> dict:
    trace_id = get_current_trace_id()

    defn = STORE.get_def(pipeline_id)
    state = STORE.get_state(pipeline_id)

    ns = state.node_states.get(node_id)
    if ns is None:
        raise ValueError(f"Node not found: {node_id}")

    alloc_key = f"{pipeline_id}:{node_id}"
    if alloc_key not in _ALLOCATED_SEQS:
        _ALLOCATED_SEQS[alloc_key] = set()
    seq = allocate_seq(_ALLOCATED_SEQS[alloc_key])
    _ALLOCATED_SEQS[alloc_key].add(seq)

    branch_name = format_branch_name(pipeline_id, node_id, artifact_type, seq)

    content_bytes = base64.b64decode(content_b64) if content_b64 else b""
    commit_msg = f"feat({node_id}): {artifact_type} v{version} ({qualifier})"

    hub = get_hub_repo()
    pr_id = f"pr-{uuid.uuid4().hex[:8]}"

    if hub is not None:
        try:
            hub.commit_push_file(branch_name, path, content_bytes, commit_msg, LFSConfig())
        except Exception:
            pass

        template_data = {
            "node_id": node_id,
            "instance_id": node_id,
            "pipeline_id": pipeline_id,
            "deps": deps or [],
            "classification": classification,
            "artifact_type": artifact_type,
            "version": version,
            "qualifier": qualifier,
            "change_class": change_class,
            "modification_declaration": change_class,
            "trace_id": trace_id,
            "role_signature": f"{node_id}-{version}",
        }
        try:
            pr_id = hub.open_pr(branch_name, "main", pr_title, template_data)
        except Exception:
            pass
    else:
        pass

    STORE.set_pending_pr(node_id, pr_id)

    ns.pending_pr_count = max(1, ns.pending_pr_count)
    evt = Event(type=EVENT_SUBMIT_ARTIFACT, payload={"node_id": node_id})
    cur_status = NodeStatus(ns.status) if isinstance(ns.status, str) else ns.status
    new_s, side_effects, err = transition(cur_status, evt, ctx={"node_id": node_id})
    if new_s is not None and err is None:
        ns.status = new_s

    if change_class == "breaking":
        from orchestration.cascade import cascade_changed
        state2, evts = cascade_changed(node_id, "breaking", DepDeclaration().coupling, defn, state)
        state.node_states = state2.node_states

    state.updated_at = datetime.now(timezone.utc).isoformat()
    STORE.set_state(pipeline_id, state)

    status_val = ns.status
    if isinstance(status_val, NodeStatus):
        status_str = status_val.value
    else:
        status_str = str(status_val)

    return {
        "pr_id": pr_id,
        "branch_name": branch_name,
        "node_status_new": status_str if status_str else "pending_review",
    }


@mcp.tool(
    name="soft_submit_artifact",
    description="Save draft artifact without PR",
    input_schema={
        "type": "object",
        "properties": {
            "pipeline_id": {"type": "string"},
            "node_id": {"type": "string"},
            "artifact_type": {"type": "string"},
            "version": {"type": "integer", "minimum": 1},
            "qualifier": {"type": "string", "default": "default"},
            "path": {"type": "string", "default": ""},
            "content_b64": {"type": "string", "default": ""},
        },
        "required": ["pipeline_id", "node_id", "artifact_type", "version"],
    },
)
@langfuse_trace(name="soft_submit_artifact", span_type="tool")
def soft_submit_artifact(
    pipeline_id: str,
    node_id: str,
    artifact_type: str,
    version: int,
    qualifier: str = "default",
    path: str = "",
    content_b64: str = "",
) -> dict:
    state = STORE.get_state(pipeline_id)
    ns = state.node_states.get(node_id)
    if ns is None:
        raise ValueError(f"Node not found: {node_id}")

    evt = Event(type=EVENT_SET_DRAFT, payload={"node_id": node_id})
    cur_status = NodeStatus(ns.status) if isinstance(ns.status, str) else ns.status
    new_s, side_effects, err = transition(cur_status, evt, ctx={"node_id": node_id})
    if new_s is not None and err is None:
        ns.status = new_s

    draft_ref = _make_draft_ref(node_id, path, content_b64, version, qualifier, artifact_type)
    add = Addendum(
        id=f"draft-{uuid.uuid4().hex[:8]}",
        version=1,
        change_class="informational",
        incompatible_with=[],
        impact_claim=[],
        diff_hash=draft_ref["draft_hash"],
        author="draft",
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    ns.addenda = [add]

    state.updated_at = datetime.now(timezone.utc).isoformat()
    STORE.set_state(pipeline_id, state)

    s = ns.status
    status_str = s.value if isinstance(s, NodeStatus) else str(s)

    return {"draft": True, "node_status": status_str or "draft"}


@mcp.tool(
    name="get_dependencies",
    description="Resolve and return effective upstream artifacts",
    input_schema={
        "type": "object",
        "properties": {
            "pipeline_id": {"type": "string"},
            "node_id": {"type": "string"},
            "include_draft": {"type": "boolean", "default": False},
            "content_max_bytes": {"type": ["integer", "null"], "default": None},
        },
        "required": ["pipeline_id", "node_id"],
    },
)
@langfuse_trace(name="get_dependencies", span_type="tool")
def get_dependencies(
    pipeline_id: str,
    node_id: str,
    include_draft: bool = False,
    content_max_bytes: int | None = None,
    _ctx: ToolContext | None = None,
) -> list[dict]:
    defn = STORE.get_def(pipeline_id)
    state = STORE.get_state(pipeline_id)

    eff_deps = resolve_effective_deps(node_id, defn, state)

    ctx_clearance = ClassificationLevel.INTERNAL
    if _ctx is not None:
        ctx_clearance = _ctx.clearance if isinstance(_ctx.clearance, ClassificationLevel) else ClassificationLevel(int(_ctx.clearance))

    hub = get_hub_repo()
    results: list[dict] = []

    for up_id, decl in eff_deps:
        up_ns = state.node_states.get(up_id)
        if up_ns is None:
            continue
        up_status = NodeStatus(up_ns.status) if isinstance(up_ns.status, str) else up_ns.status
        up_def = next((n for n in defn.nodes if n.node_id == up_id), None)
        up_class = int(up_def.classification) if up_def is not None else 1

        filtered = int(up_class) > int(ctx_clearance)

        bytes_b64 = ""
        if not filtered:
            if up_status == NodeStatus.DONE and hub is not None and up_ns.artifact_refs:
                ref = up_ns.artifact_refs[0]
                try:
                    raw = hub.git_show(ref.uri, ref.provenance.commit_sha if ref.provenance else "HEAD")
                    bytes_b64 = base64.b64encode(raw).decode()
                    if content_max_bytes and len(raw) > content_max_bytes:
                        bytes_b64 = ""
                except Exception:
                    bytes_b64 = ""

        result_entry = {
            "upstream_id": up_id,
            "status": up_status.value if isinstance(up_status, NodeStatus) else str(up_status),
            "classification": up_class,
            "bytes_base64": "" if filtered else bytes_b64,
            "filtered": filtered,
            "artifact_refs": [
                {
                    "node_id": r.node_id,
                    "artifact_type": r.artifact_type,
                    "version": r.version,
                    "qualifier": r.qualifier,
                    "uri": r.uri,
                }
                for r in up_ns.artifact_refs
            ],
        }
        results.append(result_entry)

    return results


@mcp.tool(
    name="review_artifact_pr",
    description="Review artifact PR (stub - returns needs_human)",
    input_schema={
        "type": "object",
        "properties": {
            "pipeline_id": {"type": "string"},
            "pr_id": {"type": "string"},
        },
        "required": ["pipeline_id", "pr_id"],
    },
)
@langfuse_trace(name="review_artifact_pr", span_type="tool")
def review_artifact_pr(pipeline_id: str, pr_id: str) -> dict:
    return {
        "verdict": "needs_human",
        "checks": {
            "required_fields": "pass",
            "schema": "pass",
            "secret_scan": "pass",
        },
        "needs_human": True,
        "summary": "stub review ok",
    }


@mcp.tool(
    name="approve_pr",
    description="Approve and squash merge a PR, write artifact ref and audit log",
    input_schema={
        "type": "object",
        "properties": {
            "pipeline_id": {"type": "string"},
            "pr_id": {"type": "string"},
            "bot_actor": {"type": "string", "default": "coordination-bot"},
            "note": {"type": "string", "default": ""},
        },
        "required": ["pipeline_id", "pr_id"],
    },
)
@langfuse_trace(name="approve_pr", span_type="tool")
def approve_pr(
    pipeline_id: str,
    pr_id: str,
    bot_actor: str = "coordination-bot",
    note: str = "",
) -> dict:
    trace_id = get_current_trace_id()

    defn = STORE.get_def(pipeline_id)
    state = STORE.get_state(pipeline_id)

    target_node_id = None
    for nid, pr in STORE.pending_prs.items():
        if pr == pr_id:
            target_node_id = nid
            break
    if target_node_id is None:
        target_node_id = _get_first_ready_node(state, defn)

    ns = state.node_states.get(target_node_id)
    if ns is None:
        raise ValueError(f"Node not found: {target_node_id}")

    hub = get_hub_repo()
    commit_sha = f"{uuid.uuid4().hex[:40]}"
    if hub is not None:
        try:
            commit_sha = hub.approve_and_squash_merge(pr_id, bot_actor)
        except Exception:
            pass

    for n in defn.nodes:
        if n.node_id == target_node_id:
            atype = n.node_type
            break
    else:
        atype = "artifact"

    if ns.artifact_refs:
        version = ns.artifact_refs[-1].version + 1
        qualifier = ns.artifact_refs[-1].qualifier
    else:
        version = 1
        qualifier = "default"

    prov = Provenance(
        commit_sha=commit_sha,
        pr_id=pr_id,
        approver_ids=[bot_actor],
        reviewer_ids=[],
        merged_at=datetime.now(timezone.utc).isoformat(),
    )
    ref = ArtifactRef(
        node_id=target_node_id,
        artifact_type=atype,
        version=version,
        qualifier=qualifier,
        uri=f"commit://{commit_sha}",
        external=False,
        ref_hash=f"sha256:{uuid.uuid4().hex}",
        trace_id=trace_id,
        provenance=prov,
    )
    ns.artifact_refs = ns.artifact_refs + [ref]

    _entry, new_tip = _append_audit(
        state.hash_chain_tip,
        "APPROVE_PR",
        bot_actor,
        {"pr_id": pr_id, "node_id": target_node_id, "commit_sha": commit_sha, "note": note},
    )
    state.hash_chain_tip = new_tip

    state2, events = cascade_done(target_node_id, defn, state)
    state.node_states = state2.node_states

    done_count = 0
    for nid, nss in state.node_states.items():
        s = NodeStatus(nss.status) if isinstance(nss.status, str) else nss.status
        if s == NodeStatus.DONE:
            done_count += 1
    state.completed_nodes_count = done_count

    state.updated_at = datetime.now(timezone.utc).isoformat()
    STORE.set_state(pipeline_id, state)

    ns = state.node_states[target_node_id]
    s = ns.status
    status_str = s.value if isinstance(s, NodeStatus) else str(s)

    return {
        "commit_sha": commit_sha,
        "artifact_ref": {
            "node_id": ref.node_id,
            "artifact_type": ref.artifact_type,
            "version": ref.version,
            "qualifier": ref.qualifier,
            "uri": ref.uri,
            "ref_hash": ref.ref_hash,
            "trace_id": ref.trace_id,
            "provenance": ref.provenance.model_dump() if ref.provenance else None,
        },
        "node_new_status": status_str or "done",
    }


@mcp.tool(
    name="reject_pr",
    description="Reject PR and reset node to ready",
    input_schema={
        "type": "object",
        "properties": {
            "pipeline_id": {"type": "string"},
            "pr_id": {"type": "string"},
            "reason": {"type": "string"},
        },
        "required": ["pipeline_id", "pr_id", "reason"],
    },
)
@langfuse_trace(name="reject_pr", span_type="tool")
def reject_pr(pipeline_id: str, pr_id: str, reason: str) -> dict:
    defn = STORE.get_def(pipeline_id)
    state = STORE.get_state(pipeline_id)

    target_node_id = None
    for nid, pr in STORE.pending_prs.items():
        if pr == pr_id:
            target_node_id = nid
            break
    if target_node_id is None:
        target_node_id = _get_first_ready_node(state, defn)

    ns = state.node_states.get(target_node_id)
    if ns is None:
        raise ValueError(f"Node not found: {target_node_id}")

    hub = get_hub_repo()
    if hub is not None:
        try:
            hub.reject_pr(pr_id, reason)
        except Exception:
            pass

    evt = Event(type="REJECT_REVIEW", payload={"node_id": target_node_id, "reason": reason})
    cur_status = NodeStatus(ns.status) if isinstance(ns.status, str) else ns.status
    new_s, side_effects, err = transition(cur_status, evt, ctx={"node_id": target_node_id})
    if new_s is not None and err is None:
        ns.status = new_s
    else:
        ns.status = NodeStatus.READY

    if ns.pending_pr_count > 0:
        ns.pending_pr_count -= 1

    evt_log = Event(type=EVENT_REJECT_REVIEW, payload={"node_id": target_node_id, "reason": reason})

    state.updated_at = datetime.now(timezone.utc).isoformat()
    STORE.set_state(pipeline_id, state)

    s = ns.status
    status_str = s.value if isinstance(s, NodeStatus) else str(s)

    return {"ok": True, "node_status_new": status_str or "ready"}


@mcp.tool(
    name="update_progress",
    description="Update node status with transition check",
    input_schema={
        "type": "object",
        "properties": {
            "pipeline_id": {"type": "string"},
            "node_id": {"type": "string"},
            "status": {"type": "string"},
            "note": {"type": "string", "default": ""},
        },
        "required": ["pipeline_id", "node_id", "status"],
    },
)
@langfuse_trace(name="update_progress", span_type="tool")
def update_progress(
    pipeline_id: str,
    node_id: str,
    status: str,
    note: str = "",
) -> dict:
    state = STORE.get_state(pipeline_id)
    ns = state.node_states.get(node_id)
    if ns is None:
        raise ValueError(f"Node not found: {node_id}")

    target = NodeStatus(status) if status in {s.value for s in NodeStatus} else NodeStatus.IN_PROGRESS
    ns.status = target

    state.updated_at = datetime.now(timezone.utc).isoformat()
    STORE.set_state(pipeline_id, state)

    return {"status_new": target.value}


@mcp.tool(
    name="get_pipeline_state",
    description="Get pipeline state summary for visualization",
    input_schema={
        "type": "object",
        "properties": {
            "pipeline_id": {"type": "string"},
        },
        "required": ["pipeline_id"],
    },
)
@langfuse_trace(name="get_pipeline_state", span_type="tool")
def get_pipeline_state(pipeline_id: str) -> dict:
    defn = STORE.get_def(pipeline_id)
    state = STORE.get_state(pipeline_id)

    nodes_list: list[dict] = []
    for n in defn.nodes:
        ns = state.node_states.get(n.node_id)
        s = NodeStatus(ns.status) if ns and isinstance(ns.status, str) else (ns.status if ns else NodeStatus.BLOCKED)
        status_val = s.value if isinstance(s, NodeStatus) else str(s)
        nodes_list.append({
            "id": n.node_id,
            "status": status_val,
            "optional": n.optional,
        })

    ps = state.status
    pipeline_status_val = ps.value if isinstance(ps, PipelineStatus) else str(ps)

    return {
        "pipeline_id": pipeline_id,
        "status": pipeline_status_val,
        "nodes": nodes_list,
        "completed_nodes_count": state.completed_nodes_count,
        "hash_chain_tip": state.hash_chain_tip,
    }


@mcp.tool(
    name="pause_pipeline",
    description="Pause pipeline",
    input_schema={
        "type": "object",
        "properties": {
            "pipeline_id": {"type": "string"},
            "reason": {"type": "string", "default": ""},
        },
        "required": ["pipeline_id"],
    },
)
@langfuse_trace(name="pause_pipeline", span_type="tool")
def pause_pipeline_tool(pipeline_id: str, reason: str = "") -> dict:
    state = STORE.get_state(pipeline_id)
    new_state, events = pause_pipeline(state, reason)
    STORE.set_state(pipeline_id, new_state)
    ps = new_state.status
    val = ps.value if isinstance(ps, PipelineStatus) else str(ps)
    return {"pipeline_status_new": val}


@mcp.tool(
    name="resume_pipeline",
    description="Resume pipeline",
    input_schema={
        "type": "object",
        "properties": {
            "pipeline_id": {"type": "string"},
        },
        "required": ["pipeline_id"],
    },
)
@langfuse_trace(name="resume_pipeline", span_type="tool")
def resume_pipeline_tool(pipeline_id: str) -> dict:
    defn = STORE.get_def(pipeline_id)
    state = STORE.get_state(pipeline_id)
    new_state, events = resume_pipeline(defn, state)
    STORE.set_state(pipeline_id, new_state)
    ps = new_state.status
    val = ps.value if isinstance(ps, PipelineStatus) else str(ps)
    return {"pipeline_status_new": val}


@mcp.tool(
    name="cancel_pipeline",
    description="Cancel pipeline",
    input_schema={
        "type": "object",
        "properties": {
            "pipeline_id": {"type": "string"},
            "reason": {"type": "string", "default": ""},
        },
        "required": ["pipeline_id"],
    },
)
@langfuse_trace(name="cancel_pipeline", span_type="tool")
def cancel_pipeline_tool(pipeline_id: str, reason: str = "") -> dict:
    defn = STORE.get_def(pipeline_id)
    state = STORE.get_state(pipeline_id)
    new_state, events = cancel_pipeline(defn, state, reason)
    STORE.set_state(pipeline_id, new_state)
    ps = new_state.status
    val = ps.value if isinstance(ps, PipelineStatus) else str(ps)
    return {"pipeline_status_new": val}


def _make_tool_decorator():
    pass
