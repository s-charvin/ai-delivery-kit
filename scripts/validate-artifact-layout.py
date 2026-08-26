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
import re
import sys
import tempfile
from pathlib import Path

LAYOUT_REL = Path(".agents/skills/ai-delivery-orchestrator/scripts")


def _locate_layout_dir() -> Path:
    """Find the orchestrator scripts dir by walking up from this file.

    Handles both layouts this validator lives in: the kit repo
    (``<kit>/scripts/``) and a bootstrapped repo (``<repo>/.ai-delivery/scripts/``,
    where ``.agents/`` is a *sibling* of ``.ai-delivery/``, not a parent).
    """
    here = Path(__file__).resolve()
    for base in here.parents:
        cand = base / LAYOUT_REL
        if (cand / "layout.py").is_file():
            return cand
    raise SystemExit(
        "ERROR: cannot locate .agents/skills/ai-delivery-orchestrator/scripts/layout.py "
        "— the artifact-layout contract is unavailable"
    )


# Reuse the same layout contract the orchestrator uses. `is_new_layout`,
# `canonical_sha256` and `spec_drift` live there so hashing/detection logic
# exists in exactly one place (see docs/artifact-layout.md).
sys.path.insert(0, str(_locate_layout_dir()))
from layout import (  # noqa: E402
    canonical_sha256,
    is_new_layout,
    load_workflow_policy,
    spec_drift,
)

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
UI_TRUTH_CAPABILITY_MODES = frozenset({"runtime-baseline", "figma"})
UI_TRUTH_MODES = frozenset({"none", "existing", "runtime-baseline", "figma"})
DESIGN_MODES = frozenset({"none", "light", "full"})
LEGACY_MODE_FIELDS = frozenset({"ui_contract_exempt", "no_design_client"})


def _contains_identifier(text: str, identifier: str) -> bool:
    """Match a machine id as a token, not as a substring of another id."""
    return re.search(
        rf"(?<![a-z0-9-]){re.escape(identifier)}(?![a-z0-9-])", text
    ) is not None


def legacy_binding_errors(req_root: Path) -> list[str]:
    """Reject removed mode fields in the project binding metadata."""

    def legacy_keys(value: object) -> set[str]:
        if isinstance(value, dict):
            found = {key for key in value if key in LEGACY_MODE_FIELDS}
            for nested in value.values():
                found.update(legacy_keys(nested))
            return found
        if isinstance(value, list):
            found: set[str] = set()
            for nested in value:
                found.update(legacy_keys(nested))
            return found
        return set()

    def has_legacy_profile(value: object) -> bool:
        if isinstance(value, dict):
            if value.get("participation") == "no_design_client":
                return True
            return any(has_legacy_profile(nested) for nested in value.values())
        if isinstance(value, list):
            return any(has_legacy_profile(nested) for nested in value)
        return False

    candidates = [req_root / ".ai-delivery" / "meta" / "project-binding.json"]
    candidates.extend(
        parent / ".ai-delivery" / "meta" / "project-binding.json"
        for parent in req_root.parents
    )
    for path in candidates:
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            continue
        if not isinstance(data, dict):
            continue
        stale = sorted(legacy_keys(data))
        if has_legacy_profile(data):
            stale.append("no_design_client")
        if stale:
            return [
                "[LAYOUT] legacy project-binding field(s) are forbidden: "
                + ", ".join(sorted(set(stale)))
            ]
    return []


def _at_least(status: str, target: str) -> bool:
    try:
        return STATUS_ORDER.index(status) >= STATUS_ORDER.index(target)
    except ValueError:
        return False


def _has_ui_truth(subreq_dir: Path) -> bool:
    return (subreq_dir / "contracts" / "ui-truth-index.json").is_file()


