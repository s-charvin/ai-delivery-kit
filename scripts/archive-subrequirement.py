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
5. If a requirement-level ``retrospective.md`` exists, registers its marked
   problem map in the project-level retrospective index without rewriting the
   ledger.

The archive snapshot is immutable: any later byte change is caught by
``validate-artifact-layout.py --verify-archive``. Requirement changes must open a
new ``<req-id>/`` directory; the archived one is a read-only reference.
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
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
from layout import (  # noqa: E402
    artifact_path,
    artifact_path_from_ai_delivery_dir,
    canonical_sha256,
    find_ai_delivery_dir,
)

RETROSPECTIVE_INDEX_START = "<!-- ai-delivery-retrospective:problem-index:v1 -->"
RETROSPECTIVE_INDEX_END = "<!-- /ai-delivery-retrospective:problem-index:v1 -->"
PROJECT_INDEX_START = "<!-- ai-delivery-retrospective:index:v1 -->"
PROJECT_INDEX_END = "<!-- /ai-delivery-retrospective:index:v1 -->"
INDEX_TEMPLATE_MARKER = "ai-delivery-retrospective:index:v1"
INDEX_TEMPLATE_PLACEHOLDER = "<retrospective_rows>"


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


def _table_cells(line: str) -> list[str]:
    if not line.lstrip().startswith("|"):
        return []
    cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
    return cells if len(cells) >= 6 else []


def read_retrospective_entries(retrospective: Path) -> list[dict[str, str]]:
    """Read only the stable problem-map table; never synthesize its content."""
    try:
        lines = retrospective.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise SystemExit(f"ERROR: cannot read retrospective {retrospective}: {exc}")

    try:
        start = lines.index(RETROSPECTIVE_INDEX_START)
        end = lines.index(RETROSPECTIVE_INDEX_END, start + 1)
    except ValueError:
        raise SystemExit(
            "ERROR: retrospective is missing the stable problem-index markers"
        )

    entries: list[dict[str, str]] = []
    for line in lines[start + 1 : end]:
        cells = _table_cells(line)
        if len(cells) < 6 or not cells[0].startswith("RET-") or cells[0].lower() in {"problem", "id"}:
            continue
        entries.append(
            {
                "id": cells[0],
                "trigger": cells[1],
                "scenario": cells[2],
                "path": cells[3],
                "status": cells[4],
                "details": cells[5],
            }
        )
    return entries


def retrospective_ledger_path(req_root: Path, req_id: str) -> Path:
    ad_dir = find_ai_delivery_dir(req_root)
    if ad_dir is not None:
        return artifact_path_from_ai_delivery_dir(ad_dir, "retrospective", req_id)
    return artifact_path(req_root.parent.parent.parent, "retrospective", req_id)


def retrospective_index_path(req_root: Path, req_id: str) -> Path:
    ad_dir = find_ai_delivery_dir(req_root)
    if ad_dir is not None:
        return artifact_path_from_ai_delivery_dir(ad_dir, "retrospective_index", req_id)
    return artifact_path(req_root.parent.parent.parent, "retrospective_index", req_id)


def has_writable_index_block(index_text: str) -> bool:
    try:
        start = index_text.index(PROJECT_INDEX_START)
        end = index_text.index(PROJECT_INDEX_END, start)
    except ValueError:
        return False
    return any(
        line.startswith("| ---")
        for line in index_text[start:end].splitlines()
    )


def load_retrospective_index_template(path: Path) -> str:
    try:
        template = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise SystemExit(f"ERROR: cannot read retrospective index template: {exc}")
    if TEMPLATE_LANGUAGE_MARKER in template:
        raise SystemExit(
            "ERROR: retrospective index template still contains its language instruction"
        )
    if INDEX_TEMPLATE_MARKER not in template or INDEX_TEMPLATE_PLACEHOLDER not in template:
        raise SystemExit(
            "ERROR: retrospective index template must contain the stable marker and "
            f"{INDEX_TEMPLATE_PLACEHOLDER}"
        )
    return template


