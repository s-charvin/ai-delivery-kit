from __future__ import annotations

import re
from typing import Any
from uuid import uuid4

from audit.engine import ReviewContext, RuleEngine
from orchestration.models import ClassificationLevel
from repo.hub import PrDetail


_URL_PATTERN = re.compile(r"https?://[^\s\"'>)]+")


def _count_diff_lines(diff_unified: str) -> tuple[int, int]:
    added = 0
    deleted = 0
    for line in (diff_unified or "").splitlines():
        if line.startswith("+") and not line.startswith("+++"):
            added += 1
        elif line.startswith("-") and not line.startswith("---"):
            deleted += 1
    return added, deleted


def _extract_external_refs(diff_unified: str, content_bytes: dict[str, bytes]) -> list[str]:
    refs: list[str] = []
    for line in (diff_unified or "").splitlines():
        found = _URL_PATTERN.findall(line)
        refs.extend(found)
    for content in content_bytes.values():
        try:
            text = content.decode("utf-8", errors="ignore")
            found = _URL_PATTERN.findall(text)
            refs.extend(found)
        except Exception:
            pass
    return refs


def _build_context_from_state(
    pipeline_def: Any,
    pipeline_state: Any,
    node_id: str,
    pr_id: str,
    pr_detail: PrDetail,
    content_bytes: dict[str, bytes] | None = None,
    role_instance_id: str | None = None,
    token_payload: dict | None = None,
    clearance: ClassificationLevel | None = None,
    skill: Any | None = None,
    submitter_role: str | None = None,
    external_repo_whitelist: list[str] | None = None,
    trace_id: str | None = None,
) -> ReviewContext:
    template = pr_detail.template or {}
    content_bytes = content_bytes or {}

    node_def = None
    for n in pipeline_def.nodes:
        if n.node_id == node_id:
            node_def = n
            break

    node_type = node_def.node_type if node_def else "artifact"
    artifact_class_raw = template.get("classification", 1)
    try:
        artifact_class = ClassificationLevel(int(artifact_class_raw))
    except Exception:
        artifact_class = ClassificationLevel.INTERNAL

    change_class = str(template.get("change_class", "compatible"))
    addendum_declared = bool(template.get("addendum_declared")) or (change_class == "addendum")

    diff_added, diff_deleted = _count_diff_lines(pr_detail.diff_unified or "")
    external_refs = _extract_external_refs(pr_detail.diff_unified or "", content_bytes)

    final_role_instance_id = role_instance_id or str(template.get("instance_id", node_id))
    final_token_payload = token_payload or {"sub": final_role_instance_id}
    final_clearance = clearance
    if final_clearance is None:
        try:
            final_clearance = ClassificationLevel(int(template.get("clearance", int(artifact_class))))
        except Exception:
            final_clearance = ClassificationLevel.INTERNAL
    final_submitter_role = submitter_role or str(template.get("submitter_role", node_type))
    final_trace_id = trace_id or uuid4().hex

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
        role_instance_id=final_role_instance_id,
        token_payload=final_token_payload,
        clearance=final_clearance,
        skill=skill,
        submitter_role=final_submitter_role,
        node_type=node_type,
        artifact_classification=artifact_class,
        change_class_declared=change_class,
        addendum_declared=addendum_declared,
        external_refs=external_refs,
        external_repo_whitelist=external_repo_whitelist or [],
        trace_id=final_trace_id,
    )


_ENGINE_SINGLETON: RuleEngine | None = None


def get_engine() -> RuleEngine:
    global _ENGINE_SINGLETON
    if _ENGINE_SINGLETON is None:
        _ENGINE_SINGLETON = RuleEngine()
    return _ENGINE_SINGLETON


def _run_review(
    pipeline_def: Any,
    pipeline_state: Any,
    node_id: str,
    pr_id: str,
    pr_detail: PrDetail,
    content_bytes: dict[str, bytes] | None = None,
    engine: RuleEngine | None = None,
    **kwargs: Any,
) -> dict:
    ctx = _build_context_from_state(
        pipeline_def=pipeline_def,
        pipeline_state=pipeline_state,
        node_id=node_id,
        pr_id=pr_id,
        pr_detail=pr_detail,
        content_bytes=content_bytes,
        **kwargs,
    )
    eng = engine or get_engine()
    return eng.evaluate(ctx)
