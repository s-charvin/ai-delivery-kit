from __future__ import annotations

import json
from pathlib import Path

import pytest

from mcp.loop_registry import LoopRegistry


def _seed_req(tmp_path: Path, req_id: str = "req-loop-mcp") -> Path:
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
    (req_root / "status.json").write_text(
        json.dumps(
            {
                "requirement_id": req_id,
                "updated_at": "2026-01-01T00:00:00Z",
                "sub_requirements": {
                    "SR-001": {
                        "status": "tasks_ready",
                        "ui_bearing": False,
                        "design_approved": True,
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    return req_root


def test_intervene_resume_writes_audit(tmp_path: Path):
    req_root = _seed_req(tmp_path)
    reg = LoopRegistry(data_dir=tmp_path / "loop-data")
    started = reg.start(str(req_root), repo_root=str(tmp_path))
    pipeline_id = started["pipeline_id"]

    with pytest.raises(ValueError, match="resume requires"):
        reg.intervene(pipeline_id, "resume", reason="")

    out = reg.intervene(pipeline_id, "resume", reason="operator cleared stall")
    assert out["audit"]["action"] == "resume"
    assert out["audit"]["reason"] == "operator cleared stall"

    reg.stop(pipeline_id)


def test_intervene_approve_overbudget_requires_reason(tmp_path: Path):
    req_root = _seed_req(tmp_path)
    reg = LoopRegistry(data_dir=tmp_path / "loop-data2")
    started = reg.start(str(req_root), repo_root=str(tmp_path))
    pipeline_id = started["pipeline_id"]

    with pytest.raises(ValueError, match="approve_overbudget requires"):
        reg.intervene(pipeline_id, "approve_overbudget", reason="")

    out = reg.intervene(pipeline_id, "approve_overbudget", reason="CFO approved")
    assert out["status"]["overbudget_approved"] is True
    reg.stop(pipeline_id)