def preflight_retrospective_index(
    req_root: Path, req_id: str, template_path: Path | None
) -> str | None:
    """Validate ledger/index inputs before archive state or bytes are changed."""
    retrospective = retrospective_ledger_path(req_root, req_id)
    if not retrospective.is_file():
        return None
    entries = read_retrospective_entries(retrospective)
    if not entries:
        return None

    index = retrospective_index_path(req_root, req_id)
    existing = index.read_text(encoding="utf-8") if index.is_file() else ""
    if template_path is None and not has_writable_index_block(existing):
        raise SystemExit(
            "ERROR: first retrospective index creation requires a localized "
            "--retrospective-index-template"
        )
    return (
        load_retrospective_index_template(template_path)
        if template_path is not None
        else None
    )


def register_retrospective_index(
    req_root: Path,
    req_id: str,
    archived_at: datetime.datetime,
    template: str | None,
) -> Path | None:
    """Idempotently replace one requirement's rows in the project index."""
    retrospective = retrospective_ledger_path(req_root, req_id)
    if not retrospective.is_file():
        return None

    entries = read_retrospective_entries(retrospective)
    if not entries:
        return None

    index = retrospective_index_path(req_root, req_id)
    existing = index.read_text(encoding="utf-8") if index.is_file() else ""
    rows = []
    for entry in entries:
        anchor = ""
        details = entry["details"]
        if "#" in details:
            anchor = "#" + details.rsplit("#", 1)[1].rstrip(")")
        target = f"{Path(os.path.relpath(retrospective, index.parent)).as_posix()}{anchor}"
        rows.append(
            f"| {req_id}/{entry['id']} | {entry['trigger']} | {entry['scenario']} | "
            f"{entry['path']} | {entry['status']} | {archived_at.isoformat()} | "
            f"[{req_id}/{entry['id']}]({target}) |"
        )
    row_text = "\n".join(rows)

    if existing:
        try:
            start = existing.index(PROJECT_INDEX_START)
            end_marker = PROJECT_INDEX_END
            end = existing.index(end_marker, start) + len(end_marker)
            block = existing[start:end]
            lines = block.splitlines()
            separator = next((i for i, line in enumerate(lines) if line.startswith("| ---")), None)
            if separator is None:
                raise ValueError
            other_rows = [
                line
                for line in lines[separator + 1 : -1]
                if not line.lstrip().startswith("|")
                or not line.lstrip().startswith(f"| {req_id}/")
            ]
            replacement = "\n".join(
                lines[: separator + 1] + other_rows + [row_text, lines[-1]]
            )
            content = existing[:start] + replacement + existing[end:]
        except ValueError:
            if template is None:
                raise SystemExit(
                    "ERROR: retrospective index has no recognized markers and no localized "
                    "--retrospective-index-template was provided"
                )
            content = existing.rstrip() + "\n\n" + template.replace(INDEX_TEMPLATE_PLACEHOLDER, row_text).rstrip() + "\n"
    else:
        if template is None:
            raise SystemExit(
                "ERROR: first retrospective index creation requires a localized "
                "--retrospective-index-template"
            )
        if INDEX_TEMPLATE_MARKER not in template or INDEX_TEMPLATE_PLACEHOLDER not in template:
            raise SystemExit(
                "ERROR: retrospective index template must contain the stable marker and "
                f"{INDEX_TEMPLATE_PLACEHOLDER}"
            )
        content = template.replace(INDEX_TEMPLATE_PLACEHOLDER, row_text).rstrip() + "\n"
    index.parent.mkdir(parents=True, exist_ok=True)
    index.write_text(content, encoding="utf-8")
    return index


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--req-root", type=Path, required=True, help="Requirement root (parent of sub-requirements/)")
    parser.add_argument("--subreq", type=str, required=True, help="Sub-requirement id to archive")
    parser.add_argument("--now", type=str, default=None, help="Override archive timestamp (ISO8601, for tests)")
    parser.add_argument("--no-status-write", action="store_true", help="Freeze only; do not touch status.json")
    parser.add_argument(
        "--retrospective-index-template",
        type=Path,
        help="Localized index template used when the project retrospective index is first created",
    )
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
    index_template = None
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
    if will_complete:
        try:
            index_template = preflight_retrospective_index(
                req_root, data.get("requirement_id", ""), args.retrospective_index_template
            )
        except SystemExit as exc:
            print(str(exc), file=sys.stderr)
            return 2

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

    if not args.no_status_write and all_archived(data):
        index = register_retrospective_index(req_root, req_id, now, index_template)
        if index is not None:
            print(f"RETROSPECTIVE_INDEX {index}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
