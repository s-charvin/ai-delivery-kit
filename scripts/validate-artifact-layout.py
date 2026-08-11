#!/usr/bin/env python3
"""Validate the unified artifact-layout contract for a requirement.

This is the single layout validator backing `docs/artifact-layout.md`. It is
deliberately **backward-compatible**: it inspects each sub-requirement and
detects whether it uses the *new* canonical layout (artifacts under
``spec/``, ``design.md``, ``verification.md``) or the *legacy* layout
(``spec.md`` / ``tasks.md`` at the sub-requirement root). New-layout rules are
only enforced on sub-requirements that have already adopted the new layout, so
repos bootstrapped before this contract keep validating cleanly.

Canonical artifact paths are resolved through the same ``layout`` contract as
the orchestrator (project-binding.json ``layout`` section); this script reads
it directly so it can also flag files sitting at the wrong location.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

# Reuse the same layout contract the orchestrator uses.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / ".agents" / "skills" / "ai-delivery-orchestrator" / "scripts"))
from layout import artifact_path, canonical_sha256  # noqa: E402

STATUS_ORDER = [
    "draft",
    "split_ready",
    "acceptance_frozen",
    "spec_ready",
    "plan_ready",
    "tasks_ready",
    "in_dev",
    "visual_acceptance_passed",
    "merged",
    "archived",
]


def _at_least(status: str, target: str) -> bool:
    try:
        return STATUS_ORDER.index(status) >= STATUS_ORDER.index(target)
    except ValueError:
        return False


def _detect_new_layout(subreq_dir: Path) -> bool:
    if (subreq_dir / "spec" / "spec.md").is_file():
        return True
    if (subreq_dir / "design.md").is_file():
        return True
    if (subreq_dir / "verification.md").is_file():
        return True
    return False


def _has_contracts(subreq_dir: Path) -> bool:
    return bool(list(subreq_dir.rglob("ui-contract.html")))


def validate_subreq(subreq_id: str, entry: dict, subreq_dir: Path) -> tuple[list[str], list[str]]:
    """Return (errors, warnings) for one sub-requirement."""
    errors: list[str] = []
    warnings: list[str] = []
    status = entry.get("status")
    if not isinstance(status, str):
        return errors, warnings

    new_layout = _detect_new_layout(subreq_dir)
    ui_bearing = bool(entry.get("ui_bearing")) or _has_contracts(subreq_dir)

    if new_layout:
        if _at_least(status, "spec_ready") and not (subreq_dir / "spec" / "spec.md").is_file():
            errors.append(f"[LAYOUT] {subreq_id}: status={status} (new layout) requires spec/spec.md")
        if _at_least(status, "plan_ready") and not (subreq_dir / "spec" / "plan.md").is_file():
            errors.append(f"[LAYOUT] {subreq_id}: status={status} (new layout) requires spec/plan.md")
        if _at_least(status, "tasks_ready") and not (subreq_dir / "spec" / "tasks.md").is_file():
            errors.append(f"[LAYOUT] {subreq_id}: status={status} (new layout) requires spec/tasks.md")
        if _at_least(status, "spec_ready") and not (subreq_dir / "design.md").is_file():
            errors.append(f"[LAYOUT] {subreq_id}: status={status} (new layout) requires design.md")
        if status in {"merged", "archived"} and not (subreq_dir / "verification.md").is_file():
            errors.append(f"[LAYOUT] {subreq_id}: status={status} requires verification.md")
        # Legacy files at the wrong (root) location in a new-layout sub-req.
        if (subreq_dir / "spec.md").is_file():
            warnings.append(f"[LAYOUT] {subreq_id}: legacy spec.md at root; move to spec/spec.md")
        if (subreq_dir / "tasks.md").is_file():
            warnings.append(f"[LAYOUT] {subreq_id}: legacy tasks.md at root; move to spec/tasks.md")
    else:
        # Legacy layout: only enforce what the legacy contract required.
        if _at_least(status, "spec_ready") and not (subreq_dir / "spec.md").is_file():
            errors.append(f"[LAYOUT] {subreq_id}: status={status} requires spec.md")
        if _at_least(status, "tasks_ready") and not (
            (subreq_dir / "tasks.md").is_file() or (subreq_dir / "plan.md").is_file()
        ):
            errors.append(f"[LAYOUT] {subreq_id}: status={status} requires tasks.md or plan.md")

    if ui_bearing and status in {"visual_acceptance_passed", "merged", "archived"}:
        if not (subreq_dir / "visual-acceptance.md").is_file() and not any(
            (subreq_dir / "visual-acceptance").glob("*.png")
        ):
            warnings.append(
                f"[LAYOUT] {subreq_id}: UI-bearing status={status} has no visual-acceptance evidence"
            )

    return errors, warnings


def verify_archive(subreq_dir: Path) -> list[str]:
    """Validate archive immutability via MANIFEST.json sha256 (Phase 3 hook)."""
    errors: list[str] = []
    manifests = sorted(subreq_dir.glob("archive/*/MANIFEST.json"))
    for manifest in manifests:
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"[ARCHIVE] {manifest}: cannot read manifest: {exc}")
            continue
        for item in data.get("files", []):
            rel = item.get("path")
            expected = item.get("sha256")
            if not isinstance(rel, str) or not isinstance(expected, str):
                errors.append(f"[ARCHIVE] {manifest}: malformed manifest entry")
                continue
            target = manifest.parent / rel
            if not target.is_file():
                errors.append(f"[ARCHIVE] {manifest}: missing archived file {rel}")
                continue
            actual = canonical_sha256(target.read_text(encoding="utf-8"))
            if actual != expected:
                errors.append(f"[ARCHIVE] {manifest}: hash mismatch for {rel}")
    return errors


def validate_requirement(req_root: Path, verify_archive: bool = False) -> list[str]:
    status_path = req_root / "status.json"
    if not status_path.is_file():
        return [f"[LAYOUT] status.json not found at {status_path}"]
    try:
        data = json.loads(status_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"[LAYOUT] cannot read status.json: {exc}"]

    sub_requirements = data.get("sub_requirements")
    if not isinstance(sub_requirements, dict):
        return ["[LAYOUT] sub_requirements must be a mapping"]

    errors: list[str] = []
    for subreq_id, entry in sub_requirements.items():
        if not isinstance(entry, dict):
            errors.append(f"[LAYOUT] sub_requirements.{subreq_id} must be a mapping")
            continue
        if str(entry.get("status", "")).startswith("blocked_"):
            continue
        subreq_dir = req_root / "sub-requirements" / subreq_id
        sub_errors, _warnings = validate_subreq(subreq_id, entry, subreq_dir)
        errors.extend(sub_errors)
        if verify_archive:
            errors.extend(verify_archive(subreq_dir))
    return errors


def _selftest() -> int:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)

        # Old-layout subreq at tasks_ready: should pass (legacy files present).
        old = root / "sub-requirements" / "SR-OLD"
        old.mkdir(parents=True)
        (old / "spec.md").write_text("# spec\n", encoding="utf-8")
        (old / "tasks.md").write_text("# tasks\n", encoding="utf-8")
        st_old = root / "status.json"
        st_old.write_text(
            json.dumps({"sub_requirements": {"SR-OLD": {"status": "tasks_ready"}}}),
            encoding="utf-8",
        )
        assert validate_requirement(root) == [], "old-layout tasks_ready should validate clean"

        # New-layout subreq at tasks_ready missing spec/tasks.md: should fail.
        new = root / "sub-requirements" / "SR-NEW"
        new.mkdir(parents=True)
        new_spec = new / "spec"
        new_spec.mkdir(parents=True)
        (new_spec / "spec.md").write_text("# spec\n", encoding="utf-8")
        (new / "design.md").write_text("# design\n", encoding="utf-8")
        st_new = root / "status.json"
        st_new.write_text(
            json.dumps({"sub_requirements": {"SR-NEW": {"status": "tasks_ready"}}}),
            encoding="utf-8",
        )
        errs = validate_requirement(root)
        assert any("spec/tasks.md" in e for e in errs), errs

        # New-layout merged requires verification.md.
        (new / "spec" / "plan.md").write_text("# plan\n", encoding="utf-8")
        (new / "spec" / "tasks.md").write_text("# tasks\n", encoding="utf-8")
        st_new.write_text(
            json.dumps({"sub_requirements": {"SR-NEW": {"status": "merged"}}}),
            encoding="utf-8",
        )
        errs = validate_requirement(root)
        assert any("verification.md" in e for e in errs), errs

        # Archive immutability: tamper with an archived file -> mismatch.
        arch = new / "archive" / "2026-08-11T000000Z"
        arch.mkdir(parents=True)
        archived = arch / "spec" / "spec.md"
        archived.parent.mkdir(parents=True)
        archived.write_text("# original\n", encoding="utf-8")
        manifest = arch / "MANIFEST.json"
        manifest.write_text(
            json.dumps({"files": [{"path": "spec/spec.md", "sha256": canonical_sha256("# original\n")}]}),
            encoding="utf-8",
        )
        assert verify_archive(new) == [], "untampered archive should validate"
        archived.write_text("# tampered\n", encoding="utf-8")
        assert verify_archive(new), "tampered archive must be detected"

    print("validate-artifact-layout.py selftest OK")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("req_root", type=Path, nargs="?", help="Requirement root (parent of sub-requirements/)")
    parser.add_argument("--verify-archive", action="store_true", help="Also verify archive immutability via MANIFEST.json")
    parser.add_argument("--selftest", action="store_true", help="Run built-in assertions")
    args = parser.parse_args()

    if args.selftest:
        return _selftest()

    if args.req_root is None:
        parser.error("req_root is required (or use --selftest)")
    req_root = args.req_root.resolve()
    errors = validate_requirement(req_root, verify_archive=args.verify_archive)
    if not errors:
        print(f"OK: {req_root}")
        return 0
    for error in errors:
        print(f"FAIL {error}", file=sys.stderr)
    print(f"INVALID: {req_root} ({len(errors)} issue(s))", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
