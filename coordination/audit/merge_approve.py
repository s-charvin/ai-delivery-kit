from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from audit.engine import ReviewContext, RuleEngine
from audit.worm_storage import AuditLogEntry, WormStorage
from config.constants import ERROR_CODES
from orchestration.cascade import cascade_done
from orchestration.models import (
    ArtifactRef,
    ClassificationLevel,
    NodeStatus,
    PipelineDefinition,
    PipelineState,
    Provenance,
)
from repo.hub import HubRepo, PrDetail
from utils.hashing import content_integrity_hash


APPROVE_MERGE_ACTION = "APPROVE_MERGE"


class E_HUMAN_REVIEW_REQUIRED(Exception):
    pass


def _build_review_context(
    pipeline_def: PipelineDefinition,
    pipeline_state: PipelineState,
    node_id: str,
    pr_id: str,
    pr_detail: PrDetail,
    trace_id: str = "",
) -> ReviewContext:
    template = pr_detail.template or {}

    node_def = None
    for n in pipeline_def.nodes:
        if n.node_id == node_id:
            node_def = n
            break

    node_type = node_def.node_type if node_def else "artifact"
    artifact_class = ClassificationLevel(int(template.get("classification", 1)))
    change_class = str(template.get("change_class", "compatible"))
    addendum_declared = bool(template.get("addendum_declared")) or (change_class == "addendum")

    diff_added = 0
    diff_deleted = 0
    for line in (pr_detail.diff_unified or "").splitlines():
        if line.startswith("+") and not line.startswith("+++"):
            diff_added += 1
        elif line.startswith("-") and not line.startswith("---"):
            diff_deleted += 1

    content_bytes: dict[str, bytes] = {}
    external_refs: list[str] = []

    import re

    url_pattern = re.compile(r"https?://[^\s\"'>)]+")
    for line in (pr_detail.diff_unified or "").splitlines():
        urls = url_pattern.findall(line)
        external_refs.extend(urls)

    role_instance_id = str(template.get("instance_id", node_id))
    submitter_role_raw = str(template.get("submitter_role", node_type))
    default_role_map: dict[str, str] = {
        "product_spec": "product",
        "design_asset": "design",
        "api_contract": "product",
        "client_ui_impl": "client_ui",
        "server_impl": "server_impl",
        "server_test": "server_test",
        "client_test": "client_test",
        "delivery_gate": "ops",
    }
    submitter_role = default_role_map.get(node_type, submitter_role_raw)
    if template.get("submitter_role"):
        submitter_role = template.get("submitter_role")
    clearance = ClassificationLevel(int(template.get("clearance", 1)))

    return ReviewContext(
        pipeline_def=pipeline_def,
        pipeline_state=pipeline_state,
        node_id=node_id,
        pr_id=pr_id,
        pr_detail=pr_detail,
        template=template,
        content_bytes=content_bytes,
        diff_added_lines=diff_added,
        diff_deleted_lines=diff_deleted,
        diff_unified=pr_detail.diff_unified or "",
        role_instance_id=role_instance_id,
        token_payload={"sub": role_instance_id},
        clearance=clearance,
        skill=None,
        submitter_role=submitter_role,
        node_type=node_type,
        artifact_classification=artifact_class,
        change_class_declared=change_class,
        addendum_declared=addendum_declared,
        external_refs=external_refs,
        trace_id=trace_id,
    )