def _check_design_scenario_refs(subreq_id: str, subreq_dir: Path) -> list[str]:
    index_path = subreq_dir / "contracts" / "ui-truth-index.json"
    design_path = subreq_dir / "design.md"
    if not index_path.is_file() or not design_path.is_file():
        return []
    try:
        index = json.loads(index_path.read_text(encoding="utf-8"))
        design_text = design_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return [f"[DESIGN] {subreq_id}: cannot inspect scenario references: {exc}"]
    errors: list[str] = []
    for unit in index.get("units", []) if isinstance(index, dict) else []:
        if not isinstance(unit, dict):
            continue
        for scenario in unit.get("scenarios", []):
            if not isinstance(scenario, dict):
                continue
            scenario_id = scenario.get("scenario_id")
            if (
                isinstance(scenario_id, str)
                and scenario_id
                and not _contains_identifier(design_text, scenario_id)
            ):
                errors.append(
                    f"[DESIGN] {subreq_id}: design.md must reference indexed scenario_id {scenario_id}"
                )
    return errors


def validate_subreq(subreq_id: str, entry: dict, subreq_dir: Path) -> tuple[list[str], list[str]]:
    """Return (errors, warnings) for one sub-requirement."""
    errors: list[str] = []
    warnings: list[str] = []
    status = entry.get("status")
    if not isinstance(status, str):
        return errors, warnings

    def legacy_keys(value: object) -> set[str]:
        if isinstance(value, dict):
            found = {key for key in value if key in LEGACY_MODE_FIELDS}
            for nested in value.values():
                found.update(legacy_keys(nested))
            return found
        if isinstance(value, list):
            found: set[str] = set()
            for nested in value:
                found.update(legacy_keys(nested))
            return found
        return set()

    for field in sorted(legacy_keys(entry)):
        errors.append(f"[LAYOUT] {subreq_id}: legacy field {field} is forbidden")
    if type(entry.get("design_approved")) is not bool:
        errors.append(f"[LAYOUT] {subreq_id}: design_approved must be a boolean")
    elif entry.get("design_mode") == "none" and entry.get("design_approved") is True:
        errors.append(
            f"[LAYOUT] {subreq_id}: design_mode=none cannot set design_approved=true"
        )

    new_layout = is_new_layout(subreq_dir)
    ui_truth_mode = entry.get("ui_truth_mode")
    design_mode = entry.get("design_mode")
    if type(entry.get("ui_bearing")) is not bool:
        errors.append(f"[LAYOUT] {subreq_id}: ui_bearing must be a boolean")
    ui_bearing = entry.get("ui_bearing") is True
    if ui_truth_mode not in UI_TRUTH_MODES:
        errors.append(
            f"[LAYOUT] {subreq_id}: ui_truth_mode must be one of "
            f"{', '.join(sorted(UI_TRUTH_MODES))}"
        )
    if design_mode not in DESIGN_MODES:
        errors.append(
            f"[LAYOUT] {subreq_id}: design_mode must be one of "
            f"{', '.join(sorted(DESIGN_MODES))}"
        )
    if isinstance(ui_truth_mode, str) and ui_truth_mode in UI_TRUTH_MODES:
        expected_ui = ui_truth_mode != "none"
        if ui_bearing != expected_ui:
            errors.append(
                f"[LAYOUT] {subreq_id}: ui_bearing is inconsistent with "
                f"ui_truth_mode={ui_truth_mode}"
            )

    if new_layout:
        if _at_least(status, "spec_ready") and not (subreq_dir / "spec" / "spec.md").is_file():
            errors.append(f"[LAYOUT] {subreq_id}: status={status} (new layout) requires spec/spec.md")
        if _at_least(status, "plan_ready") and not (subreq_dir / "spec" / "plan.md").is_file():
            errors.append(f"[LAYOUT] {subreq_id}: status={status} (new layout) requires spec/plan.md")
        if _at_least(status, "tasks_ready") and not (subreq_dir / "spec" / "tasks.md").is_file():
            errors.append(f"[LAYOUT] {subreq_id}: status={status} (new layout) requires spec/tasks.md")
        if (
            design_mode in {"light", "full"}
            and _at_least(status, "spec_ready")
            and not (subreq_dir / "design.md").is_file()
        ):
            errors.append(f"[LAYOUT] {subreq_id}: status={status} (new layout) requires design.md")
        if status in {"merged", "archived"} and not (subreq_dir / "verification.md").is_file():
            errors.append(f"[LAYOUT] {subreq_id}: status={status} requires verification.md")
        # Legacy files at the wrong (root) location in a new-layout sub-req.
        if (subreq_dir / "spec.md").is_file():
            warnings.append(f"[LAYOUT] {subreq_id}: legacy spec.md at root; move to spec/spec.md")
        if (subreq_dir / "tasks.md").is_file():
            warnings.append(f"[LAYOUT] {subreq_id}: legacy tasks.md at root; move to spec/tasks.md")
        # living-spec drift: derived plan/tasks are stale relative to spec.md.
        if _at_least(status, "plan_ready"):
            for message in spec_drift(subreq_dir):
                errors.append(
                    f"[DRIFT] {subreq_id}: {message} — regenerate the derived "
                    f"artifacts (living spec downgrades to spec_ready; record key "
                    f"decisions in decisions.md first)"
                )
    else:
        # Legacy layout: only enforce what the legacy contract required.
        if _at_least(status, "spec_ready") and not (subreq_dir / "spec.md").is_file():
            errors.append(f"[LAYOUT] {subreq_id}: status={status} requires spec.md")
        if _at_least(status, "tasks_ready") and not (
            (subreq_dir / "tasks.md").is_file() or (subreq_dir / "plan.md").is_file()
        ):
            errors.append(f"[LAYOUT] {subreq_id}: status={status} requires tasks.md or plan.md")

    if ui_truth_mode in UI_TRUTH_CAPABILITY_MODES and _at_least(status, "acceptance_frozen") and not _has_ui_truth(subreq_dir):
        errors.append(
            f"[LAYOUT] {subreq_id}: ui_truth_mode={ui_truth_mode} status={status} "
            "requires contracts/ui-truth-index.json"
        )

    if status == "acceptance_frozen" and ui_truth_mode not in UI_TRUTH_CAPABILITY_MODES:
        errors.append(
            f"[LAYOUT] {subreq_id}: acceptance_frozen requires ui_truth_mode="
            "figma or runtime-baseline"
        )
    if status == "visual_acceptance_passed" and ui_truth_mode not in UI_TRUTH_CAPABILITY_MODES:
        errors.append(
            f"[LAYOUT] {subreq_id}: visual_acceptance_passed requires ui_truth_mode="
            "figma or runtime-baseline"
        )

    if ui_truth_mode in UI_TRUTH_CAPABILITY_MODES and status in {"visual_acceptance_passed", "merged", "archived"}:
        if not (subreq_dir / "visual-acceptance.json").is_file():
            errors.append(
                f"[LAYOUT] {subreq_id}: ui_truth_mode={ui_truth_mode} status={status} "
                "requires visual-acceptance.json"
            )

    if ui_truth_mode not in UI_TRUTH_CAPABILITY_MODES and _has_ui_truth(subreq_dir):
        errors.append(
            f"[LAYOUT] {subreq_id}: contracts/ui-truth-index.json is forbidden when "
            f"ui_truth_mode={ui_truth_mode}"
        )
    if ui_truth_mode not in UI_TRUTH_CAPABILITY_MODES and (
        subreq_dir / "visual-acceptance.json"
    ).is_file():
        errors.append(
            f"[LAYOUT] {subreq_id}: visual-acceptance.json is forbidden when "
            f"ui_truth_mode={ui_truth_mode}"
        )

    design_path = subreq_dir / "design.md"
    if design_mode == "none" and design_path.is_file():
        errors.append(f"[LAYOUT] {subreq_id}: design_mode=none must not produce design.md")
    if design_mode in {"light", "full"} and entry.get("design_approved") is True and not design_path.is_file():
        errors.append(f"[LAYOUT] {subreq_id}: design_approved=true requires design.md")

    if design_mode in {"light", "full"}:
        errors.extend(_check_design_scenario_refs(subreq_id, subreq_dir))

    return errors, warnings


