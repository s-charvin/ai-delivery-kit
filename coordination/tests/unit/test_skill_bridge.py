from __future__ import annotations

import json
from pathlib import Path

import pytest

from orchestration.models import NodeStatus
from orchestration.skill_bridge import (
    EXECUTION_SEGMENT_STATUSES,
    SKILL_TO_NODE_STATUS,
    SkillBridgeError,
    flush_back,
    load_requirement,
    node_status_to_skill_status,
    skill_status_to_node_status,
)


def test_skill_to_node_mapping_is_frozen():
  expected = {
      "tasks_ready": NodeStatus.READY,
      "in_dev": NodeStatus.IN_PROGRESS,
      "merged": NodeStatus.DONE,
      "blocked_verification_failure": NodeStatus.BLOCKED,
  }
  for skill, node in expected.items():
      assert skill_status_to_node_status(skill) == node


def test_unknown_skill_status_raises():
    with pytest.raises(SkillBridgeError):
        skill_status_to_node_status("not_a_real_status")


def test_node_to_skill_flush_only_execution_segment():
    assert node_status_to_skill_status(NodeStatus.IN_PROGRESS) == "in_dev"
    assert node_status_to_skill_status(NodeStatus.DONE) == "merged"
    assert node_status_to_skill_status(NodeStatus.READY) is None
    assert (
        node_status_to_skill_status(
            NodeStatus.BLOCKED, prior_skill_status="blocked_merge_conflict"
        )
        == "blocked_merge_conflict"
    )


def test_load_and_flush_back_round_trip(tmp_path: Path):
    req_id = "req-bridge-test"
    req_root = tmp_path / ".ai-delivery" / "requirements" / req_id
    req_root.mkdir(parents=True)
    (req_root / "dependency-graph.json").write_text(
        json.dumps(
            {
                "version": 1,
                "requirement_id": req_id,
                "nodes": [{"subreq_id": "SR-001", "depends_on": [], "blocks": []}],
                "edges": [],
            }
        ),
        encoding="utf-8",
    )
    status = {
        "requirement_id": req_id,
        "updated_at": "2026-01-01T00:00:00Z",
        "sub_requirements": {
            "SR-001": {
                "status": "in_dev",
                "detail": None,
                "blocked_from_status": None,
                "blocker_scope": None,
                "resume_target_status": None,
                "ui_bearing": False,
                "design_approved": True,
                "notes": None,
            }
        },
    }
    (req_root / "status.json").write_text(json.dumps(status, indent=2), encoding="utf-8")

    _defn, state, ctx = load_requirement(req_root, repo_root=tmp_path)
    assert state.node_states["SR-001"].status == NodeStatus.IN_PROGRESS

    state.node_states["SR-001"].status = NodeStatus.DONE
    result = flush_back(state, ctx, run_reconcile=False)
    assert result["updated_subreqs"] == ["SR-001"]

    saved = json.loads((req_root / "status.json").read_text(encoding="utf-8"))
    assert saved["sub_requirements"]["SR-001"]["status"] == "merged"
    assert saved["sub_requirements"]["SR-001"]["status"] in EXECUTION_SEGMENT_STATUSES


def test_flush_back_does_not_touch_spec_segment(tmp_path: Path):
    req_id = "req-spec-segment"
    req_root = tmp_path / ".ai-delivery" / "requirements" / req_id
    req_root.mkdir(parents=True)
    (req_root / "dependency-graph.json").write_text(
        json.dumps(
            {
                "version": 1,
                "requirement_id": req_id,
                "nodes": [{"subreq_id": "SR-001", "depends_on": [], "blocks": []}],
                "edges": [],
            }
        ),
        encoding="utf-8",
    )
    status = {
        "requirement_id": req_id,
        "updated_at": "2026-01-01T00:00:00Z",
        "sub_requirements": {
            "SR-001": {
                "status": "spec_ready",
                "ui_bearing": False,
                "design_approved": True,
            }
        },
    }
    (req_root / "status.json").write_text(json.dumps(status), encoding="utf-8")

    _defn, state, ctx = load_requirement(req_root, repo_root=tmp_path)
    assert state.node_states["SR-001"].status == NodeStatus.BLOCKED
    # READY in pipeline == tasks_ready on skill side; must not be flushed as in_dev.
    state.node_states["SR-001"].status = NodeStatus.READY
    result = flush_back(state, ctx, run_reconcile=False)
    assert result["updated_subreqs"] == []

    saved = json.loads((req_root / "status.json").read_text(encoding="utf-8"))
    assert saved["sub_requirements"]["SR-001"]["status"] == "spec_ready"


def test_all_skill_statuses_have_node_mapping():
    for skill in list(SKILL_TO_NODE_STATUS):
        assert skill_status_to_node_status(skill) is not None