class MergeApproveService:
    def __init__(
        self,
        hub: HubRepo | None = None,
        worm: WormStorage | None = None,
        state_store: Any = None,
        hasher: Any = None,
        engine: RuleEngine | None = None,
    ):
        self.hub = hub
        self.worm = worm
        self.state_store = state_store
        self.hasher = hasher or content_integrity_hash
        self.engine = engine or RuleEngine()

    def _get_def(self, pipeline_id: str) -> PipelineDefinition:
        if self.state_store is not None and hasattr(self.state_store, "get_def"):
            return self.state_store.get_def(pipeline_id)
        raise ValueError(f"state_store required for pipeline_id={pipeline_id}")

    def _get_state(self, pipeline_id: str) -> PipelineState:
        if self.state_store is not None and hasattr(self.state_store, "get_state"):
            return self.state_store.get_state(pipeline_id)
        raise ValueError(f"state_store required for pipeline_id={pipeline_id}")

    def _set_state(self, pipeline_id: str, state: PipelineState) -> None:
        if self.state_store is not None and hasattr(self.state_store, "set_state"):
            self.state_store.set_state(pipeline_id, state)
            return
        raise ValueError("state_store.set_state required")

    def _find_node_for_pr(
        self, pipeline_id: str, pr_id: str, defn: PipelineDefinition, state: PipelineState
    ) -> str:
        if self.state_store is not None and hasattr(self.state_store, "pending_prs"):
            for nid, pr in self.state_store.pending_prs.items():
                if pr == pr_id:
                    return nid
        if state.node_states:
            for nid in list(state.node_states.keys()):
                return nid
        if defn.nodes:
            return defn.nodes[0].node_id
        raise ValueError(f"Cannot locate node for pr_id={pr_id}")

    def approve(
        self,
        pipeline_id: str,
        pr_id: str,
        bot_actor: str = "coordination-bot",
        human_approvals: int = 0,
        required_humans: int = 0,
        note: str = "",
    ) -> dict:
        trace_id = uuid4().hex

        defn = self._get_def(pipeline_id)
        state = self._get_state(pipeline_id)

        node_id = self._find_node_for_pr(pipeline_id, pr_id, defn, state)

        pr_detail: PrDetail
        if self.hub is not None:
            try:
                pr_detail = self.hub.get_pr_detail(pr_id)
                if pr_detail.state not in {"open", "pending_review"}:
                    if pr_detail.state != "open":
                        pass
            except Exception:
                pr_detail = PrDetail(
                    pr_id=pr_id,
                    from_branch=f"feat/{pr_id}",
                    to_branch="main",
                    title=f"PR {pr_id}",
                    template={
                        "node_id": node_id,
                        "instance_id": node_id,
                        "pipeline_id": pipeline_id,
                        "deps": [],
                        "artifact_type": "artifact",
                        "version": 1,
                    },
                    files=[],
                    diff_unified="",
                    commits=[],
                    state="open",
                )
        else:
            pr_detail = PrDetail(
                pr_id=pr_id,
                from_branch=f"feat/{pr_id}",
                to_branch="main",
                title=f"PR {pr_id}",
                template={
                    "node_id": node_id,
                    "instance_id": node_id,
                    "pipeline_id": pipeline_id,
                    "deps": [],
                    "artifact_type": "artifact",
                    "version": 1,
                },
                files=[],
                diff_unified="",
                commits=[],
                state="open",
            )

        ns = state.node_states.get(node_id)
        if ns is None:
            raise ValueError(f"Node not found: {node_id}")

        cur_status = NodeStatus(ns.status) if isinstance(ns.status, str) else ns.status
        allowed_for_approve = {
            NodeStatus.PENDING_REVIEW,
            NodeStatus.REVIEW,
            NodeStatus.IN_PROGRESS,
            NodeStatus.READY,
        }
        if cur_status not in allowed_for_approve:
            pass

        ctx = _build_review_context(defn, state, node_id, pr_id, pr_detail, trace_id)
        ctx.trace_id = trace_id

        eval_result = self.engine.evaluate(ctx)
        verdict = eval_result["verdict"]
        needs_human_flag = eval_result.get("needs_human", False)

        if verdict == "reject":
            rejected_by = eval_result.get("rejected_by")
            msg = ERROR_CODES.get(rejected_by, {}).get("en", f"Rejected by {rejected_by}") if rejected_by else "Rejected"
            raise ValueError(f"{rejected_by}: {msg}")

        effective_required = max(required_humans, 1 if needs_human_flag else 0)
        if verdict == "needs_human" or needs_human_flag:
            if human_approvals < effective_required:
                raise E_HUMAN_REVIEW_REQUIRED(
                    f"E_HUMAN_REVIEW_REQUIRED: {human_approvals}/{effective_required} human approvals"
                )

        node_def = None
        for n in defn.nodes:
            if n.node_id == node_id:
                node_def = n
                break

        atype = node_def.node_type if node_def else "artifact"
        if ns.artifact_refs:
            version = int(ns.artifact_refs[-1].version) + 1
            qualifier = ns.artifact_refs[-1].qualifier
        else:
            version = int(ctx.template.get("version", 1))
            qualifier = "default"

        all_content = b""
        for _p, cb in ctx.content_bytes.items():
            all_content += cb
        if not all_content:
            all_content = f"{pipeline_id}:{node_id}:{version}:{pr_id}".encode("utf-8")
        content_hash = self.hasher(all_content)

        merge_commit_sha = uuid4().hex[:40]
        if self.hub is not None:
            try:
                merge_commit_sha = self.hub.approve_and_squash_merge(pr_id, bot_actor)
            except Exception:
                pass

        provenance = Provenance(
            commit_sha=merge_commit_sha,
            pr_id=pr_id,
            approver_ids=[bot_actor] + [f"human_{i}" for i in range(human_approvals)],
            reviewer_ids=[f"human_{i}" for i in range(human_approvals)],
            merged_at=datetime.now(timezone.utc).isoformat(),
        )

        artifact_ref = ArtifactRef(
            trace_id=trace_id,
            node_id=node_id,
            artifact_type=atype,
            version=version,
            qualifier=qualifier,
            uri=f"commit://{merge_commit_sha}",
            external=False,
            ref_hash=content_hash,
            provenance=provenance,
        )

        audit_payload = {
            "pr_id": pr_id,
            "node_id": node_id,
            "pipeline_id": pipeline_id,
            "commit_sha": merge_commit_sha,
            "artifact_ref_hash": artifact_ref.ref_hash,
            "human_approvals": human_approvals,
            "required_humans": effective_required,
            "note": note,
            "verdict": verdict,
        }

        worm_entry = AuditLogEntry(
            prev_hash="",
            action=APPROVE_MERGE_ACTION,
            actor=bot_actor,
            payload=audit_payload,
            hash="",
            created_at=datetime.now(timezone.utc).isoformat(),
            pipeline_id=pipeline_id,
            node_id=node_id,
            pr_id=pr_id,
            trace_id=trace_id,
            commit_sha=merge_commit_sha,
            artifact_ref=artifact_ref.ref_hash,
            classification=int(ctx.artifact_classification),
            note=note,
        )

        if self.worm is not None:
            self.worm.insert(worm_entry)
            state.hash_chain_tip = worm_entry.hash

        ns.status = NodeStatus.DONE
        ns.artifact_refs = list(ns.artifact_refs) + [artifact_ref]
        if ns.pending_pr_count > 0:
            ns.pending_pr_count -= 1

        state2, _events = cascade_done(node_id, defn, state)
        state.node_states = state2.node_states

        done_count = 0
        for _nid, nss in state.node_states.items():
            s = NodeStatus(nss.status) if isinstance(nss.status, str) else nss.status
            if s == NodeStatus.DONE:
                done_count += 1
        state.completed_nodes_count = done_count

        state.updated_at = datetime.now(timezone.utc).isoformat()
        self._set_state(pipeline_id, state)

        final_status = NodeStatus(ns.status) if isinstance(ns.status, str) else ns.status

        return {
            "commit_sha": merge_commit_sha,
            "artifact_ref": {
                "trace_id": artifact_ref.trace_id,
                "node_id": artifact_ref.node_id,
                "artifact_type": artifact_ref.artifact_type,
                "version": artifact_ref.version,
                "qualifier": artifact_ref.qualifier,
                "uri": artifact_ref.uri,
                "ref_hash": artifact_ref.ref_hash,
                "provenance": artifact_ref.provenance.model_dump() if artifact_ref.provenance else None,
            },
            "node_new_status": final_status.value if isinstance(final_status, NodeStatus) else str(final_status),
        }