def verify_archive(subreq_dir: Path, status: str | None = None) -> list[str]:
    """Validate archive immutability via MANIFEST.json sha256 (Phase 3 hook)."""
    errors: list[str] = []
    manifests = sorted(subreq_dir.glob("archive/*/MANIFEST.json"))
    # An archived sub-requirement MUST carry at least one immutable snapshot;
    # without it the flow-forward guarantee (docs/artifact-layout.md §3) is void.
    if status == "archived" and not manifests:
        errors.append(
            f"[ARCHIVE] {subreq_dir}: archived sub-requirement has no archive snapshot "
            f"(expected archive/<ISO-ts>/MANIFEST.json)"
        )
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


def validate_requirement(req_root: Path, check_archive: bool = False) -> list[str]:
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
    errors.extend(legacy_binding_errors(req_root))
    for field in sorted(LEGACY_MODE_FIELDS):
        if field in data:
            errors.append(f"[LAYOUT] legacy field {field} is forbidden")
    for subreq_id, entry in sub_requirements.items():
        if not isinstance(entry, dict):
            errors.append(f"[LAYOUT] sub_requirements.{subreq_id} must be a mapping")
            continue
        subreq_dir = req_root / "sub-requirements" / subreq_id
        sub_errors, _warnings = validate_subreq(subreq_id, entry, subreq_dir)
        errors.extend(sub_errors)
        if check_archive and not str(entry.get("status", "")).startswith("blocked_"):
            errors.extend(verify_archive(subreq_dir, entry.get("status")))
    return errors


