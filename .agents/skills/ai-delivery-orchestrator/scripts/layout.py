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


def file_sha256(path: Path) -> str | None:
    """canonical_sha256 of a file's contents, or None if unreadable."""
    try:
        return canonical_sha256(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError):
        return None


# --------------------------------------------------------------------------
# Layout detection + spec persistence (spec-kit living/flow-forward support)
# --------------------------------------------------------------------------

SPEC_KINDS = ("spec", "plan", "tasks")

DEFAULT_WORKFLOW_POLICY: dict = {
    "review_loop": {"max_rounds": 3},
    "spec_persistence": {
        "active": "living",
        "complete": "flow_forward",
        "living": {
            "source_of_truth": "spec/spec.md",
            "derived": ["spec/plan.md", "spec/tasks.md"],
            "on_drift": "downgrade_to_spec_ready",
        },
        "flow_forward": {"immutable_root": "archive", "change_requires": "new_requirement_dir"},
    },
    "verification_policy": {
        "required_at": ["merged", "archived"],
        "artifact": "verification.md",
        "required_sections": ["评审轮次记录", "验证命令与结果", "签署"],
    },
}


def is_new_layout(subreq_dir: Path | str) -> bool:
    """True when a sub-requirement has adopted the unified canonical layout.

    Shared by every validator so "new layout" is decided in exactly one place.
    Marker files: ``spec/spec.md``, ``design.md``, ``verification.md``.
    """
    d = Path(subreq_dir)
    return (
        (d / "spec" / "spec.md").is_file()
        or (d / "design.md").is_file()
        or (d / "verification.md").is_file()
    )


