#!/usr/bin/env python3
"""在原位置归档已合并的子需求。

归档消费共享治理校验，预检并准备交付报告及复盘索引；输出逐文件原子
替换成功后，最后原子写入 archived 状态并打印成功。合作入口以项目锁
串行化，保护同需求状态及共享索引；这不构成跨文件事务。

规范材料保留原路径，新归档不创建 archive 快照。历史已归档状态不会
自动重置；已合并状态下的中断可在修复故障后用原命令重试。
"""

from __future__ import annotations

import argparse
import datetime
import contextlib
import hashlib
import importlib.util
import json
import os
import re
import sys
import stat
import tempfile
import time
from html.parser import HTMLParser
from pathlib import Path

LAYOUT_REL = Path(".agents/skills/ai-delivery-orchestrator/scripts")
TEMPLATE_LANGUAGE_MARKER = "ai-delivery-template-language"
REPORT_PLACEHOLDERS = (
    "<req-id>",
    "<archived_at>",
    "<subreq_count>",
    "<subreq_rows>",
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


sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
sys.path.insert(0, str(_locate_layout_dir()))
from layout import (  # noqa: E402
    artifact_path,
    artifact_path_from_ai_delivery_dir,
    find_ai_delivery_dir,
    requirement_artifact_path,
    requirement_subdir,
    resolve_validator_script,
    load_workflow_policy,
    repo_root_from_ai_delivery_dir,
)

RETROSPECTIVE_INDEX_START = "<!-- ai-delivery-retrospective:problem-index:v2 -->"
RETROSPECTIVE_INDEX_END = "<!-- /ai-delivery-retrospective:problem-index:v2 -->"
LEGACY_RETROSPECTIVE_INDEX_START = "<!-- ai-delivery-retrospective:problem-index:v1 -->"
LEGACY_RETROSPECTIVE_INDEX_END = "<!-- /ai-delivery-retrospective:problem-index:v1 -->"
PROJECT_INDEX_START = "<!-- ai-delivery-retrospective:index:v1 -->"
PROJECT_INDEX_END = "<!-- /ai-delivery-retrospective:index:v1 -->"
INDEX_TEMPLATE_MARKER = "ai-delivery-retrospective:index:v1"
INDEX_TEMPLATE_PLACEHOLDER = "<retrospective_rows>"
PROBLEM_MAP_REQUIRED_COLUMNS = frozenset(
    {
        "knowledge_type",
        "reuse_scope",
        "index_decision",
        "confidence",
        "importance",
    }
)
RETROSPECTIVE_REVIEWED_AT_RE = re.compile(
    r"<!--\s*ai-delivery-retrospective:reviewed-at:(?P<value>[^\s]+)\s*-->"
)
INDEXABLE_KNOWLEDGE_TYPES = frozenset({"reusable"})
INDEXABLE_REUSE_SCOPES = frozenset({"project", "domain"})
INDEXABLE_INDEX_DECISIONS = frozenset({"include"})
INDEXABLE_CONFIDENCE = frozenset({"confirmed"})
INDEXABLE_IMPORTANCE = frozenset({"high", "critical"})


@contextlib.contextmanager
def archive_lock(req_root: Path):
    """合作归档入口共用项目锁；平台不支持时拒绝写入。"""
    try:
        import fcntl
    except ImportError as exc:
        raise ValueError("当前平台不支持 flock；归档写入已停止") from exc
    ad = find_ai_delivery_dir(req_root)
    lock_root = repo_root_from_ai_delivery_dir(ad) if ad is not None else req_root
    if ad is None and not req_root.exists():
        # 显式重建可能已移动自定义治理根；仅复用既有项目锁，不另建需求锁。
        lock_root = next((parent for parent in req_root.parents
                          if (parent / ".ai-delivery.lock").exists()
                          or (parent / ".ai-delivery.lock").is_symlink()), None)
        if lock_root is None:
            raise ValueError("需求路径不存在且无法定位稳定项目锁；归档写入已停止")
    lock_path = lock_root / ".ai-delivery.lock"
    if not hasattr(os, "O_NOFOLLOW"):
        raise ValueError("当前平台不支持安全项目锁；归档写入已停止")
    descriptor = os.open(lock_path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "a+b") as handle:
        if not stat.S_ISREG(os.fstat(handle.fileno()).st_mode):
            raise ValueError(f"项目锁必须为普通文件：{lock_path}")
        deadline = time.monotonic() + 5
        while True:
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise ValueError("等待归档项目锁超时（5s）；请稍后重试")
                time.sleep(0.05)
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def load_status(req_root: Path) -> dict:
    status_path = requirement_artifact_path(req_root, "status")
    data = json.loads(status_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{status_path}: status 根必须为对象")
    return data


def prepare_output(path: Path, content: str) -> Path:
    """在目标文件所在目录准备完整字节；每个 replace 仅保证单文件原子性。"""
    if path.exists() and not path.is_file():
        raise ValueError(f"归档输出目标不是普通文件：{path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                     suffix=".archive-tmp", delete=False) as handle:
        temporary = Path(handle.name)
        try:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise
    return temporary


def atomic_write(path: Path, content: str) -> None:
    temporary = prepare_output(path, content)
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def write_status(req_root: Path, data: dict) -> None:
    atomic_write(requirement_artifact_path(req_root, "status"),
                 json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def validator_report(status_path: Path, req_root: Path) -> dict:
    """复用 reconcile 的严格校验器协议，避免另建状态判断。"""
    spec = importlib.util.spec_from_file_location("archive_reconcile", _locate_layout_dir() / "reconcile-delivery.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.run_status_validator_report(status_path, req_root, resolve_validator_script(req_root))


def governance_input_paths(req_root: Path, data: dict, extra: list[Path]) -> set[Path]:
    paths = {requirement_artifact_path(req_root, kind) for kind in
             ("status", "dependency_graph", "retrospective")}
    for sid in data.get("sub_requirements", {}):
        paths.update(requirement_artifact_path(req_root, kind, sid) for kind in
                     ("solution_design", "verification", "ui_truth_index", "visual_acceptance"))
    ad = find_ai_delivery_dir(req_root)
    if ad is not None:
        paths.update((ad / "meta/project-binding.json", ad / "meta/workflow-policy.json"))
    paths.update(extra)
    return paths


def input_snapshot(req_root: Path, data: dict, extra: list[Path]) -> dict[Path, str | None]:
    paths = governance_input_paths(req_root, data, extra)
    paths.add(retrospective_index_path(req_root, data.get("requirement_id", "")))
    return {p: snapshot_digest(p) for p in paths}


def snapshot_digest(path: Path) -> str | None:
    if path.is_file():
        return hashlib.sha256(path.read_bytes()).hexdigest()
    # absent 绑定不存在；目录重新出现同样属于漂移。
    return "not-a-file" if path.exists() else None


def verification_reference_snapshot(req_root: Path, data: dict, selected: str) -> dict[Path, str | None]:
    """共享校验通过后，以 v2 合同原有 hash/absence 绑定实际输入和原生报告。"""
    load_workflow_policy(req_root)
    from verification_contract import START, fingerprint, parse_verification_v2

    ad = find_ai_delivery_dir(req_root)
    root = repo_root_from_ai_delivery_dir(ad) if ad is not None else req_root
    references: dict[Path, str | None] = {}
    for sid, entry in data.get("sub_requirements", {}).items():
        # 与共享校验器的验证材料适用范围保持一致；草稿模板不是归档前置。
        if sid != selected and entry.get("status") not in {"merged", "archived"}:
            continue
        if sid != selected and entry.get('status') == 'archived' and 'archive_evidence' in entry:
            continue
        verification = requirement_artifact_path(req_root, "verification", sid)
        # 其他切片可处于尚未产出合同或只读历史阶段；声明了 v2 的合同严格解析。
        if sid != selected and (not verification.is_file() or START not in verification.read_text(encoding="utf-8")):
            continue
        contract = parse_verification_v2(verification)
        entries = list(contract["inputs"])
        for check in contract["checks"]:
            # 共享合同只消费 passed 检查的原生证据；其他结果不新增门禁。
            if check.get("result") == "passed":
                entries.extend(check["evidence"])
        for entry in entries:
            current = fingerprint(root, entry["path"])
            path = root / entry["path"]
            expected = entry["sha256"]
            if current.get("sha256") != expected:
                raise ValueError(f"归档输入发生版本漂移：{path}；请重新校验后重试")
            references[path] = expected
    return references


def assert_unchanged(snapshot: dict[Path, str | None | dict]) -> None:
    for path, expected in snapshot.items():
        if isinstance(expected, dict):
            from evidence_identity import file_identity
            root = Path(expected['repo_root'])
            try:
                unchanged = file_identity(root, path) == expected['identity']
            except (OSError, ValueError, RuntimeError) as exc:
                raise ValueError(f'归档输入发生版本漂移：{path}；{exc}') from exc
            if not unchanged:
                raise ValueError(f'归档输入发生版本漂移：{path}；请重新校验后重试')
            continue
        current = snapshot_digest(path)
        if current != expected:
            raise ValueError(f"归档输入发生版本漂移：{path}；保留当前状态，请重新校验后重试")


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


def delivery_report_content(
    req_root: Path, data: dict, now: datetime.datetime, template: str
) -> str:
    req_id = data.get("requirement_id", "<req-id>")
    subreqs = data.get("sub_requirements", {})

    rows: list[str] = []
    for sid in sorted(subreqs):
        entry = subreqs[sid]
        subreq_dir = requirement_subdir(req_root, sid)
        canonical_root = Path(os.path.relpath(subreq_dir, req_root)).as_posix() + "/"
        verification_path = requirement_artifact_path(req_root, "verification", sid)
        verification = Path(os.path.relpath(verification_path, req_root)).as_posix() if verification_path.is_file() else "-"
        rows.append(f"| {sid} | {entry.get('status', '-')} | {canonical_root} | {verification} |")

    rendered = (
        template.replace("<req-id>", req_id)
        .replace("<archived_at>", now.isoformat())
        .replace("<subreq_count>", str(len(subreqs)))
        .replace("<subreq_rows>", "\n".join(rows))
    )
    return rendered


def render_delivery_report(req_root: Path, data: dict, now: datetime.datetime, template: str) -> Path:
    out = requirement_artifact_path(req_root, "delivery_report")
    atomic_write(out, delivery_report_content(req_root, data, now, template))
    return out


def _table_cells(line: str) -> list[str]:
    if not line.lstrip().startswith("|"):
        return []
    cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
    return cells if len(cells) >= 6 else []


def _entry_from_cells(cells: list[str]) -> dict[str, str]:
    """Parse a v2 problem-map row after schema validation."""
    entry = {
        "id": cells[0],
        "trigger": cells[1],
        "scenario": cells[2],
        "path": cells[3],
        "knowledge_type": "",
        "reuse_scope": "",
        "index_decision": "",
        "confidence": "",
        "importance": "",
        "status": "",
        "details": "",
    }
    (
        entry["knowledge_type"],
        entry["reuse_scope"],
        entry["index_decision"],
        entry["confidence"],
        entry["importance"],
        entry["status"],
        entry["details"],
    ) = cells[4:11]
    return entry


def is_indexable_entry(entry: dict[str, str]) -> bool:
    """Return whether AI-declared metadata qualifies a problem for routing."""
    return (
        entry.get("knowledge_type", "").lower() in INDEXABLE_KNOWLEDGE_TYPES
        and entry.get("reuse_scope", "").lower() in INDEXABLE_REUSE_SCOPES
        and entry.get("index_decision", "").lower() in INDEXABLE_INDEX_DECISIONS
        and entry.get("confidence", "").lower() in INDEXABLE_CONFIDENCE
        and entry.get("importance", "").lower() in INDEXABLE_IMPORTANCE
    )


def indexable_entries(entries: list[dict[str, str]]) -> list[dict[str, str]]:
    return [entry for entry in entries if is_indexable_entry(entry)]


def _retrospective_prose(lines: list[str]) -> list[tuple[int, str]]:
    """Keep line locations, excluding fenced examples and HTML comment bodies."""
    result = []
    fence_char = ""
    fence_size = 0
    in_comment = False
    for number, raw in enumerate(lines, 1):
        fence = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", raw)
        if fence_char:
            if re.fullmatch(r" {0,3}" + re.escape(fence_char) + "{" + str(fence_size) + r",}\s*", raw):
                fence_char = ""
            continue
        if fence and not in_comment:
            fence_char, fence_size = fence.group(1)[0], len(fence.group(1))
            continue
        # Stable explicit anchors survive; comments are not prose headings.
        visible = ""
        rest = raw
        while rest:
            if in_comment:
                _, found, rest = rest.partition("-->")
                if not found:
                    break
                in_comment = False
            else:
                before, found, rest = rest.partition("<!--")
                visible += before
                if not found:
                    break
                in_comment = True
        result.append((number, visible))
    return result


def retrospective_detail_anchor(details: str) -> str | None:
    """Read the one local Markdown destination used by validation and routing."""
    links = re.findall(
        r"\]\(\s*<?(#[^<>\s)]+)>?(?:\s+[\"\x27][^\"\x27]*[\"\x27])?\s*\)",
        details,
    )
    return links[0][1:] if len(links) == 1 else None


class _RetrospectiveAnchors(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.anchors: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            self.anchors.extend(dict.fromkeys(
                value for key, value in attrs if key in {"id", "name"} and value
            ))


def validate_retrospective_structure(
    retrospective: Path, lines: list[str], entries: list[dict[str, str]]
) -> None:
    """Objective structure only; never infer source coverage or causal truth."""
    def fail(number: int, message: str) -> None:
        raise SystemExit(f"ERROR: {retrospective}:{number}: {message}")

    for marker in (RETROSPECTIVE_INDEX_START, RETROSPECTIVE_INDEX_END):
        locations = [i for i, line in enumerate(lines, 1) if line.strip() == marker]
        if len(locations) != 1:
            fail(locations[-1] if locations else 1,
                 "exactly one pair of problem-index:v2 markers is required")
    start = lines.index(RETROSPECTIVE_INDEX_START)
    end = lines.index(RETROSPECTIVE_INDEX_END)
    if start >= end:
        fail(end + 1, "problem-index markers are out of order")
    row_locations = {}
    for number in range(start + 1, end):
        cells = _table_cells(lines[number])
        if not cells or not cells[0].startswith("RET-"):
            continue
        problem_id = cells[0]
        if not re.fullmatch(r"RET-\d{3,}", problem_id):
            fail(number + 1, f"{problem_id}: invalid problem ID")
        if problem_id in row_locations:
            fail(number + 1, f"{problem_id}: duplicate problem-map row")
        row_locations[problem_id] = number + 1

    prose = _retrospective_prose(lines)
    details = {}
    explicit = {}
    section_headings = []
    anchor_reader = _RetrospectiveAnchors()

    def leading_anchor_start(index: int, heading_number: int) -> int:
        start = heading_number
        for prior_number, prior_line in reversed(prose[:index]):
            if not prior_line.strip():
                continue
            # Reserve standalone anchors preceding a heading for that section.
            if re.search(r"<a\b", prior_line, re.I) and not re.sub(r"</?a\b[^>]*>", "", prior_line, flags=re.I).strip():
                start = prior_number
            else:
                break
        return start
    for index, (number, line) in enumerate(prose):
        anchor_reader.anchors.clear()
        anchor_reader.feed(line + "\n")
        for anchor in anchor_reader.anchors:
            if anchor in explicit:
                fail(number, f"duplicate detail anchor #{anchor}")
            explicit[anchor] = number
        heading = re.match(r"^ {0,3}#{1,6}\s+(.+?)(?:\s+#+)?\s*$", line)
        if not heading:
            continue
        title = heading.group(1)
        level = len(line.lstrip().split()[0])
        section_headings.append((number, level, leading_anchor_start(index, number)))
        # Detect known revision-batch containers, not every mention or date.
        batch_title = re.sub(r"^(?:\d+[.)]\s*|\d{4}-\d{1,2}-\d{1,2}\s*[:|\-]?\s*)+", "", title)
        if re.match(
            r"(?:this (?:round|session)(?:'s)? (?:additions|findings)|"
            r"(?:supplemental|additional|appended) (?:retrospective|review)|"
            r"retrospective addendum|"
            r"\u672c\u8f6e\u65b0\u589e|\u8ffd\u52a0\u590d\u76d8|\u8865\u5145\u590d\u76d8|\u8865\u5ba1)",
            batch_title, re.I,
        ):
            fail(number, f"revision-batch retrospective section is forbidden: {title}")
        match = re.match(r"(RET-\d{3,})(?=$|[\s:\uff1a])", title)
        if not match:
            continue
        problem_id = match.group(1)
        if problem_id in details:
            fail(number, f"{problem_id}: duplicate detail record")
        if problem_id not in row_locations:
            fail(number, f"{problem_id}: orphan detail without problem-map row")
        # GitHub-style heading anchor for existing ledgers. Explicit anchors are
        # preferred for new records, so title edits do not invalidate links.
        slug = re.sub(r"[^\w\- ]", "", title.lower()).replace(" ", "-")
        preceding = leading_anchor_start(index, number)
        details[problem_id] = (number, slug, preceding, level)

    for entry in entries:
        problem_id = entry["id"]
        row = row_locations[problem_id]
        if problem_id not in details:
            fail(row, f"{problem_id}: missing detail record")
        number, slug, preceding, level = details[problem_id]
        anchor = retrospective_detail_anchor(entry["details"])
        if anchor is None:
            fail(row, f"{problem_id}: Details must link to its own local detail anchor")
        next_detail = min(
            [prior for n, depth, prior in section_headings if n > number and depth <= level]
            + [prior for n, _, prior, _ in details.values() if n > number],
            default=len(lines) + 1,
        )
        # An explicit stable anchor immediately before or within its record is
        # valid. Do not accept links to another RET or a generic summary heading.
        at = explicit.get(anchor)
        if anchor != slug and not (at is not None and (preceding <= at < next_detail)):
            fail(row, f"{problem_id}: missing or mismatched detail anchor #{anchor}")


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
        if (
            LEGACY_RETROSPECTIVE_INDEX_START in lines
            and LEGACY_RETROSPECTIVE_INDEX_END in lines
        ):
            raise SystemExit(
                "ERROR: retrospective uses legacy problem-map schema v1; "
                "AI must upgrade retrospective.md to problem-index:v2 before archive"
            )
        meaningful = [
            line.strip()
            for line in lines
            if line.strip()
            and not RETROSPECTIVE_REVIEWED_AT_RE.fullmatch(line.strip())
        ]
        if not meaningful:
            return []
        raise SystemExit(
            "ERROR: retrospective is missing the stable problem-index markers"
        )

    if lines.count(RETROSPECTIVE_INDEX_START) != 1 or lines.count(RETROSPECTIVE_INDEX_END) != 1:
        raise SystemExit(f"ERROR: {retrospective}:{start + 1}: exactly one pair of problem-index:v2 markers is required")
    header_seen = False
    entries: list[dict[str, str]] = []
    for line in lines[start + 1 : end]:
        cells = _table_cells(line)
        if not cells:
            continue
        if cells[0].lower() in {"problem", "id"}:
            if not PROBLEM_MAP_REQUIRED_COLUMNS.issubset(
                {cell.lower() for cell in cells}
            ):
                raise SystemExit(
                    "ERROR: retrospective uses legacy problem-map schema; "
                    "AI must add knowledge_type, reuse_scope, index_decision, "
                    "confidence, and importance before archive"
                )
            header_seen = True
            continue
        if not cells[0].startswith("RET-"):
            continue
        if len(cells) < 11:
            raise SystemExit(
                "ERROR: retrospective uses legacy problem-map schema; AI must "
                "upgrade every problem row to the v2 qualification columns before archive"
            )
        entries.append(_entry_from_cells(cells))
    if not header_seen:
        raise SystemExit(
            "ERROR: retrospective problem map is missing the v2 qualification header; "
            "AI must upgrade retrospective.md before archive"
        )
    validate_retrospective_structure(retrospective, lines, entries)
    return entries


def validate_retrospective_reviewed_at(
    retrospective: Path, archive_at: datetime.datetime
) -> None:
    """Require a parseable review marker from the same calendar day as archive."""
    try:
        text = retrospective.read_text(encoding="utf-8")
    except OSError as exc:
        raise SystemExit(f"ERROR: cannot read retrospective {retrospective}: {exc}")

    matches = list(RETROSPECTIVE_REVIEWED_AT_RE.finditer(text))
    if len(matches) != 1:
        raise SystemExit(
            "ERROR: retrospective must contain exactly one marker "
            "<!-- ai-delivery-retrospective:reviewed-at:<ISO-8601> -->"
        )
    raw = matches[0].group("value")
    try:
        parsed = datetime.datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise SystemExit(
            f"ERROR: retrospective reviewed-at marker is not valid ISO-8601: {raw}"
        ) from exc
    if parsed.date() != archive_at.date():
        raise SystemExit(
            "ERROR: retrospective reviewed-at date "
            f"{parsed.date().isoformat()} is stale for archive date "
            f"{archive_at.date().isoformat()}; update retrospective.md first"
        )


def retrospective_ledger_path(req_root: Path, req_id: str) -> Path:
    return requirement_artifact_path(req_root, "retrospective")


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
    req_root: Path,
    req_id: str,
    archive_at: datetime.datetime,
    template_path: Path | None,
    require_index_template: bool,
) -> str | None:
    """Validate ledger/index inputs before archive state or bytes are changed."""
    retrospective = retrospective_ledger_path(req_root, req_id)
    if not retrospective.is_file():
        raise SystemExit(
            f"ERROR: requirement retrospective is required before archive: {retrospective}"
        )
    validate_retrospective_reviewed_at(retrospective, archive_at)
    entries = read_retrospective_entries(retrospective)
    if not indexable_entries(entries) or not require_index_template:
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


def retrospective_index_content(
    req_root: Path,
    req_id: str,
    archived_at: datetime.datetime,
    template: str | None,
) -> tuple[Path, str] | None:
    """准备索引内容，保留其他需求的路由。"""
    retrospective = retrospective_ledger_path(req_root, req_id)
    if not retrospective.is_file():
        return None

    entries = read_retrospective_entries(retrospective)
    if not entries:
        return None
    entries = indexable_entries(entries)

    index = retrospective_index_path(req_root, req_id)
    existing = index.read_text(encoding="utf-8") if index.is_file() else ""
    if not entries and not existing:
        return None
    rows = []
    for entry in entries:
        # read_retrospective_entries already validated this local destination.
        anchor = "#" + retrospective_detail_anchor(entry["details"])
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
    return index, content


def register_retrospective_index(req_root: Path, req_id: str, archived_at: datetime.datetime, template: str | None) -> Path | None:
    with archive_lock(req_root):
        prepared = retrospective_index_content(req_root, req_id, archived_at, template)
        if prepared is None:
            return None
        index, content = prepared
        atomic_write(index, content)
        return index


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--req-root", type=Path, required=True, help="Requirement root (parent of sub-requirements/)")
    parser.add_argument("--subreq", type=str, required=True, help="Sub-requirement id to archive")
    parser.add_argument("--now", type=str, default=None, help="Override archive timestamp (ISO8601, for tests)")
    parser.add_argument("--no-status-write", action="store_true", help="Preview the archive action without changing status.json")
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
    try:
        # 预览不得创建锁、临时文件、目录或任何归档输出。
        with contextlib.nullcontext() if args.no_status_write else archive_lock(req_root):
            return archive_action(args, req_root)
    except (OSError, UnicodeDecodeError, ValueError, SystemExit) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


def archive_action(args: argparse.Namespace, req_root: Path) -> int:
    status_path = requirement_artifact_path(req_root, "status")
    loaded_status_hash = hashlib.sha256(status_path.read_bytes()).hexdigest()
    data = load_status(req_root)
    subreq_dir = requirement_subdir(req_root, args.subreq)
    if not subreq_dir.is_dir():
        raise ValueError(f"sub-requirement dir not found: {subreq_dir}")
    entry = (data.get("sub_requirements") or {}).get(args.subreq)
    if not isinstance(entry, dict) or entry.get("status") != "merged":
        raise ValueError(f"{args.subreq}: only merged sub-requirements may be archived；历史终态不自动重置")
    now = datetime.datetime.fromisoformat(args.now) if args.now else datetime.datetime.now(datetime.timezone.utc)
    req_id = data.get("requirement_id", "")
    extra = [p for p in (args.delivery_report_template, args.retrospective_index_template) if p is not None]
    snapshot = input_snapshot(req_root, data, extra)
    if snapshot[status_path] != loaded_status_hash:
        raise ValueError(f"归档输入发生版本漂移：{status_path}；请重新校验后重试")
    report = validator_report(status_path, req_root)
    if not report["valid"]:
        raise ValueError("归档治理校验失败：" + "; ".join(report["errors"]))
    assert_unchanged(snapshot)
    reference_snapshot = verification_reference_snapshot(req_root, data, args.subreq)
    snapshot.update(reference_snapshot)
    from evidence_identity import archive_evidence, validate_identity
    ad = find_ai_delivery_dir(req_root)
    root = repo_root_from_ai_delivery_dir(ad) if ad is not None else req_root
    consumed = report.get('consumed_files')
    if consumed is None:
        raise ValueError('归档需要支持 consumed_files 的当前共享校验器；请升级已配置入口')
    elif not isinstance(consumed, list):
        raise ValueError('status validator consumed_files 必须为列表')
    else:
        for identity in consumed:
            path = validate_identity(root, identity)
            reference_snapshot[path] = {'repo_root': str(root), 'identity': identity}
        snapshot.update(reference_snapshot)
    assert_unchanged(snapshot)
    # 历史终态可只读；新转换仍须具备规范设计和验证材料。
    for kind in ("solution_design", "verification"):
        evidence = requirement_artifact_path(req_root, kind, args.subreq)
        if not evidence.is_file():
            raise ValueError(f"新归档缺少规范证据 {kind}: {evidence}")

    will_complete = all_archived_after(data, args.subreq)
    report_template = None
    if will_complete and not args.no_delivery_report:
        if args.delivery_report_template is None:
            raise ValueError("final archive requires --delivery-report-template with localized content")
        report_template = load_delivery_report_template(args.delivery_report_template)
    index_template = preflight_retrospective_index(req_root, req_id, now,
        args.retrospective_index_template, will_complete)
    entry["status"] = "archived"
    entry['archive_evidence'] = archive_evidence(req_root, args.subreq, entry)
    outputs: list[tuple[Path, str]] = []
    messages = []
    if report_template is not None:
        target = requirement_artifact_path(req_root, "delivery_report")
        outputs.append((target, delivery_report_content(req_root, data, now, report_template)))
        messages.append(f"DELIVERY_REPORT {target}")
    if will_complete:
        prepared = retrospective_index_content(req_root, req_id, now, index_template)
        if prepared is not None:
            outputs.append(prepared)
            messages.append(f"RETROSPECTIVE_INDEX {prepared[0]}")
        skipped = [e["id"] for e in read_retrospective_entries(retrospective_ledger_path(req_root, req_id)) if not is_indexable_entry(e)]
        if skipped:
            messages.append(f"RETROSPECTIVE_INDEX_SKIPPED {len(skipped)} (not explicitly qualified: {', '.join(skipped)})")
    # 所有目标先预检，再准备全部输出；故障时 status 仍保持 merged，可原命令重试。
    targets = [path for path, _ in outputs] + [status_path]
    if len({p.resolve() for p in targets}) != len(targets):
        raise ValueError("归档输出路径与 status/index/report 冲突")
    protected = {p.resolve() for p in governance_input_paths(req_root, data, extra) if p != status_path}
    protected.update(p.resolve() for p in reference_snapshot)
    if any(p.resolve() in protected for p in targets):
        raise ValueError("归档输出路径覆盖治理输入")
    for target in targets:
        if target.exists() and not target.is_file():
            raise ValueError(f"归档输出目标不是普通文件：{target}")
    if args.no_status_write:
        assert_unchanged(snapshot)
        print(f"WOULD_ARCHIVE {args.subreq} (read-only preview)")
        return 0
    staged: list[tuple[Path, Path]] = []
    try:
        for target, content in outputs:
            staged.append((target, prepare_output(target, content)))
        staged.append((status_path, prepare_output(status_path, json.dumps(data, indent=2, ensure_ascii=False) + "\n")))
        assert_unchanged(snapshot)
        for target, temporary in staged:
            # 仅约束合作入口；直接修改文件的外部进程仍需写前核对。
            assert_unchanged(snapshot)
            os.replace(temporary, target)
            snapshot.pop(target, None)
    finally:
        for _, temporary in staged:
            temporary.unlink(missing_ok=True)
    for message in messages:
        print(message)
    print(f"ARCHIVED {args.subreq} (status updated in place)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