def _selftest() -> int:
    assert not _contains_identifier(
        "default-phone-extra", "default-phone"
    ), "scenario ids must not match as substrings"
    assert _contains_identifier(
        "Scenario IDs: default-phone", "default-phone"
    ), "scenario token should be discoverable"

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)

        # Old-layout subreq at tasks_ready: should pass (legacy files present).
        old = root / "sub-requirements" / "SR-OLD"
        old.mkdir(parents=True)
        (old / "spec.md").write_text("# spec\n", encoding="utf-8")
        (old / "tasks.md").write_text("# tasks\n", encoding="utf-8")
        st_old = root / "status.json"
        st_old.write_text(
            json.dumps(
                {
                    "sub_requirements": {
                        "SR-OLD": {
                            "status": "tasks_ready",
                            "ui_bearing": False,
                            "ui_truth_mode": "none",
                            "design_mode": "none",
                            "design_approved": False,
                        }
                    }
                }
            ),
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
            json.dumps(
                {
                    "sub_requirements": {
                        "SR-NEW": {
                            "status": "tasks_ready",
                            "ui_bearing": False,
                            "ui_truth_mode": "none",
                            "design_mode": "light",
                            "design_approved": True,
                        }
                    }
                }
            ),
            encoding="utf-8",
        )
        errs = validate_requirement(root)
        assert any("spec/tasks.md" in e for e in errs), errs

        # New-layout merged requires verification.md.
        (new / "spec" / "plan.md").write_text("# plan\n", encoding="utf-8")
        (new / "spec" / "tasks.md").write_text("# tasks\n", encoding="utf-8")
        st_new.write_text(
            json.dumps(
                {
                    "sub_requirements": {
                        "SR-NEW": {
                            "status": "merged",
                            "ui_bearing": False,
                            "ui_truth_mode": "none",
                            "design_mode": "light",
                            "design_approved": True,
                        }
                    }
                }
            ),
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

        # check_archive=True must reach verify_archive through validate_requirement
        # (regression guard: the parameter used to shadow the function name).
        (new / "verification.md").write_text("# verification\n", encoding="utf-8")
        errs = validate_requirement(root, check_archive=True)
        assert any(e.startswith("[ARCHIVE]") for e in errs), errs

    # living-spec drift: recorded hash != on-disk content -> [DRIFT] at plan_ready
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        sr = root / "sub-requirements" / "SR-D"
        (sr / "spec").mkdir(parents=True)
        (sr / "spec" / "spec.md").write_text("# spec\nv1\n", encoding="utf-8")
        (sr / "spec" / "plan.md").write_text("# plan\n", encoding="utf-8")
        (sr / "design.md").write_text("# design\n", encoding="utf-8")
        (sr / "traceability.json").write_text(
            json.dumps(
                {
                    "spec_refs": {
                        "tier": "native",
                        "artifacts": [
                            {
                                "kind": "spec",
                                "canonical_path": "spec/spec.md",
                                "content_sha256": canonical_sha256("# spec\nv1\n"),
                                "sync_state": "synced",
                            }
                        ],
                    }
                }
            ),
            encoding="utf-8",
        )
        (root / "status.json").write_text(
            json.dumps(
                {
                    "sub_requirements": {
                        "SR-D": {
                            "status": "plan_ready",
                            "ui_bearing": False,
                            "ui_truth_mode": "none",
                            "design_mode": "light",
                            "design_approved": True,
                        }
                    }
                }
            ),
            encoding="utf-8",
        )
        assert validate_requirement(root) == [], validate_requirement(root)
        # rewrite spec.md -> derived plan.md is now stale
        (sr / "spec" / "spec.md").write_text("# spec\nv2\n", encoding="utf-8")
        errs = validate_requirement(root)
        assert any(e.startswith("[DRIFT]") for e in errs), errs
        # drift is not enforced before plan_ready (nothing derived yet)
        (root / "status.json").write_text(
            json.dumps(
                {
                    "sub_requirements": {
                        "SR-D": {
                            "status": "spec_ready",
                            "ui_bearing": False,
                            "ui_truth_mode": "none",
                            "design_mode": "light",
                            "design_approved": True,
                        }
                    }
                }
            ),
            encoding="utf-8",
        )
        assert not any(e.startswith("[DRIFT]") for e in validate_requirement(root))

    # A customized binding may place spec artifacts outside sub_requirement_dir.
    # Drift checks must resolve the recorded repo-relative canonical path.
    with tempfile.TemporaryDirectory() as td:
        repo = Path(td)
        ai_delivery = repo / ".ai-delivery"
        meta = ai_delivery / "meta"
        meta.mkdir(parents=True)
        (meta / "project-binding.json").write_text(
            json.dumps(
                {
                    "ai_delivery_path": ".ai-delivery",
                    "layout": {
                        "requirement_root": "requirements/{req_id}",
                        "sub_requirement_dir": (
                            "requirements/{req_id}/sub-requirements/{sr_id}"
                        ),
                        "requirement_artifacts": {},
                        "sub_requirement_artifacts": {
                            "spec": (
                                "requirements/{req_id}/custom-artifacts/"
                                "{sr_id}/spec.md"
                            )
                        },
                    },
                }
            ),
            encoding="utf-8",
        )
        sr = ai_delivery / "requirements" / "REQ-C" / "sub-requirements" / "SR-C"
        sr.mkdir(parents=True)
        custom_spec = (
            ai_delivery / "requirements" / "REQ-C" / "custom-artifacts" / "SR-C" / "spec.md"
        )
        custom_spec.parent.mkdir(parents=True)
        custom_spec.write_text("# custom spec\n", encoding="utf-8")
        (sr / "traceability.json").write_text(
            json.dumps(
                {
                    "spec_refs": {
                        "tier": "native",
                        "artifacts": [
                            {
                                "kind": "spec",
                                "canonical_path": (
                                    ".ai-delivery/requirements/REQ-C/"
                                    "custom-artifacts/SR-C/spec.md"
                                ),
                                "derived_paths": [],
                                "content_sha256": canonical_sha256("# custom spec\n"),
                                "sync_state": "synced",
                            }
                        ],
                    }
                }
            ),
            encoding="utf-8",
        )
        assert spec_drift(sr) == [], spec_drift(sr)

    # policy is readable and carries the spec_persistence contract
    policy = load_workflow_policy(Path(__file__).resolve().parents[1])
    assert policy.get("spec_persistence", {}).get("active") == "living", policy.get("spec_persistence")

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
    errors = validate_requirement(req_root, check_archive=args.verify_archive)
    if not errors:
        print(f"OK: {req_root}")
        return 0
    for error in errors:
        print(f"FAIL {error}", file=sys.stderr)
    print(f"INVALID: {req_root} ({len(errors)} issue(s))", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