def load_workflow_policy(start: Path | str) -> dict:
    """Read workflow-policy.json by walking up to `.ai-delivery`, else defaults."""
    ad_dir = find_ai_delivery_dir(start)
    if ad_dir is not None:
        policy_path = ad_dir / "meta" / "workflow-policy.json"
        try:
            data = json.loads(policy_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            data = None
        if isinstance(data, dict):
            return data
    return dict(DEFAULT_WORKFLOW_POLICY)


def load_traceability(subreq_dir: Path | str) -> dict | None:
    try:
        data = json.loads((Path(subreq_dir) / "traceability.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def iter_spec_artifacts(traceability: dict | None) -> list[dict]:
    """Normalize the three accepted `spec_refs` shapes into artifact entries.

    Canonical shape (preferred)::

        "spec_refs": {"tier": "...", "artifacts": [{kind, canonical_path,
                       derived_paths, content_sha256, sync_state}, ...]}

    Also accepted: a bare list of those entries, and the legacy
    ``{spec_path, plan_path, tasks_path}`` form (which carries no hash, so it
    simply yields entries without ``content_sha256`` and is skipped by the
    drift check).
    """
    if not isinstance(traceability, dict):
        return []
    refs = traceability.get("spec_refs")
    if isinstance(refs, list):
        return [e for e in refs if isinstance(e, dict)]
    if not isinstance(refs, dict):
        return []
    artifacts = refs.get("artifacts")
    if isinstance(artifacts, list):
        return [e for e in artifacts if isinstance(e, dict)]
    legacy: list[dict] = []
    for kind in SPEC_KINDS:
        rel = refs.get(f"{kind}_path")
        if isinstance(rel, str) and rel:
            legacy.append({"kind": kind, "canonical_path": rel})
    return legacy


def _resolve_canonical(subreq_dir: Path, rel: str) -> Path:
    """Resolve a recorded canonical_path against the sub-requirement dir.

    Recorded paths may be written relative to the sub-requirement itself
    (``spec/spec.md``) or include the ``sub-requirements/<SR>/`` prefix; both
    resolve to the same file.
    """
    p = Path(rel)
    direct = subreq_dir / p
    if direct.is_file():
        return direct
    marker = "sub-requirements/"
    posix = p.as_posix()
    if marker in posix:
        tail = posix.split(marker, 1)[1]
        parts = tail.split("/", 1)
        if len(parts) == 2:
            cand = subreq_dir / parts[1]
            if cand.is_file():
                return cand
    return direct


def spec_drift(subreq_dir: Path | str) -> list[str]:
    """Detect living-spec drift: recorded content_sha256 != on-disk hash.

    Returns human-readable messages (empty when in sync). Entries without a
    recorded hash are skipped — nothing recorded means nothing to drift from.
    """
    d = Path(subreq_dir)
    entries = iter_spec_artifacts(load_traceability(d))
    messages: list[str] = []
    for entry in entries:
        kind = entry.get("kind")
        if kind not in SPEC_KINDS:
            continue
        recorded = entry.get("content_sha256")
        rel = entry.get("canonical_path")
        if not isinstance(recorded, str) or not recorded or not isinstance(rel, str):
            continue
        target = _resolve_canonical(d, rel)
        if not target.is_file():
            messages.append(f"{kind}: recorded artifact missing on disk ({rel})")
            continue
        actual = file_sha256(target)
        if actual is None:
            continue
        if actual != recorded:
            messages.append(f"{kind}: {rel} recorded {recorded[:8]} != current {actual[:8]}")
    return messages


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

    # 4) is_new_layout markers
    with tempfile.TemporaryDirectory() as td:
        sr = Path(td) / "SR-001"
        (sr / "spec").mkdir(parents=True)
        assert not is_new_layout(sr)
        (sr / "spec" / "spec.md").write_text("# spec\n", encoding="utf-8")
        assert is_new_layout(sr)

    # 5) spec_drift: in-sync clean, cosmetic edit clean, real edit detected
    with tempfile.TemporaryDirectory() as td:
        sr = Path(td) / "SR-001"
        (sr / "spec").mkdir(parents=True)
        spec_file = sr / "spec" / "spec.md"
        spec_file.write_text("# spec\nbody\n", encoding="utf-8")
        plan_file = sr / "spec" / "plan.md"
        plan_file.write_text("# plan\n", encoding="utf-8")
        (sr / "traceability.json").write_text(
            json.dumps(
                {
                    "spec_refs": {
                        "tier": "native",
                        "artifacts": [
                            {
                                "kind": "spec",
                                "canonical_path": "spec/spec.md",
                                "content_sha256": canonical_sha256("# spec\nbody\n"),
                                "sync_state": "synced",
                            },
                            {
                                "kind": "plan",
                                "canonical_path": "sub-requirements/SR-001/spec/plan.md",
                                "content_sha256": canonical_sha256("# plan\n"),
                                "sync_state": "synced",
                            },
                        ],
                    }
                }
            ),
            encoding="utf-8",
        )
        assert spec_drift(sr) == [], spec_drift(sr)
        # cosmetic trailing whitespace must NOT be reported as drift
        spec_file.write_text("# spec\nbody   \n\n", encoding="utf-8")
        assert spec_drift(sr) == [], spec_drift(sr)
        # a real content change must be reported
        spec_file.write_text("# spec\nbody changed\n", encoding="utf-8")
        drift = spec_drift(sr)
        assert len(drift) == 1 and drift[0].startswith("spec:"), drift

    # 6) legacy spec_refs shape carries no hash -> no drift, no crash
    with tempfile.TemporaryDirectory() as td:
        sr = Path(td) / "SR-001"
        sr.mkdir(parents=True)
        (sr / "spec.md").write_text("# spec\n", encoding="utf-8")
        (sr / "traceability.json").write_text(
            json.dumps({"spec_refs": {"tier": "native", "spec_path": "spec.md"}}),
            encoding="utf-8",
        )
        assert spec_drift(sr) == []
        assert iter_spec_artifacts(load_traceability(sr))[0]["kind"] == "spec"

    # 7) workflow policy falls back to defaults outside a governed repo
    with tempfile.TemporaryDirectory() as td:
        policy = load_workflow_policy(Path(td))
        assert policy["review_loop"]["max_rounds"] == 3
        assert policy["spec_persistence"]["active"] == "living"

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
