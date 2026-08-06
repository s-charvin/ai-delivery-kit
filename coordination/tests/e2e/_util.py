from __future__ import annotations

import asyncio
import base64
import sys
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from audit.engine import RuleEngine
from audit.merge_approve import MergeApproveService
from audit.worm_storage import AuditLogEntry
from config.constants import PARTICIPATION_PROFILES
from orchestration.materialize import (
    is_pipeline_completed,
    materialize_pipeline,
)
from orchestration.models import (
    ClassificationLevel,
    DepCoupling,
    DepDeclaration,
    DepPresence,
    DepStrictness,
    NodeDef,
    NodeState,
    NodeStatus,
    PipelineDefinition,
    PipelineState,
    PipelineStatus,
)
from mcp.server import (
    _bootstrap_state,
    mcp,
)
from mcp.state_store import STORE
from repo.hub import PrDetail

_HUB_GLOBAL_LOCK = threading.RLock()


def _make_nodes_dict(extra_nodes: list[NodeDef] | None = None) -> dict[str, NodeDef]:
    n1 = NodeDef(
        node_id="n1",
        node_type="product_spec",
        role_assignments=[],
        deps=[],
    )
    n2 = NodeDef(
        node_id="n2",
        node_type="api_contract",
        role_assignments=[],
        deps=[
            DepDeclaration(
                upstream="n1",
                presence=DepPresence.REQUIRED,
                strictness=DepStrictness.STRICT,
                coupling=DepCoupling.HARD,
            )
        ],
    )
    n3 = NodeDef(
        node_id="n3",
        node_type="design_asset",
        role_assignments=[],
        deps=[
            DepDeclaration(
                upstream="n1",
                presence=DepPresence.REQUIRED,
                strictness=DepStrictness.STRICT,
                coupling=DepCoupling.HARD,
            )
        ],
    )
    n4 = NodeDef(
        node_id="n4",
        node_type="client_ui_impl",
        role_assignments=[],
        deps=[
            DepDeclaration(
                upstream="n2",
                presence=DepPresence.REQUIRED,
                strictness=DepStrictness.STRICT,
                coupling=DepCoupling.HARD,
            ),
            DepDeclaration(
                upstream="n3",
                presence=DepPresence.IF_PRESENT,
                strictness=DepStrictness.STRICT,
                coupling=DepCoupling.HARD,
            ),
        ],
    )
    n5 = NodeDef(
        node_id="n5",
        node_type="server_impl",
        role_assignments=[],
        deps=[
            DepDeclaration(
                upstream="n2",
                presence=DepPresence.REQUIRED,
                strictness=DepStrictness.STRICT,
                coupling=DepCoupling.HARD,
            )
        ],
    )
    n6 = NodeDef(
        node_id="n6",
        node_type="server_test",
        role_assignments=[],
        deps=[
            DepDeclaration(
                upstream="n5",
                presence=DepPresence.REQUIRED,
                strictness=DepStrictness.STRICT,
                coupling=DepCoupling.HARD,
            )
        ],
    )
    n7 = NodeDef(
        node_id="n7",
        node_type="delivery_gate",
        role_assignments=[],
        deps=[
            DepDeclaration(
                upstream="n4",
                presence=DepPresence.IF_PRESENT,
                strictness=DepStrictness.STRICT,
                coupling=DepCoupling.HARD,
            ),
            DepDeclaration(
                upstream="n6",
                presence=DepPresence.REQUIRED,
                strictness=DepStrictness.STRICT,
                coupling=DepCoupling.HARD,
            ),
            DepDeclaration(
                upstream="n3",
                presence=DepPresence.IF_PRESENT,
                strictness=DepStrictness.STRICT,
                coupling=DepCoupling.HARD,
            ),
        ],
    )
    result = {
        "n1": n1,
        "n2": n2,
        "n3": n3,
        "n4": n4,
        "n5": n5,
        "n6": n6,
        "n7": n7,
    }
    if extra_nodes:
        for nd in extra_nodes:
            result[nd.node_id] = nd
    return result


