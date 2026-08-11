#!/usr/bin/env python3
"""Canonical artifact-layout resolver for ai-delivery-kit.

Single source of truth for *where* governed artifacts live. Both the
skill-layer orchestrator (reconcile-delivery.py) and, by reading the same
`project-binding.json` layout section, the coordination/ Python engine use
this contract.

The layout is declared once in `.ai-delivery/meta/project-binding.json`
under the `layout` key. Every path below is *relative to* `ai_delivery_path`
(also from that file, default `.ai-delivery`).

Artifact kinds come in two scopes:
  * requirement-level   (no sub-requirement): status, requirement, ...
  * sub-requirement-level: spec, plan, tasks, design, verification, ...

Phase 0 only introduces this module + the layout contract. Nothing else in
the kit imports it yet; Phase 1 onwards wires reconcile / validators to it.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

# Fallback layout used when project-binding.json is absent (e.g. unit tests).
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

DEFAULT_AI_DELIVERY_PATH = ".ai-delivery"


def find_ai_delivery_dir(start: Path | str) -> Path | None:
    """Walk up from `start` to locate the `.ai-delivery` directory.

    Used by callers that only have a requirement/sub-requirement path and need
    the governed root (which holds meta/project-binding.json).
    """
    p = Path(start)
    for cand in [p, *p.parents]:
        if (cand / "meta" / "project-binding.json").exists():
            return cand
    return None


def _find_binding(repo_root: Path) -> Path | None:
    """Locate project-binding.json.

    The meta dir is always ``<root>/<ai_delivery_path>/meta/``, but
    ``ai_delivery_path`` may be overridden, so probe the default location
    plus one level of immediate subdirectories (bounded, no deep walk).
    """
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


def _read_binding(repo_root: Path) -> dict | None:
    pb = _find_binding(repo_root)
    if pb is None:
        return None
    try:
        data = json.loads(pb.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def load_layout(repo_root: Path) -> dict:
    """Read the `layout` section from project-binding.json, else fallback."""
    data = _read_binding(repo_root)
    if isinstance(data, dict) and isinstance(data.get("layout"), dict):
        return data["layout"]
    return dict(DEFAULT_LAYOUT)


def ai_delivery_path(repo_root: Path) -> Path:
    data = _read_binding(repo_root)
    if isinstance(data, dict):
        p = data.get("ai_delivery_path")
        if isinstance(p, str) and p:
            return Path(repo_root) / p
    return Path(repo_root) / DEFAULT_AI_DELIVERY_PATH


def _fmt(template: str, req_id: str, sr_id: str | None, unit_id: str | None, ts: str | None) -> str:
    # str.format tolerates extra kwargs, so always pass all four.
    return template.format(req_id=req_id, sr_id=sr_id, unit_id=unit_id, ts=ts)


def artifact_path(
    repo_root: Path | str,
    kind: str,
    req_id: str,
    sr_id: str | None = None,
    unit_id: str | None = None,
    ts: str | None = None,
) -> Path:
    """Resolve the canonical on-disk path of an artifact kind.

    `kind` must be one of the keys in DEFAULT_LAYOUT's two artifact maps.
    Requirement-level kinds ignore sr_id/unit_id/ts; sub-requirement kinds
    require sr_id (and ts for `manifest`).
    """
    layout = load_layout(Path(repo_root))
    req_map = layout.get("requirement_artifacts", {})
    sub_map = layout.get("sub_requirement_artifacts", {})
    if kind in req_map:
        rel = _fmt(req_map[kind], req_id, sr_id, unit_id, ts)
    elif kind in sub_map:
        rel = _fmt(sub_map[kind], req_id, sr_id, unit_id, ts)
    else:
        raise KeyError(f"unknown artifact kind: {kind!r}")
    return ai_delivery_path(Path(repo_root)) / rel


def requirement_dir(repo_root: Path | str, req_id: str) -> Path:
    layout = load_layout(Path(repo_root))
    rel = _fmt(layout["requirement_root"], req_id, None, None, None)
    return ai_delivery_path(Path(repo_root)) / rel


def sub_requirement_dir(repo_root: Path | str, req_id: str, sr_id: str) -> Path:
    layout = load_layout(Path(repo_root))
    rel = _fmt(layout["sub_requirement_dir"], req_id, sr_id, None, None)
    return ai_delivery_path(Path(repo_root)) / rel


def normalize_text(text: str) -> str:
    """Normalize for stable hashing: CRLF->LF, strip trailing whitespace/EOF.

    Used by spec-kit persistence hash-drift checks so cosmetic edits don't
    trigger false re-generation. Applied identically on both skill and engine
    sides (see coordination/config/paths.py).
    """
    out_lines = []
    for line in text.replace("\r\n", "\n").split("\n"):
        out_lines.append(line.rstrip())
    return "\n".join(out_lines).rstrip("\n") + "\n"


def canonical_sha256(text: str) -> str:
    return hashlib.sha256(normalize_text(text).encode("utf-8")).hexdigest()


def _selftest() -> int:
    import tempfile

    # 1) default layout works without project-binding.json
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        p = artifact_path(root, "status", "REQ-1")
        assert p == root / ".ai-delivery" / "requirements" / "REQ-1" / "status.json", p
        p = artifact_path(root, "spec", "REQ-1", sr_id="SR-001")
        assert p == root / ".ai-delivery" / "requirements" / "REQ-1" / "sub-requirements" / "SR-001" / "spec" / "spec.md", p
        # ts placeholder
        m = artifact_path(root, "manifest", "REQ-1", sr_id="SR-001", ts="2026-08-11T000000Z")
        assert m.name == "MANIFEST.json" and "2026-08-11T000000Z" in str(m), m
        # requirement dir + sub dir
        assert requirement_dir(root, "REQ-1").name == "REQ-1"
        assert sub_requirement_dir(root, "REQ-1", "SR-001").name == "SR-001"

    # 2) project-binding.json layout overrides + base dir honored
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        meta = root / "governed" / "meta"
        meta.mkdir(parents=True)
        (meta / "project-binding.json").write_text(
            json.dumps(
                {
                    "ai_delivery_path": "governed",
                    "layout": {
                        "requirement_root": "requirements/{req_id}",
                        "sub_requirement_dir": "requirements/{req_id}/sub-requirements/{sr_id}",
                        "requirement_artifacts": {"status": "requirements/{req_id}/status.json"},
                        "sub_requirement_artifacts": {"spec": "requirements/{req_id}/sub-requirements/{sr_id}/spec/spec.md"},
                    },
                }
            ),
            encoding="utf-8",
        )
        p = artifact_path(root, "spec", "REQ-9", sr_id="SR-002")
        assert p == root / "governed" / "requirements" / "REQ-9" / "sub-requirements" / "SR-002" / "spec" / "spec.md", p

    # 3) canonical_sha256 is stable across cosmetic whitespace
    a = canonical_sha256("line1\nline2  \n")
    b = canonical_sha256("line1\nline2\n")
    assert a == b, (a, b)
    assert len(a) == 64

    print("layout.py selftest OK")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selftest", action="store_true", help="Run built-in assertions")
    args = parser.parse_args()
    if args.selftest:
        return _selftest()
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
