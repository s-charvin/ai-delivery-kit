"""Task 2 核心数据模型 + 错误码 + 工具函数 验收测试 (TR-2.1 ~ TR-2.5)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from freezegun import freeze_time

from audit.models import AuditLogEntry
from config.constants import (
    CONFIDENTIAL,
    ERROR_CODES,
    INTERNAL,
    PUBLIC,
    RESTRICTED,
    TRANSITION_MATRIX,
    VALID_TRANSITIONS,
)
from orchestration.models import (
    Addendum,
    ArtifactRef,
    ClassificationLevel,
    NodeState,
    NodeStatus,
    PipelineState,
    PipelineStatus,
    Provenance,
    RoleInstance,
)
from utils.hashing import audit_entry_hash, hash_chain_validate
from utils.tokens import check_token_scope, create_session_token, verify_session_token


def test_tr2_1_pipeline_state_roundtrip():
    """TR-2.1 PipelineState roundtrip JSON 序列化/反序列化."""
    provenance = Provenance(
        commit_sha="abc123def456",
        pr_id="PR-42",
        approver_ids=["u1", "u2"],
        reviewer_ids=["r1"],
        merged_at="2025-06-01T12:00:00Z",
    )

    artifact_ref = ArtifactRef(
        node_id="node-1",
        artifact_type="OpenSpec",
        version=2,
        qualifier="default",
        uri="/hub/specs/node-1/v2",
        external=False,
        ref_hash="sha256:abcdef0123456789",
        trace_id="a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6",
        provenance=provenance,
    )

    addendum = Addendum(
        id="add-001",
        version=1,
        change_class="must",
        incompatible_with=["node-3"],
        impact_claim=["node-2"],
        diff_hash="sha256:deadbeefcafebabe",
        author="user-1",
        created_at="2025-06-02T10:00:00Z",
    )

    node_state = NodeState(
        node_id="node-1",
        status=NodeStatus.DONE,
        artifact_refs=[artifact_ref],
        downstream_acked_ids=["node-2", "node-3"],
        addenda=[addendum],
        change_state="soft_acked",
        pending_pr_count=1,
        locked_by=None,
    )

    full_data = {
        "pipeline_id": "pipe-2025-001",
        "version": 3,
        "status": PipelineStatus.COMPLETED,
        "created_at": "2025-05-01T00:00:00Z",
        "updated_at": "2025-06-05T18:30:00Z",
        "node_states": {"node-1": node_state.model_dump()},
        "cascade_pending": [
            {"from_node": "node-1", "to_node": "node-2", "type": "soft_change"}
        ],
        "profile_id": "profile-fullstack",
        "classification": ClassificationLevel.CONFIDENTIAL,
        "completed_nodes_count": 8,
        "hash_chain_tip": "sha256:chain_tip_hash",
        "checkpoint_id": "cp-2025-06-05",
    }

    obj = PipelineState(**full_data)
    obj_dict = obj.model_dump()
    j = json.dumps(obj_dict, sort_keys=True)
    obj2 = PipelineState.model_validate_json(j)
    obj2_dict = obj2.model_dump()
    assert json.dumps(obj2_dict, sort_keys=True) == json.dumps(obj_dict, sort_keys=True)


def test_tr2_2_valid_invalid_transitions():
    """TR-2.2 合法/非法状态转移验证."""
    for (from_, to), tag in VALID_TRANSITIONS.items():
        assert TRANSITION_MATRIX[from_][to] is True, (
            f"Valid transition {tag}: {from_} -> {to} should be True"
        )

    invalid_cases = [
        (NodeStatus.BLOCKED, NodeStatus.DONE),
        (NodeStatus.READY, NodeStatus.BLOCKED),
        (NodeStatus.DONE, NodeStatus.READY),
        (NodeStatus.DONE, NodeStatus.BLOCKED),
        (NodeStatus.CHANGED, NodeStatus.READY),
        (NodeStatus.DRAFT, NodeStatus.DONE),
        (NodeStatus.SKIPPED, NodeStatus.READY),
        (NodeStatus.DEPRECATED, NodeStatus.IN_PROGRESS),
        (NodeStatus.SUNSET, NodeStatus.READY),
        (NodeStatus.REVIEW, NodeStatus.BLOCKED),
        (NodeStatus.PENDING_REVIEW, NodeStatus.DONE),
        (NodeStatus.IN_PROGRESS, NodeStatus.DONE),
        (NodeStatus.CHANGED, NodeStatus.DONE),
        (NodeStatus.BLOCKED, NodeStatus.REVIEW),
    ]
    for from_, to in invalid_cases:
        assert TRANSITION_MATRIX[from_][to] is False, (
            f"Invalid transition {from_} -> {to} should be False"
        )


def test_tr2_3_hash_chain_validate():
    """TR-2.3 hash_chain_validate 破坏检测."""
    a0, actor0, p0 = "node_create", "bot-1", {"k0": "v0"}
    a1, actor1, p1 = "submit", "bot-2", {"k1": "v1"}
    a3, actor3, p3 = "review", "hum-1", {"k3": "v3"}
    a4, actor4, p4 = "approve", "adm-1", {"k4": "v4"}

    h0 = audit_entry_hash("", a0, actor0, p0)
    h1 = audit_entry_hash(h0, a1, actor1, p1)
    h2_wrong = "sha256:WRONGWRONG"
    h3 = audit_entry_hash(h2_wrong, a3, actor3, p3)
    h4 = audit_entry_hash(h3, a4, actor4, p4)

    entries = [
        AuditLogEntry(
            pipeline_id="P1",
            action=a0,
            actor=actor0,
            payload=p0,
            created_at="2025-01-01T00:00:00Z",
            prev_hash="",
            hash=h0,
            trace_id="t0",
        ),
        AuditLogEntry(
            pipeline_id="P1",
            action=a1,
            actor=actor1,
            payload=p1,
            created_at="2025-01-01T00:01:00Z",
            prev_hash=h0,
            hash=h1,
            trace_id="t1",
        ),
        AuditLogEntry(
            pipeline_id="P1",
            action="tampered",
            actor="evil",
            payload={"bad": True},
            created_at="2025-01-01T00:02:00Z",
            prev_hash=h1,
            hash=h2_wrong,
            trace_id="t2",
        ),
        AuditLogEntry(
            pipeline_id="P1",
            action=a3,
            actor=actor3,
            payload=p3,
            created_at="2025-01-01T00:03:00Z",
            prev_hash=h2_wrong,
            hash=h3,
            trace_id="t3",
        ),
        AuditLogEntry(
            pipeline_id="P1",
            action=a4,
            actor=actor4,
            payload=p4,
            created_at="2025-01-01T00:04:00Z",
            prev_hash=h3,
            hash=h4,
            trace_id="t4",
        ),
    ]

    result = hash_chain_validate(entries)
    assert result == (False, 2), f"Expected (False, 2), got {result}"


def test_tr2_4_classification_and_clearance():
    """TR-2.4 ClassificationLevel 比较 + RoleInstance clearance."""
    assert PUBLIC < INTERNAL < CONFIDENTIAL < RESTRICTED
    assert (
        ClassificationLevel.PUBLIC
        < ClassificationLevel.INTERNAL
        < ClassificationLevel.CONFIDENTIAL
        < ClassificationLevel.RESTRICTED
    )

    role_internal = RoleInstance(
        instance_id="ri-1",
        role="server_impl",
        approvers=["bot-1"],
        clearance=INTERNAL,
    )
    role_confidential = RoleInstance(
        instance_id="ri-2",
        role="admin",
        approvers=["bot-2", "hum-1"],
        clearance=CONFIDENTIAL,
    )

    assert role_internal.can_access(CONFIDENTIAL) is False
    assert role_confidential.can_access(INTERNAL) is True
    assert role_internal.can_access(PUBLIC) is True
    assert role_confidential.can_access(RESTRICTED) is False


@freeze_time("2025-01-01T00:00:00")
def test_tr2_5_jwt_token():
    """TR-2.5 JWT token 测试."""
    secret = "test-secret"

    with pytest.raises(ValueError, match="E_TOKEN_EXPIRED"):
        expired_token = create_session_token(
            secret=secret,
            node_id="n1",
            allowed_tools=["submit_artifact"],
            expires_at_iso="2024-12-31T00:00:00",
        )
        verify_session_token(secret, expired_token)

    valid_token = create_session_token(
        secret=secret,
        node_id="n1",
        allowed_tools=["submit_artifact"],
        expires_at_iso="2025-12-31T00:00:00",
    )
    payload = verify_session_token(secret, valid_token)
    assert check_token_scope(payload, "submit_artifact") is True
    assert check_token_scope(payload, "cancel_pipeline") is False

    scope_token = create_session_token(
        secret=secret,
        node_id="n2",
        allowed_tools=["get_status"],
        expires_at_iso="2025-12-31T00:00:00",
    )
    payload2 = verify_session_token(secret, scope_token)
    assert check_token_scope(payload2, "submit_artifact") is False

    bad_token = "invalid.token.here"
    with pytest.raises(ValueError, match="E_TOKEN_SCOPE_MISMATCH"):
        verify_session_token(secret, bad_token)
