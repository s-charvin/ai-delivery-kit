#!/usr/bin/env python3
"""Freeze a merged sub-requirement into the immutable archive (the `archive` action).

Run by the orchestrator as the `archive` action emitted by reconcile when a
sub-requirement is `merged` and the requirement has reached `runtime_mode=closing`.
It:

1. Copies the canonical three-piece spec set plus ``design.md`` and
   ``verification.md`` into ``<subreq>/archive/<ISO-ts>/``.
2. Writes ``MANIFEST.json`` recording each archived file's sha256 (the machine
   basis for later ``--verify-archive`` tamper detection).
3. Advances the sub-requirement status ``merged`` -> ``archived``.
4. When every executable sub-requirement is ``archived``, generates a
   requirement-level ``delivery-report.md`` from a caller-supplied template
   already localized to the user's current conversation language.

The archive snapshot is immutable: any later byte change is caught by
``validate-artifact-layout.py --verify-archive``. Requirement changes must open a
new ``<req-id>/`` directory; the archived one is a read-only reference.
"""

from __future__ import annotations

import argparse
import datetime
import json
import sys
from pathlib import Path

LAYOUT_REL = Path(".agents/skills/ai-delivery-orchestrator/scripts")
TEMPLATE_LANGUAGE_MARKER = "ai-delivery-template-language"
REPORT_PLACEHOLDERS = (
    "<req-id>",
    "<archived_at>",
    "<subreq_count>",
    "<subreq_rows>",
)

# Canonical artifacts frozen into each archive snapshot, in on-disk form.
ARTIFACT_RELS = (
    "spec/spec.md",
    "spec/plan.md",
    "spec/tasks.md",
    "design.md",
    "verification.md",
)


def _locate_layout_dir() -> Path:
    """Find the orchestrator scripts dir by walking up from this file.

    Mirrors the resolution in ``validate-artifact-layout.py``: handles both the
    kit repo (``<kit>/scripts/``) and a bootstrapped repo
    (``<repo>/.ai-delivery/scripts/``, where ``.agents/`` is a sibling).
    """
    here = Path(__file__).resolve()
    for base in [here, *here.parents]:
        cand = base / LAYOUT_REL
        if (cand / "layout.py").is_file():
            return cand
    raise SystemExit(
        "ERROR: cannot locate .agents/skills/ai-delivery-orchestrator/scripts/layout.py "
        "— the artifact-layout contract is unavailable"
    )


sys.path.insert(0, str(_locate_layout_dir()))
from layout import canonical_sha256  # noqa: E402


