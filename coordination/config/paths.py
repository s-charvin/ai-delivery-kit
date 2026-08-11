"""Canonical artifact-path resolver for the coordination/ Python engine.

This module intentionally does NOT import from the skill layer
(``.agents/...``). It reads the *same* ``project-binding.json`` layout
contract so both sides agree on artifact locations. If the file is missing
(e.g. in engine unit tests) it falls back to an embedded copy of the
default layout identical to ``scripts/layout.py``.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

DEFAULT_AI_DELIVERY_PATH = ".ai-delivery"

DEFAULT_LAYOUT: dict = {
    "requirement_root": "requirements/{req_id}",
    "sub_requirement_dir": "requirements/{req_id}/sub-requirements/{sr_id}",
    "requirement_artifacts": {
        "status": "requirements/{req_id}/status.json",
        "requirement": "requirements/{req_id}/requirement.md",
        "breakdown_summary": "requirements/{req_id}/breakdown-summary.md",
        "global_rules": "requirements/{req_id}/global-rules.md",
        "dependency_graph": "requirements/{req_id}/dependency-graph.json",
        "progress": "requirements/{req_id}/progress.md",
        "todo": "requirements/{req_id}/todo.md",
        "delivery_report": "requirements/{req_id}/delivery-report.md",
    },
    "sub_requirement_artifacts": {
        "requirement_slice": "requirements/{req_id}/sub-requirements/{sr_id}/requirement-slice.md",
        "decisions": "requirements/{req_id}/sub-requirements/{sr_id}/decisions.md",
        "readme": "requirements/{req_id}/sub-requirements/{sr_id}/README.md",
        "traceability": "requirements/{req_id}/sub-requirements/{sr_id}/traceability.json",
        "design": "requirements/{req_id}/sub-requirements/{sr_id}/design.md",
        "verification": "requirements/{req_id}/sub-requirements/{sr_id}/verification.md",
        "spec": "requirements/{req_id}/sub-requirements/{sr_id}/spec/spec.md",
        "plan": "requirements/{req_id}/sub-requirements/{sr_id}/spec/plan.md",
        "tasks": "requirements/{req_id}/sub-requirements/{sr_id}/spec/tasks.md",
        "ui_contract_index": "requirements/{req_id}/sub-requirements/{sr_id}/contracts/ui-contract-index.json",
        "manifest": "requirements/{req_id}/sub-requirements/{sr_id}/archive/{ts}/MANIFEST.json",
    },
}


def _find_binding(repo_root: Path | str) -> Path | None:
    """Locate project-binding.json (see layout.py for rationale)."""
    root = Path(repo_root)
    default_pb = root / DEFAULT_AI_DELIVERY_PATH / "meta" / "project-binding.json"
    if default_pb.exists():
        return default_pb
    for child in root.iterdir():
        if child.is_dir():
            cand = child / "meta" / "project-binding.json"
            if cand.exists():
                return cand
    return None


def _read_binding(repo_root: Path | str) -> dict | None:
    pb = _find_binding(repo_root)
    if pb is None:
        return None
    try:
        data = json.loads(pb.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def load_layout(repo_root: Path | str) -> dict:
    data = _read_binding(repo_root)
    if isinstance(data, dict) and isinstance(data.get("layout"), dict):
        return data["layout"]
    return dict(DEFAULT_LAYOUT)


def ai_delivery_path(repo_root: Path | str) -> Path:
    data = _read_binding(repo_root)
    if isinstance(data, dict):
        p = data.get("ai_delivery_path")
        if isinstance(p, str) and p:
            return Path(repo_root) / p
    return Path(repo_root) / DEFAULT_AI_DELIVERY_PATH


def _fmt(template: str, req_id: str, sr_id: str | None, unit_id: str | None, ts: str | None) -> str:
    return template.format(req_id=req_id, sr_id=sr_id, unit_id=unit_id, ts=ts)


def resolve(
    repo_root: Path | str,
    kind: str,
    req_id: str,
    sr_id: str | None = None,
    unit_id: str | None = None,
    ts: str | None = None,
) -> Path:
    layout = load_layout(repo_root)
    req_map = layout.get("requirement_artifacts", {})
    sub_map = layout.get("sub_requirement_artifacts", {})
    if kind in req_map:
        rel = _fmt(req_map[kind], req_id, sr_id, unit_id, ts)
    elif kind in sub_map:
        rel = _fmt(sub_map[kind], req_id, sr_id, unit_id, ts)
    else:
        raise KeyError(f"unknown artifact kind: {kind!r}")
    return ai_delivery_path(repo_root) / rel


def normalize_text(text: str) -> str:
    out_lines = []
    for line in text.replace("\r\n", "\n").split("\n"):
        out_lines.append(line.rstrip())
    return "\n".join(out_lines).rstrip("\n") + "\n"


def canonical_sha256(text: str) -> str:
    return hashlib.sha256(normalize_text(text).encode("utf-8")).hexdigest()