class HappyPathDriver:
    def __init__(self, env: Any):
        self.env = env
        self.pid: str = ""
        self.engine = RuleEngine()
        self.merge_service = MergeApproveService(
            hub=env.hub,
            worm=env.worm,
            state_store=STORE,
            engine=self.engine,
        )
        self._submitted_prs: dict[str, str] = {}

    def create_pipeline(
        self,
        participation: str = "fullstack",
        extra_nodes: list[NodeDef] | None = None,
        pid: str | None = None,
    ) -> list[str]:
        nodes_map = _make_nodes_dict(extra_nodes)
        nodes_list = list(nodes_map.values())
        if pid is None:
            pid = f"pipe-{uuid.uuid4().hex[:8]}"
        self.pid = pid

        if participation not in PARTICIPATION_PROFILES:
            raise ValueError(f"Unknown profile: {participation}")
        profile = PARTICIPATION_PROFILES[participation].model_copy(deep=True)

        base_def = PipelineDefinition(
            id=pid,
            name=f"test-{participation}",
            nodes=nodes_list,
            profile=profile,
            root_product_node_id="n1" if "n1" in nodes_map else nodes_list[0].node_id,
        )

        mat_def = materialize_pipeline(base_def, profile)
        state, ready_roots = _bootstrap_state(mat_def)
        STORE.register(mat_def, state)
        return ready_roots

    def _node_type_for(self, node_id: str) -> str:
        defn = STORE.get_def(self.pid)
        for n in defn.nodes:
            if n.node_id == node_id:
                return n.node_type
        return "artifact"

    def _submit_to_hub(
        self,
        node_id: str,
        content: bytes,
        classification: int,
        change_class: str,
        pr_extra_template: dict | None,
        artifact_type: str | None,
        path: str | None,
    ) -> tuple[str, str]:
        from repo.branch_naming import allocate_seq, format_branch_name

        seq_key = f"{self.pid}:{node_id}"
        seq_set = getattr(self, "_seq_map", None)
        if seq_set is None:
            seq_set = {}
            setattr(self, "_seq_map", seq_set)
        if seq_key not in seq_set:
            seq_set[seq_key] = set()
        seq = allocate_seq(seq_set[seq_key])
        seq_set[seq_key].add(seq)

        atype = artifact_type or self._node_type_for(node_id)
        branch_name = format_branch_name(self.pid, node_id, atype, seq)
        final_path = path or f"artifacts/{node_id}/{atype}-v{seq}.md"
        commit_msg = f"feat({node_id}): {atype} v{seq}"

        with _HUB_GLOBAL_LOCK:
            try:
                self.env.hub.commit_push_file(branch_name, final_path, content, commit_msg)
            except Exception:
                pass

            exact = False
            if pr_extra_template and pr_extra_template.pop("_exact", False):
                exact = True

            if exact and pr_extra_template is not None:
                template_data = dict(pr_extra_template)
                for k, v in {
                    "trace_id": uuid.uuid4().hex,
                    "role_signature": f"{node_id}-{seq}",
                }.items():
                    if k not in template_data:
                        template_data[k] = v
            else:
                template_data = {
                    "node_id": node_id,
                    "instance_id": node_id,
                    "pipeline_id": self.pid,
                    "deps": [],
                    "classification": classification,
                    "artifact_type": atype,
                    "version": seq,
                    "qualifier": "default",
                    "change_class": change_class,
                    "modification_declaration": change_class,
                    "trace_id": uuid.uuid4().hex,
                    "role_signature": f"{node_id}-{seq}",
                    "submitter_role": self._default_role_for_node(node_id),
                    "clearance": classification,
                }
                if pr_extra_template:
                    template_data.update(pr_extra_template)
            pr_title = f"PR: {node_id} {atype} v{seq}"
            pr_id = self.env.hub.open_pr(branch_name, "main", pr_title, template_data)
        return pr_id, final_path

    def _default_role_for_node(self, node_id: str) -> str:
        ntype = self._node_type_for(node_id)
        mapping = {
            "product_spec": "product",
            "design_asset": "design",
            "api_contract": "product",
            "client_ui_impl": "client_ui",
            "server_impl": "server_impl",
            "server_test": "server_test",
            "client_test": "client_test",
            "delivery_gate": "ops",
        }
        return mapping.get(ntype, ntype)

    def _transition_node_status(self, node_id: str, event_type: str) -> None:
        from orchestration.state_machine import Event, transition

        state = STORE.get_state(self.pid)
        ns = state.node_states.get(node_id)
        if ns is None:
            return
        cur_status = NodeStatus(ns.status) if isinstance(ns.status, str) else ns.status
        evt = Event(type=event_type, payload={"node_id": node_id})
        new_s, _se, _err = transition(cur_status, evt, ctx={"node_id": node_id})
        if new_s is not None:
            ns.status = new_s
        STORE.set_state(self.pid, state)

    def _submit_transition(self, node_id: str) -> None:
        state = STORE.get_state(self.pid)
        ns = state.node_states.get(node_id)
        if ns is None:
            return
        ns.pending_pr_count = max(1, ns.pending_pr_count)
        STORE.set_state(self.pid, state)
        self._transition_node_status(node_id, "SUBMIT_ARTIFACT")

    def _run_engine_review(
        self,
        node_id: str,
        pr_id: str,
        content_bytes_in: dict[str, bytes] | None = None,
    ) -> dict:
        from mcp.review_integration import _build_context_from_state

        defn = STORE.get_def(self.pid)
        state = STORE.get_state(self.pid)
        try:
            pr_detail = self.env.hub.get_pr_detail(pr_id)
        except Exception:
            pr_detail = PrDetail(
                pr_id=pr_id,
                from_branch=f"feat/{pr_id}",
                to_branch="main",
                title=f"PR {pr_id}",
                template={
                    "node_id": node_id,
                    "instance_id": node_id,
                    "pipeline_id": self.pid,
                    "deps": [],
                    "artifact_type": "artifact",
                    "version": 1,
                },
                files=[],
                diff_unified="",
                commits=[],
                state="open",
            )
        content_bytes = content_bytes_in or {}
        ctx = _build_context_from_state(
            pipeline_def=defn,
            pipeline_state=state,
            node_id=node_id,
            pr_id=pr_id,
            pr_detail=pr_detail,
            content_bytes=content_bytes,
            role_instance_id=node_id,
            submitter_role=self._default_role_for_node(node_id),
            clearance=ClassificationLevel(int(pr_detail.template.get("classification", 1))),
        )
        return self.engine.evaluate(ctx)

    def submit_and_approve(
        self,
        node_id: str,
        content: bytes | None = None,
        classification: int = 1,
        change_class: str = "compatible",
        skip_review: bool = False,
        human_approvals: int = 1,
        required_humans: int = 0,
        pr_extra_template: dict | None = None,
        artifact_type: str | None = None,
        path: str | None = None,
    ) -> str:
        if content is None:
            content = f"content for {node_id} at {datetime.now(timezone.utc).isoformat()}".encode("utf-8")

        pr_id, final_path = self._submit_to_hub(
            node_id, content, classification, change_class,
            pr_extra_template, artifact_type, path,
        )
        STORE.set_pending_pr(node_id, pr_id)
        self._submitted_prs[node_id] = pr_id
        self._submit_transition(node_id)

        ns = self.get_node(node_id)
        s = NodeStatus(ns.status) if isinstance(ns.status, str) else ns.status
        assert s == NodeStatus.PENDING_REVIEW, f"after submit node should be pending_review, got {s}"

        if not skip_review:
            self._transition_node_status(node_id, "START_REVIEW")
            cb: dict[str, bytes] = {final_path: content}
            review_result = self._run_engine_review(node_id, pr_id, cb)
            verdict = review_result["verdict"]
            if verdict == "reject":
                return ""

        try:
            with _HUB_GLOBAL_LOCK:
                result = self.merge_service.approve(
                    pipeline_id=self.pid,
                    pr_id=pr_id,
                    bot_actor="coordination-bot",
                    human_approvals=human_approvals,
                    required_humans=required_humans,
                    note="auto-approved",
                )
        except Exception:
            return ""

        ns2 = self.get_node(node_id)
        s2 = NodeStatus(ns2.status) if isinstance(ns2.status, str) else ns2.status
        assert s2 == NodeStatus.DONE, f"after approve node should be done, got {s2}"
        return result.get("commit_sha", "")

    def reject_reason_expected(
        self,
        node_id: str,
        content: bytes,
        expected_error_code_substr: str,
        classification: int = 1,
        change_class: str = "compatible",
        pr_extra_template: dict | None = None,
    ) -> dict:
        pr_id, final_path = self._submit_to_hub(
            node_id, content, classification, change_class,
            pr_extra_template, None, None,
        )
        STORE.set_pending_pr(node_id, pr_id)
        self._submitted_prs[node_id] = pr_id
        self._submit_transition(node_id)
        self._transition_node_status(node_id, "START_REVIEW")

        cb: dict[str, bytes] = {final_path: content}
        review_result = self._run_engine_review(node_id, pr_id, cb)
        rejected_by = review_result.get("rejected_by") or ""
        assert expected_error_code_substr in rejected_by or any(
            expected_error_code_substr in c.get("rule_id", "")
            for c in review_result.get("checks", [])
            if not c.get("pass", True)
        ), f"expected rejection containing {expected_error_code_substr}, got {review_result}"

        state = STORE.get_state(self.pid)
        ns = state.node_states.get(node_id)
        if ns is not None:
            evt_type = "REJECT_REVIEW"
            from orchestration.state_machine import Event, transition
            cur_status = NodeStatus(ns.status) if isinstance(ns.status, str) else ns.status
            evt = Event(type=evt_type, payload={"node_id": node_id, "reason": rejected_by})
            new_s, _se, _err = transition(cur_status, evt, ctx={"node_id": node_id})
            if new_s is not None:
                ns.status = new_s
            else:
                ns.status = NodeStatus.READY
            if ns.pending_pr_count > 0:
                ns.pending_pr_count -= 1
        STORE.set_state(self.pid, state)
        return review_result

    def get_state(self) -> PipelineState:
        return STORE.states[self.pid]

    def get_node(self, nid: str) -> NodeState:
        return self.get_state().node_states[nid]

    def is_pipeline_completed(self) -> bool:
        defn = STORE.get_def(self.pid)
        state = STORE.get_state(self.pid)
        return is_pipeline_completed(defn, state)

    def mark_pipeline_completed_if_done(self) -> None:
        if self.is_pipeline_completed():
            state = STORE.get_state(self.pid)
            state.status = PipelineStatus.COMPLETED
            STORE.set_state(self.pid, state)

    def skip_finalize(self) -> None:
        from orchestration.state_machine import EVENT_SKIP_OPTIONAL, Event, transition

        defn = STORE.get_def(self.pid)
        state = STORE.get_state(self.pid)
        for n in defn.nodes:
            if not n.optional:
                continue
            ns = state.node_states.get(n.node_id)
            if ns is None:
                continue
            cur_status = NodeStatus(ns.status) if isinstance(ns.status, str) else ns.status
            if cur_status in {NodeStatus.DONE, NodeStatus.SKIPPED, NodeStatus.DEPRECATED}:
                continue
            evt = Event(type=EVENT_SKIP_OPTIONAL, payload={"node_id": n.node_id})
            new_s, _se, _err = transition(cur_status, evt, ctx={"node_id": n.node_id})
            if new_s is not None:
                ns.status = new_s
            worm_entry = AuditLogEntry(
                prev_hash="",
                action="NODE_SKIPPED",
                actor="coordination-bot",
                payload={"node_id": n.node_id, "optional": True, "reason": "skip_finalize"},
                hash="",
                created_at=datetime.now(timezone.utc).isoformat(),
                pipeline_id=self.pid,
                node_id=n.node_id,
                trace_id=uuid.uuid4().hex,
            )
            try:
                self.env.worm.insert(worm_entry)
                state.hash_chain_tip = worm_entry.hash
            except Exception:
                pass
        STORE.set_state(self.pid, state)
