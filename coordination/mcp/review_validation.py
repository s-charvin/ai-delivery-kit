from __future__ import annotations

import json
import re

from orchestration.models import NodeState, PipelineDefinition

# SHA-256 hex digest: 64 lowercase hex characters.
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

# Conservative secret patterns — enough to flag obvious leaks before human review.
# Not a complete scanner.
_SECRET_RE = re.compile(
    r"(AKIA[0-9A-Z]{16})"
    r"|(aws_secret_access_key\s*[=:]\s*['\"]?[A-Za-z0-9/+=]{40})"
    r"|(sk-[A-Za-z0-9]{20,})"
    r"|(gh[pousr]_[A-Za-z0-9]{20,})"
    r"|(-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----)"
    r"|(Bearer\s+[A-Za-z0-9._\-]{20,})",
    re.IGNORECASE,
)


def _required_fields_present(node_state: NodeState) -> bool:
    if not node_state.artifact_refs:
        return False
    for ref in node_state.artifact_refs:
        if not (
            ref.node_id
            and ref.artifact_type
            and ref.uri
            and ref.ref_hash
            and ref.trace_id
        ):
            return False
    return True


def _schema_valid(node_state: NodeState) -> bool:
    for ref in node_state.artifact_refs:
        if not isinstance(ref.version, int):
            return False
        if not isinstance(ref.uri, str):
            return False
        if not isinstance(ref.artifact_type, str):
            return False
    return True


def _ref_hashes_are_sha256(node_state: NodeState) -> bool:
    if not node_state.artifact_refs:
        return False
    return all(_SHA256_RE.match(ref.ref_hash or "") for ref in node_state.artifact_refs)


def _contains_secret(node_state: NodeState, defn: PipelineDefinition | None) -> bool:
    blob = json.dumps(
        {
            "node_state": node_state.model_dump(),
            "def": defn.model_dump() if defn is not None else {},
        },
        default=str,
    )
    return bool(_SECRET_RE.search(blob))


def review_artifact_checks(
    node_state: NodeState,
    defn: PipelineDefinition | None = None,
) -> dict[str, str]:
    """Minimal real validation for an artifact PR.

    Each gate returns "pass" or "fail". Routing is the caller's concern; this
    function only reports the checks.
    """
    return {
        "required_fields": "pass" if _required_fields_present(node_state) else "fail",
        "schema": "pass" if _schema_valid(node_state) else "fail",
        "sha256": "pass" if _ref_hashes_are_sha256(node_state) else "fail",
        "secret_scan": "pass" if not _contains_secret(node_state, defn) else "fail",
    }


def review_artifact_pr_result(
    node_state: NodeState,
    defn: PipelineDefinition | None = None,
    pipeline_id: str = "",
    pr_id: str = "",
) -> dict:
    checks = review_artifact_checks(node_state, defn)
    all_pass = all(v == "pass" for v in checks.values())
    summary = (
        "all checks pass; routed to human reviewer"
        if all_pass
        else "check failures detected; routed to human reviewer"
    )
    return {
        "verdict": "needs_human",
        "checks": checks,
        "needs_human": True,
        "summary": summary,
    }