def freeze(subreq_dir: Path, req_id: str, subreq_id: str, now: datetime.datetime) -> tuple[Path, list[str]]:
    """Copy canonical artifacts into a timestamped archive dir + write MANIFEST.json."""
    stamp = now.strftime("%Y-%m-%dT%H%M%SZ")
    archive_dir = subreq_dir / "archive" / stamp
    archive_dir.mkdir(parents=True, exist_ok=True)

    files: list[dict] = []
    missing: list[str] = []
    for rel in ARTIFACT_RELS:
        src = subreq_dir / rel
        if not src.is_file():
            missing.append(rel)
            continue
        text = src.read_text(encoding="utf-8")
        dst = archive_dir / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(text, encoding="utf-8")
        files.append({"path": rel, "sha256": canonical_sha256(text)})

    if not files:
        raise SystemExit(
            f"ERROR: {subreq_id} has no canonical artifacts to archive (looked for: "
            f"{', '.join(ARTIFACT_RELS)}); refusing to create an empty snapshot"
        )

    manifest = {
        "req_id": req_id,
        "subreq_id": subreq_id,
        "archived_at": now.isoformat(),
        "files": files,
    }
    (archive_dir / "MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return archive_dir, missing


def load_status(req_root: Path) -> dict:
    status_path = req_root / "status.json"
    if not status_path.is_file():
        raise SystemExit(f"ERROR: status.json not found at {status_path}")
    try:
        return json.loads(status_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"ERROR: cannot read status.json: {exc}")


def write_status(req_root: Path, data: dict) -> None:
    (req_root / "status.json").write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def all_archived(data: dict) -> bool:
    subreqs = data.get("sub_requirements")
    if not isinstance(subreqs, dict) or not subreqs:
        return False
    return all(
        isinstance(e, dict) and e.get("status") == "archived"
        for e in subreqs.values()
    )


def all_archived_after(data: dict, subreq_id: str) -> bool:
    subreqs = data.get("sub_requirements")
    if not isinstance(subreqs, dict) or not subreqs:
        return False
    return all(
        isinstance(entry, dict)
        and (sid == subreq_id or entry.get("status") == "archived")
        for sid, entry in subreqs.items()
    )


def load_delivery_report_template(path: Path) -> str:
    try:
        template = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise SystemExit(f"ERROR: cannot read delivery report template {path}: {exc}")
    if TEMPLATE_LANGUAGE_MARKER in template:
        raise SystemExit(
            "ERROR: delivery report template still contains its language instruction; "
            "localize the human-readable content and remove the instruction before archiving"
        )
    missing = [placeholder for placeholder in REPORT_PLACEHOLDERS if placeholder not in template]
    if missing:
        raise SystemExit(
            "ERROR: delivery report template is missing required placeholders: "
            + ", ".join(missing)
        )
    return template


def render_delivery_report(
    req_root: Path, data: dict, now: datetime.datetime, template: str
) -> Path:
    req_id = data.get("requirement_id", "<req-id>")
    subreqs = data.get("sub_requirements", {})

    rows: list[str] = []
    for sid in sorted(subreqs):
        entry = subreqs[sid]
        subreq_dir = req_root / "sub-requirements" / sid
        snapshots = sorted(subreq_dir.glob("archive/*/MANIFEST.json"))
        latest = snapshots[-1].parent.name if snapshots else "-"
        verification = (
            f"sub-requirements/{sid}/verification.md"
            if (subreq_dir / "verification.md").is_file()
            else "-"
        )
        rows.append(f"| {sid} | {entry.get('status', '-')} | {latest} | {verification} |")

    rendered = (
        template.replace("<req-id>", req_id)
        .replace("<archived_at>", now.isoformat())
        .replace("<subreq_count>", str(len(subreqs)))
        .replace("<subreq_rows>", "\n".join(rows))
    )
    out = req_root / "delivery-report.md"
    out.write_text(rendered, encoding="utf-8")
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--req-root", type=Path, required=True, help="Requirement root (parent of sub-requirements/)")
    parser.add_argument("--subreq", type=str, required=True, help="Sub-requirement id to archive")
    parser.add_argument("--now", type=str, default=None, help="Override archive timestamp (ISO8601, for tests)")
    parser.add_argument("--no-status-write", action="store_true", help="Freeze only; do not touch status.json")
    report_group = parser.add_mutually_exclusive_group()
    report_group.add_argument(
        "--delivery-report-template",
        type=Path,
        help="Localized delivery report template used when this command archives the final sub-requirement",
    )
    report_group.add_argument(
        "--no-delivery-report",
        action="store_true",
        help="Do not generate delivery-report.md even if all archived",
    )
    args = parser.parse_args()

    req_root = args.req_root.resolve()
    subreq_dir = req_root / "sub-requirements" / args.subreq
    if not subreq_dir.is_dir():
        print(f"ERROR: sub-requirement dir not found: {subreq_dir}", file=sys.stderr)
        return 2

    data = load_status(req_root)
    entry = (data.get("sub_requirements") or {}).get(args.subreq)
    if not isinstance(entry, dict):
        print(f"ERROR: {args.subreq} not present in status.json", file=sys.stderr)
        return 2

    status = entry.get("status")
    if status != "merged":
        print(
            f"ERROR: {args.subreq} status is '{status}', not 'merged'; "
            f"only merged sub-requirements may be archived",
            file=sys.stderr,
        )
        return 2

    report_template = None
    will_complete = not args.no_status_write and all_archived_after(data, args.subreq)
    if will_complete and not args.no_delivery_report:
        if args.delivery_report_template is None:
            print(
                "ERROR: final archive requires --delivery-report-template with human-readable "
                "content localized to the user's current conversation language",
                file=sys.stderr,
            )
            return 2
        report_template = load_delivery_report_template(args.delivery_report_template)

    now = (
        datetime.datetime.fromisoformat(args.now)
        if args.now
        else datetime.datetime.now(datetime.timezone.utc)
    )
    req_id = data.get("requirement_id", "")
    archive_dir, missing = freeze(subreq_dir, req_id, args.subreq, now)

    if not args.no_status_write:
        entry["status"] = "archived"
        write_status(req_root, data)

    print(f"ARCHIVED {args.subreq} -> {archive_dir.relative_to(req_root)}")
    if missing:
        print(f"WARNING: skipped missing canonical artifacts: {', '.join(missing)}", file=sys.stderr)

    if not args.no_delivery_report and all_archived(data):
        if report_template is None:
            print("ERROR: localized delivery report template was not loaded", file=sys.stderr)
            return 2
        report = render_delivery_report(req_root, data, now, report_template)
        print(f"DELIVERY_REPORT {report.relative_to(req_root)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
