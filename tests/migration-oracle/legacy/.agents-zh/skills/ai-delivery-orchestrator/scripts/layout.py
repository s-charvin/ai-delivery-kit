#!/usr/bin/env python3
"""Canonical artifact-layout resolver for ai-delivery-kit.

Single source of truth for *where* governed artifacts live under `.ai-delivery/`.
The skill-layer orchestrator (reconcile-delivery.py) reads this contract from
`project-binding.json`. The optional coordination MCP service may read the same
layout JSON when bridging client repos — it is not vendored in this kit.

The layout is declared once in `.ai-delivery/meta/project-binding.json`
under the `layout` key. Every path below is *relative to* `ai_delivery_path`
(also from that file, default `.ai-delivery`).

Artifact kinds come in two scopes:
  * project-level       (shared by all requirements): retrospective_index, ...
  * requirement-level   (no sub-requirement): status, requirement, ...
  * sub-requirement-level: solution_design, verification, visual_acceptance, ...

Reconcile, validators, and archive scripts resolve paths through this module.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shlex
import sys
from pathlib import Path

# Fallback layout used when project-binding.json is absent (e.g. unit tests).
DEFAULT_LAYOUT: dict = {
    "requirement_root": "requirements/{req_id}",
    "sub_requirement_dir": "requirements/{req_id}/sub-requirements/{sr_id}",
    "project_artifacts": {
        "retrospective_index": "retrospectives/index.md",
    },
    "requirement_artifacts": {
        "status": "requirements/{req_id}/status.json",
        "requirement": "requirements/{req_id}/requirement.md",
        "breakdown_summary": "requirements/{req_id}/breakdown-summary.md",
        "global_rules": "requirements/{req_id}/global-rules.md",
        "dependency_graph": "requirements/{req_id}/dependency-graph.json",
        "progress": "requirements/{req_id}/progress.md",
        "todo": "requirements/{req_id}/todo.md",
        "delivery_report": "requirements/{req_id}/delivery-report.md",
        "retrospective": "requirements/{req_id}/retrospective.md",
    },
    "sub_requirement_artifacts": {
        "requirement_slice": "requirements/{req_id}/sub-requirements/{sr_id}/requirement-slice.md",
        "decisions": "requirements/{req_id}/sub-requirements/{sr_id}/decisions.md",
        "readme": "requirements/{req_id}/sub-requirements/{sr_id}/README.md",
        "traceability": "requirements/{req_id}/sub-requirements/{sr_id}/traceability.json",
        "solution_design": "requirements/{req_id}/sub-requirements/{sr_id}/design.md",
        "verification": "requirements/{req_id}/sub-requirements/{sr_id}/verification.md",
        "visual_acceptance": "requirements/{req_id}/sub-requirements/{sr_id}/visual-acceptance.json",
        "ui_truth_index": "requirements/{req_id}/sub-requirements/{sr_id}/contracts/ui-truth-index.json",
    },
}

DEFAULT_AI_DELIVERY_PATH = ".ai-delivery"


class DeliveryInputError(ValueError):
    """携带恢复位置的治理输入错误。"""

    def __init__(self, path: Path, category: str, message: str):
        self.path = str(path)
        self.category = category
        super().__init__(f"{path}: {message}")


def diagnostic(path: Path | str, category: str, message: str, scope="requirement") -> dict:
    return {"path": str(path), "category": category, "scope": scope,
            "recovery": recovery_options(Path(path)) if category == "compatibility" else "修复具体输入问题后重新执行；当前证据或批准仍须满足现行校验。", "message": message}



def upgrade_guide() -> Path:
    return Path(__file__).resolve().parent.parent / "references/version-upgrade.md"


def recovery_options(path: Path) -> str:
    ad = find_ai_delivery_dir(path)
    if ad is not None:
        root = repo_root_from_ai_delivery_dir(ad)
    elif path.is_dir():
        root = path
    elif path.is_file():
        root = path.parent
    else:
        root = None
    reset_option = "--reset-data"
    if ad is not None:
        relative = ad.absolute().relative_to(root.absolute()).as_posix()
        if relative != DEFAULT_AI_DELIVERY_PATH:
            reset_option += "=" + relative
    target = str(root.absolute()) if root is not None else "<project-root>"
    unresolved = "项目根无法确定，请先将 <project-root> 替换为实际项目根。" if root is None else ""
    return ("你可以自行选择：A. 自行备份后，将升级指引交给你的 AI 或手动迁移需要继续使用的数据。"
            " B. 显式备份重建：ai-delivery init --upgrade " + shlex.quote(reset_option) + " "
            + shlex.quote(target) + "。" + unresolved
            + "普通入口不会迁移或重置数据。迁移提示词和备份说明：" + str(upgrade_guide()))


def compatibility_error(path: Path, field: str, actual: object, expected: object) -> DeliveryInputError:
    return DeliveryInputError(path, "compatibility",
        f"不支持的交付数据格式：{field} 实际={json.dumps(actual, ensure_ascii=False)}；"
        f"要求={json.dumps(expected, ensure_ascii=False)}。" + recovery_options(path))


def require_current_format(path: Path, data: dict, field: str, expected: object) -> None:
    actual = data.get(field)
    if type(actual) is not type(expected) or actual != expected:
        raise compatibility_error(path, field, actual, expected)


def reject_removed_fields(path: Path, data: object) -> None:
    removed = {"legacy_terminal_slices", "migration_source_sha256", "ui_contract_exempt",
               "no_design_client", "design_mode", "design_approved"}
    if isinstance(data, dict):
        for key, value in data.items():
            if key == "participation" and value == "no_design_client":
                raise compatibility_error(path, key, value, "removed; use ui_truth_mode and the canonical design contract")
            if key in removed:
                raise compatibility_error(path, key, value, "removed; field must be absent")
            reject_removed_fields(path, value)
    elif isinstance(data, list):
        for value in data:
            reject_removed_fields(path, value)


def _safe_identifier(value: object) -> bool:
    return (isinstance(value, str) and bool(value) and value not in {".", ".."}
            and "/" not in value and "\\" not in value
            and all(ord(char) >= 32 for char in value))


def _confined_path(path: Path, root: Path) -> Path:
    """检查解析后的实际目标，同时保留词法路径以追踪 binding 权威。"""
    try:
        resolved = path.resolve()
        governed = root.resolve()
    except (OSError, RuntimeError) as exc:
        raise DeliveryInputError(path, "path", f"无法解析治理路径：{exc}") from exc
    if not resolved.is_relative_to(governed):
        raise DeliveryInputError(path, "path", f"治理产物实际目标超出治理根：{root}")
    return path.absolute()


def _read_json_object(path: Path, category: str) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DeliveryInputError(path, category, f"无法读取 JSON：{exc}") from exc
    if not isinstance(data, dict):
        raise DeliveryInputError(path, category, "JSON 根必须为对象")
    return data


def _validate_relative_template(value: object, path: Path) -> None:
    if not isinstance(value, str) or not value or Path(value).is_absolute() or ".." in Path(value).parts:
        raise DeliveryInputError(path, "binding", "布局路径必须为非空且不含 .. 的相对路径")
    if any(token not in {"req_id", "sr_id", "unit_id", "ts"} for token in re.findall(r"\{([^{}]*)\}", value)):
        raise DeliveryInputError(path, "binding", "不支持的布局占位符")
    try:
        value.format(req_id="REQ", sr_id="SR", unit_id="UNIT", ts="TS")
    except (KeyError, ValueError, IndexError, AttributeError, TypeError) as exc:
        raise DeliveryInputError(path, "binding", f"不支持的布局占位符：{exc}") from exc


def find_ai_delivery_dir(start: Path | str) -> Path | None:
    """Walk up from `start` to locate the `.ai-delivery` directory.

    Used by callers that only have a requirement/sub-requirement path and need
    the governed root. Metadata presence establishes the boundary even when
    its binding is missing or a metadata link is dangling.
    """
    p = Path(start)
    for cand in [p, *p.parents]:
        metadata = (cand / "meta" / name for name in ("project-binding.json", "workflow-policy.json"))
        if cand.name == DEFAULT_AI_DELIVERY_PATH or any(path.exists() or path.is_symlink() for path in metadata):
            return cand
    return None


def resolve_validator_script(
    req_root: Path | str,
    validator_script: Path | str | None = None,
    kit_root: Path | str | None = None,
) -> Path | None:
    """Resolve the single canonical validate-delivery-status.py path.

    Order: explicit override → seeded ``.ai-delivery/scripts/`` → kit-relative
    fallback (so the kit repo's own tests resolve without bootstrap).
    """
    if validator_script is not None:
        p = Path(validator_script)
        return p.resolve() if p.is_file() else None
    ad_dir = find_ai_delivery_dir(req_root)
    if ad_dir is not None:
        cand = ad_dir / "scripts" / "validate-delivery-status.py"
        if cand.is_file():
            return cand.resolve()
    root = Path(kit_root) if kit_root is not None else Path(__file__).resolve().parents[4]
    cand = root / "scripts" / "validate-delivery-status.py"
    if cand.is_file():
        return cand.resolve()
    return None


def _is_fs_root(path: Path) -> bool:
    return path.parent == path


def _safe_is_file(path: Path) -> bool:
    try:
        return path.is_file()
    except OSError:
        return False


def _safe_is_dir(path: Path) -> bool:
    try:
        return path.is_dir()
    except OSError:
        return False


def _find_binding(repo_root: Path) -> Path | None:
    """Locate project-binding.json.

    The meta dir is always ``<root>/<ai_delivery_path>/meta/``, but
    ``ai_delivery_path`` may be overridden, so probe the default location
    plus one level of immediate subdirectories (bounded, no deep walk).
    Never scan the filesystem root — walking ``/`` hits unreadable mounts.
    """
    root = Path(repo_root)
    if _is_fs_root(root):
        return None
    default_pb = root / DEFAULT_AI_DELIVERY_PATH / "meta" / "project-binding.json"
    if default_pb.exists():
        return default_pb
    try:
        children = list(root.iterdir())
    except OSError:
        return None
    for child in children:
        if child.name == ".ai-delivery-backups":
            continue
        if not _safe_is_dir(child):
            continue
        cand = child / "meta" / "project-binding.json"
        if cand.exists():
            return cand
    return None


def _read_binding(repo_root: Path) -> dict | None:
    pb = _find_binding(repo_root)
    if pb is None:
        return None
    data = _read_json_object(pb, "binding")
    _merge_layout(data, pb)
    _validate_binding_location(data, pb.parent.parent, repo_root)
    return data


def _validate_binding_location(data: dict, ad_dir: Path, repo_root: Path | None = None) -> None:
    """同一 binding 的物理位置与声明位置必须使用同一治理根。"""
    declared = Path(data.get("ai_delivery_path", DEFAULT_AI_DELIVERY_PATH))
    actual = ad_dir.absolute()
    if repo_root is not None:
        expected = Path(repo_root).absolute() / declared
        matches = actual == expected
    else:
        matches = actual.parts[-len(declared.parts):] == declared.parts
    if not matches:
        raise DeliveryInputError(ad_dir / "meta/project-binding.json", "binding", "binding 实际位置与声明的 ai_delivery_path 不一致")
    if repo_root is not None:
        _confined_path(ad_dir, Path(repo_root))


def load_layout(repo_root: Path) -> dict:
    """Read the `layout` section from project-binding.json, else fallback."""
    data = _read_binding(repo_root)
    return _merge_layout(data)


def _merge_layout(data: dict | None, path: Path | None = None) -> dict:
    """Merge a binding's layout over defaults without mutating either map."""
    path = path or Path("project-binding.json")
    if data is not None:
        require_current_format(path, data, "version", 3)
        reject_removed_fields(path, data)
        if "ai_delivery_path" in data:
            _validate_relative_template(data["ai_delivery_path"], path)
        if "layout" in data and not isinstance(data["layout"], dict):
            raise DeliveryInputError(path, "binding", "layout 必须为对象")
    if isinstance(data, dict) and isinstance(data.get("layout"), dict):
        configured = data["layout"]
        for key, value in configured.items():
            if key not in DEFAULT_LAYOUT:
                raise DeliveryInputError(path, "binding", f"不支持的 layout 键：{key}")
            if isinstance(DEFAULT_LAYOUT[key], dict):
                if not isinstance(value, dict):
                    raise DeliveryInputError(path, "binding", f"{key} 必须为对象")
                for kind, template in value.items():
                    if kind not in DEFAULT_LAYOUT[key]:
                        raise DeliveryInputError(path, "binding", f"不支持的 artifact：{kind}")
                    _validate_relative_template(template, path)
            else:
                _validate_relative_template(value, path)
        # Merge new optional maps so older bindings gain the canonical defaults
        # without changing their existing paths.
        merged = dict(DEFAULT_LAYOUT)
        for key, value in configured.items():
            if isinstance(value, dict) and isinstance(merged.get(key), dict):
                merged[key] = {**merged[key], **value}
            else:
                merged[key] = value
        return merged
    return dict(DEFAULT_LAYOUT)


def load_layout_from_ai_delivery_dir(ai_delivery_dir: Path | str) -> dict:
    """Read a binding directly when its configured path is nested or custom."""
    path = Path(ai_delivery_dir) / "meta" / "project-binding.json"
    data = _read_json_object(path, "binding")
    merged = _merge_layout(data, path)
    if data is not None:
        _validate_binding_location(data, Path(ai_delivery_dir))
    return merged


def ai_delivery_path(repo_root: Path) -> Path:
    data = _read_binding(repo_root)
    if isinstance(data, dict):
        p = data.get("ai_delivery_path")
        if isinstance(p, str) and p:
            return Path(repo_root) / p
    return Path(repo_root) / DEFAULT_AI_DELIVERY_PATH


def _fmt(template: str, req_id: str, sr_id: str | None, unit_id: str | None, ts: str | None) -> str:
    # str.format tolerates extra kwargs, so always pass all four.
    for key, value in (("req_id", req_id), ("sr_id", sr_id), ("unit_id", unit_id), ("ts", ts)):
        if value is not None and not (key == "req_id" and value == "") and not _safe_identifier(value):
            raise DeliveryInputError(Path("project-binding.json"), "binding", f"{key} 必须为非路径 ID")
    rendered = template.format(req_id=req_id, sr_id=sr_id, unit_id=unit_id, ts=ts)
    if Path(rendered).is_absolute() or ".." in Path(rendered).parts:
        raise DeliveryInputError(Path("project-binding.json"), "binding", "渲染后的产物路径超出治理目录")
    return rendered


def artifact_path(
    repo_root: Path | str,
    kind: str,
    req_id: str = "",
    sr_id: str | None = None,
    unit_id: str | None = None,
    ts: str | None = None,
) -> Path:
    """Resolve the canonical on-disk path of an artifact kind.

    `kind` must be one of the keys in the configured project, requirement, or
    sub-requirement artifact maps. Project-level kinds ignore all identifiers;
    requirement-level kinds ignore sr_id/unit_id/ts; sub-requirement kinds
    require sr_id for sub-requirement artifacts.
    """
    layout = load_layout(Path(repo_root))
    project_map = layout.get("project_artifacts", {})
    req_map = layout.get("requirement_artifacts", {})
    sub_map = layout.get("sub_requirement_artifacts", {})
    if kind in project_map:
        rel = _fmt(project_map[kind], req_id, sr_id, unit_id, ts)
    elif kind in req_map:
        rel = _fmt(req_map[kind], req_id, sr_id, unit_id, ts)
    elif kind in sub_map:
        rel = _fmt(sub_map[kind], req_id, sr_id, unit_id, ts)
    else:
        raise KeyError(f"unknown artifact kind: {kind!r}")
    ad_dir = ai_delivery_path(Path(repo_root))
    return _confined_path(ad_dir / rel, ad_dir)


def artifact_path_from_ai_delivery_dir(
    ai_delivery_dir: Path | str,
    kind: str,
    req_id: str = "",
    sr_id: str | None = None,
    unit_id: str | None = None,
    ts: str | None = None,
) -> Path:
    """Resolve an artifact from an already located governed directory."""
    layout = load_layout_from_ai_delivery_dir(ai_delivery_dir)
    project_map = layout.get("project_artifacts", {})
    req_map = layout.get("requirement_artifacts", {})
    sub_map = layout.get("sub_requirement_artifacts", {})
    if kind in project_map:
        rel = _fmt(project_map[kind], req_id, sr_id, unit_id, ts)
    elif kind in req_map:
        rel = _fmt(req_map[kind], req_id, sr_id, unit_id, ts)
    elif kind in sub_map:
        rel = _fmt(sub_map[kind], req_id, sr_id, unit_id, ts)
    else:
        raise KeyError(f"unknown artifact kind: {kind!r}")
    ad_dir = Path(ai_delivery_dir)
    return _confined_path(ad_dir / rel, ad_dir)


def requirement_dir(repo_root: Path | str, req_id: str) -> Path:
    layout = load_layout(Path(repo_root))
    rel = _fmt(layout["requirement_root"], req_id, None, None, None)
    ad_dir = ai_delivery_path(Path(repo_root))
    return _confined_path(ad_dir / rel, ad_dir)


def sub_requirement_dir(repo_root: Path | str, req_id: str, sr_id: str) -> Path:
    layout = load_layout(Path(repo_root))
    rel = _fmt(layout["sub_requirement_dir"], req_id, sr_id, None, None)
    ad_dir = ai_delivery_path(Path(repo_root))
    return _confined_path(ad_dir / rel, ad_dir)


def _match_ids(template: str, relative: str, path: Path) -> dict:
    if template.count("{req_id}") != 1 or template.count("{sr_id}") > 1:
        raise DeliveryInputError(path, "binding", "目录模板必须包含唯一 req_id，sr_id 不得重复")
    pattern = re.escape(template)
    for key in ("req_id", "sr_id"):
        pattern = pattern.replace(re.escape("{" + key + "}"), f"(?P<{key}>[^/]+)")
    match = re.fullmatch(pattern, relative)
    if not match:
        raise DeliveryInputError(path, "binding", "输入目录与绑定布局不一致")
    return match.groupdict()


def requirement_artifact_path(req_root: Path | str, kind: str, sr_id: str | None = None) -> Path:
    """从需求目录解析本次操作的规范 artifact；无 binding 保留默认夹具布局。"""
    req_root = Path(req_root).absolute()
    ad = find_ai_delivery_dir(req_root)
    if ad is not None:
        _confined_path(req_root, ad)
        load_layout_from_ai_delivery_dir(ad)
    if ad is None or not (ad / "meta/project-binding.json").exists():
        group = "sub_requirement_artifacts" if sr_id is not None else "requirement_artifacts"
        template = DEFAULT_LAYOUT[group][kind]
        prefix = DEFAULT_LAYOUT["requirement_root"] + "/"
        target = req_root / _fmt(template.removeprefix(prefix), req_root.name, sr_id, None, None)
        return _confined_path(target, ad or req_root)
    layout = load_layout_from_ai_delivery_dir(ad)
    ids = _match_ids(layout["requirement_root"], req_root.relative_to(ad).as_posix(), ad / "meta/project-binding.json")
    return artifact_path_from_ai_delivery_dir(ad, kind, req_id=ids["req_id"], sr_id=sr_id)


def requirement_subdir(req_root: Path | str, sr_id: str) -> Path:
    req_root = Path(req_root).absolute()
    if not _safe_identifier(sr_id):
        raise DeliveryInputError(req_root, "binding", "sr_id 必须为非路径 ID")
    ad = find_ai_delivery_dir(req_root)
    if ad is not None:
        _confined_path(req_root, ad)
        load_layout_from_ai_delivery_dir(ad)
    if ad is None or not (ad / "meta/project-binding.json").exists():
        return _confined_path(req_root / "sub-requirements" / sr_id, ad or req_root)
    layout = load_layout_from_ai_delivery_dir(ad)
    ids = _match_ids(layout["requirement_root"], req_root.relative_to(ad).as_posix(), ad / "meta/project-binding.json")
    return _confined_path(ad / _fmt(layout["sub_requirement_dir"], ids["req_id"], sr_id, None, None), ad)


def subreq_artifact_path(subreq_dir: Path | str, kind: str) -> Path:
    subreq_dir = Path(subreq_dir).absolute()
    ad = find_ai_delivery_dir(subreq_dir)
    if ad is not None:
        _confined_path(subreq_dir, ad)
        load_layout_from_ai_delivery_dir(ad)
    if ad is None or not (ad / "meta/project-binding.json").exists():
        target = subreq_dir / Path(DEFAULT_LAYOUT["sub_requirement_artifacts"][kind]).name if kind != "ui_truth_index" else subreq_dir / "contracts/ui-truth-index.json"
        return _confined_path(target, ad or subreq_dir)
    layout = load_layout_from_ai_delivery_dir(ad)
    ids = _match_ids(layout["sub_requirement_dir"], subreq_dir.relative_to(ad).as_posix(), ad / "meta/project-binding.json")
    return artifact_path_from_ai_delivery_dir(ad, kind, **ids)


DELIVERY_STATUSES = frozenset({"draft", "split_ready", "acceptance_frozen", "design_ready", "in_dev", "visual_acceptance_passed", "merged", "archived"})
DELIVERY_BLOCKERS = frozenset({
    "blocked_missing_requirement", "blocked_requirement_conflict", "blocked_dependency",
    "blocked_missing_design", "blocked_requirement_figma_conflict", "blocked_figma_conflict",
    "blocked_missing_state_code", "blocked_missing_visual_truth", "blocked_verification_failure",
    "blocked_design_mismatch", "blocked_dependency_slice", "blocked_merge_conflict",
})


def dependency_closure(seeds: set[str], deps: dict[str, list[str]]) -> set[str]:
    affected = set(seeds)
    while True:
        expanded = affected | {sid for sid, parents in deps.items() if any(p in affected for p in parents)}
        if expanded == affected:
            return affected
        affected = expanded


def inspect_delivery_inputs(status_path: Path, req_root: Path, status_data: object) -> tuple[dict[str, list[str]], list[dict]]:
    """验证调度所需输入，明确局部依赖闭包与需求级未知拓扑。"""
    issues: list[dict] = []
    deps: dict[str, list[str]] = {}
    try:
        expected = requirement_artifact_path(req_root, "status")
        if expected.resolve() != status_path.resolve():
            raise DeliveryInputError(status_path, "binding", f"status 路径与 binding 不一致；应为 {expected}")
        load_workflow_policy(req_root)
        graph_path = requirement_artifact_path(req_root, "dependency_graph")
    except DeliveryInputError as exc:
        return deps, [diagnostic(exc.path, exc.category, str(exc))]
    if not isinstance(status_data, dict):
        return deps, [diagnostic(status_path, "status", "status JSON 根必须为对象")]
    values = status_data.get("sub_requirements")
    if not isinstance(values, dict):
        return deps, [diagnostic(status_path, "status", "sub_requirements 必须为对象")]
    try:
        require_current_format(status_path, status_data, "_schema", "2.0")
        reject_removed_fields(status_path, {key: value for key, value in status_data.items() if key != "sub_requirements"})
    except DeliveryInputError as exc:
        return deps, [diagnostic(exc.path, exc.category, str(exc))]
    checkpoint = status_data.get("current_checkpoint")
    if checkpoint is not None and (not isinstance(checkpoint, str) or checkpoint not in {"CP-UI", "CP-DESIGN", "CP-002", "CP-ARCHIVE"}):
        exc = compatibility_error(status_path, "current_checkpoint", checkpoint, "CP-UI / CP-DESIGN / CP-002 / CP-ARCHIVE / null")
        issues.append(diagnostic(exc.path, exc.category, str(exc)))
    for sid, entry in values.items():
        scope = [sid]
        path = f"{status_path}#/sub_requirements/{sid}"
        if not _safe_identifier(sid):
            issues.append(diagnostic(path, "status", "子需求 ID 必须为非路径 ID", scope))
            continue
        try:
            requirement_subdir(req_root, sid)
            for kind in ("solution_design", "verification", "ui_truth_index", "visual_acceptance"):
                requirement_artifact_path(req_root, kind, sr_id=sid)
        except DeliveryInputError as exc:
            issues.append(diagnostic(exc.path, exc.category, str(exc), scope))
        if not isinstance(entry, dict):
            issues.append(diagnostic(path, "status", "子需求必须为对象", scope))
            continue
        status = entry.get("status")
        try:
            reject_removed_fields(Path(path), entry)
        except DeliveryInputError as exc:
            issues.append(diagnostic(exc.path, exc.category, str(exc), scope))
        if not isinstance(status, str) or status not in DELIVERY_STATUSES | DELIVERY_BLOCKERS:
            issues.append(diagnostic(path + "/status", "status", f"未知 status：{status}", scope))
        if "ui_truth_mode" in entry and not isinstance(entry["ui_truth_mode"], str):
            issues.append(diagnostic(path + "/ui_truth_mode", "status", "ui_truth_mode 必须为字符串", scope))
        review = entry.get("design_review")
        if isinstance(review, dict) and "review_mode" in review and not isinstance(review["review_mode"], str):
            issues.append(diagnostic(path + "/design_review/review_mode", "status", "review_mode 必须为字符串", scope))
        for key in ("blocked_from_status", "resume_target_status"):
            if key in entry and entry[key] is not None and (not isinstance(entry[key], str) or entry[key] not in DELIVERY_STATUSES):
                issues.append(diagnostic(path + "/" + key, "status", f"{key} 必须为正常状态", scope))
        if "blocker_scope" in entry and entry["blocker_scope"] is not None and (not isinstance(entry["blocker_scope"], str) or entry["blocker_scope"] not in {"slice_local", "requirement_global", "action_level_integration"}):
            issues.append(diagnostic(path + "/blocker_scope", "status", "未知 blocker_scope", scope))
        if isinstance(status, str) and status in DELIVERY_BLOCKERS and entry.get("blocked_from_status") in ("merged", "archived"):
            issues.append(diagnostic(path, "status", "终态不能作为阻塞恢复来源", scope))

    if not graph_path.exists():
        # 单切片本身没有跨切片依赖；真正 bootstrap 与终态历史也不需猜测排序。
        active = [entry for entry in values.values() if isinstance(entry, dict) and entry.get("status") not in ("merged", "archived", "draft")]
        legacy: dict = {}
        for sid in values:
            if not _safe_identifier(sid):
                continue
            if any(d["category"] == "path" and d["scope"] == [sid] for d in issues):
                continue
            path = requirement_subdir(req_root, sid) / "dependency.json"
            if path.exists():
                try:
                    legacy[sid] = _read_json_object(path, "dependency")
                except DeliveryInputError as exc:
                    issues.append(diagnostic(exc.path, exc.category, str(exc), [sid]))
        if legacy:
            nodes = legacy
        elif len(values) <= 1 or not active:
            return deps, issues
        else:
            issues.append(diagnostic(graph_path, "dependency", "活跃多切片需求缺少依赖图，无法确定独立性"))
            return deps, issues
    else:
        try:
            data = _read_json_object(graph_path, "dependency")
        except DeliveryInputError as exc:
            return deps, issues + [diagnostic(exc.path, exc.category, str(exc))]
        nodes = data.get("nodes", data.get("sub_requirements", data))
        if "edges" in data and "nodes" not in data and "sub_requirements" not in data:
            edges = data["edges"]
            if not isinstance(edges, list) or any(not isinstance(e, dict) for e in edges):
                return deps, issues + [diagnostic(graph_path, "dependency", "edges 必须为对象列表")]
            nodes = {}
            for edge in edges:
                sid = edge.get("id", edge.get("subreq_id"))
                if not isinstance(sid, str) or sid in nodes:
                    return deps, issues + [diagnostic(graph_path, "dependency", "edges 节点 ID 缺失或重复")]
                nodes[sid] = edge
        if not isinstance(nodes, dict):
            return deps, issues + [diagnostic(graph_path, "dependency", "nodes 必须为对象")]
    for sid, node in nodes.items():
        path = f"{graph_path}#/nodes/{sid}"
        if sid not in values:
            issues.append(diagnostic(path, "dependency", f"未知依赖节点：{sid}"))
            continue
        raw = node.get("depends_on", []) if isinstance(node, dict) else None
        if not isinstance(raw, list) or any(not isinstance(p, str) for p in raw):
            issues.append(diagnostic(path, "dependency", "depends_on 必须为字符串列表", [sid]))
            continue
        deps[sid] = raw
        if len(set(raw)) != len(raw) or sid in raw or any(p not in values for p in raw):
            issues.append(diagnostic(path, "dependency", "depends_on 包含重复、自依赖或未知节点", [sid]))
    visiting: list[str] = []
    visited: set[str] = set()
    cycles: set[str] = set()
    def visit(sid: str) -> None:
        if sid in visiting:
            cycles.update(visiting[visiting.index(sid):])
            return
        if sid in visited:
            return
        visiting.append(sid)
        for parent in deps.get(sid, []):
            if parent in values:
                visit(parent)
        visiting.pop()
        visited.add(sid)
    for sid in deps:
        visit(sid)
    if cycles:
        issues.append(diagnostic(graph_path, "dependency", "依赖图包含环", sorted(cycles)))
    return deps, issues


def normalize_text(text: str) -> str:
    """Normalize for stable hashing: CRLF->LF, strip trailing whitespace/EOF.

    Used by spec-kit persistence hash-drift checks so cosmetic edits don't
    trigger false re-generation. The coordination MCP service uses the same
    normalization when reading client layout JSON.
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
# Layout detection + spec persistence (spec-kit living/in-place archive support)
# --------------------------------------------------------------------------

SPEC_KINDS = ("spec", "plan", "tasks")

DEFAULT_WORKFLOW_POLICY: dict = {
    "version": 4,
    "verification_contract_version": 2,
    "truth_policy": {
        "functional_source": "Requirement",
        "visual_source": "Figma",
        "visual_sources_by_mode": {
            "none": [],
            "existing": [],
            "runtime-baseline": ["requirement", "project", "user-decision"],
            "figma": ["figma", "requirement", "project", "user-decision"],
        },
        "conflict_behavior": "block",
    },
    "workflow_gates": ["requirement_breakdown", "design_contract", "implementation"],
    "capabilities": {
        "ui_truth": {
            "checkpoint": "CP-UI",
            "index": "contracts/ui-truth-index.json",
            "preview": "official_host_stack_preview",
            "modes": {
                "none": {
                    "enabled": False,
                    "stage2": False,
                    "requires_index": False,
                    "requires_preview": False,
                    "final_acceptance": "ordinary_behavior_and_semantic_tests",
                },
                "existing": {
                    "enabled": False,
                    "stage2": False,
                    "requires_index": False,
                    "requires_preview": False,
                    "final_acceptance": "ordinary_behavior_and_semantic_tests",
                },
                "runtime-baseline": {
                    "enabled": True,
                    "stage2": True,
                    "requires_index": True,
                    "requires_preview": True,
                    "final_acceptance": "visual_acceptance",
                },
                "figma": {
                    "enabled": True,
                    "stage2": True,
                    "requires_index": True,
                    "requires_preview": True,
                    "final_acceptance": "visual_acceptance",
                },
            },
        }
    },
    "solution_design": {
        "required": True,
        "human_checkpoint": "CP-DESIGN",
        "human_checkpoint_condition": "user_decision_required_and_no_valid_human_review",
        "artifact_key": "solution_design",
    },
    "status_sequence": [
        "draft",
        "split_ready",
        "acceptance_frozen",
        "design_ready",
        "in_dev",
        "visual_acceptance_passed",
        "merged",
        "archived",
    ],
    "review_loop": {"max_rounds": 3},
    "design_contract_persistence": {
        "active": "living",
        "complete": "in_place",
        "living": {
            "source_of_truth": "design.md",
            "on_drift": "reopen_solution_design",
        },
        "in_place": {
            "source_of_truth": "canonical_artifacts",
            "change_requires": "new_requirement_dir",
        },
    },
    "verification_policy": {
        "required_at": ["merged", "archived"],
        "artifact": "verification.md",
        "required_markers": [
            "ai-delivery-verification:review-rounds",
            "ai-delivery-verification:commands-results",
            "ai-delivery-verification:sign-off",
        ],
    },
}


def is_new_layout(subreq_dir: Path | str) -> bool:
    """True when a sub-requirement has adopted the unified canonical layout.

    Shared by every validator so "new layout" is decided in exactly one place.
    Marker files: ``design.md`` and ``verification.md``.
    """
    d = Path(subreq_dir)
    return (subreq_artifact_path(d, "solution_design").is_file()
            or subreq_artifact_path(d, "verification").is_file())


def load_workflow_policy(start: Path | str) -> dict:
    """Read workflow-policy.json by walking up to `.ai-delivery`, else defaults."""
    ad_dir = find_ai_delivery_dir(start)
    if ad_dir is None:
        return dict(DEFAULT_WORKFLOW_POLICY)
    load_layout_from_ai_delivery_dir(ad_dir)
    policy_path = ad_dir / "meta" / "workflow-policy.json"
    data = _read_json_object(policy_path, "policy")
    require_current_format(policy_path, data, "version", 4)
    require_current_format(policy_path, data, "verification_contract_version", 2)
    reject_removed_fields(policy_path, data)
    if "verification_policy" in data and not isinstance(data["verification_policy"], dict):
        raise DeliveryInputError(policy_path, "policy", "verification_policy 必须为对象")
    verification = data.get("verification_policy", {})
    if "required_markers" in verification:
        markers = verification["required_markers"]
        if (not isinstance(markers, list) or not markers
                or any(not isinstance(marker, str) or not marker.strip() for marker in markers)):
            raise DeliveryInputError(policy_path, "policy", "required_markers 必须为非空列表且每项为非空字符串")
    return data


def repo_root_from_ai_delivery_dir(ad_dir: Path | str) -> Path:
    """Resolve the repository root from an ai_delivery_path binding."""
    ad_dir = Path(ad_dir)
    try:
        data = json.loads(
            (ad_dir / "meta" / "project-binding.json").read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError):
        return ad_dir.parent
    configured = data.get("ai_delivery_path") if isinstance(data, dict) else None
    if not isinstance(configured, str) or not configured:
        return ad_dir.parent
    configured_path = Path(configured)
    if configured_path.is_absolute() or ".." in configured_path.parts:
        return ad_dir.parent
    repo_root = ad_dir
    for part in configured_path.parts:
        if part not in {"", "."}:
            repo_root = repo_root.parent
    try:
        if (repo_root / configured_path).resolve() == ad_dir.resolve():
            return repo_root
    except OSError:
        pass
    return ad_dir.parent


def _selftest() -> int:
    import tempfile

    # 1) default layout works without project-binding.json
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        p = artifact_path(root, "status", "REQ-1")
        assert p == root / ".ai-delivery" / "requirements" / "REQ-1" / "status.json", p
        p = artifact_path(root, "solution_design", "REQ-1", sr_id="SR-001")
        assert p == root / ".ai-delivery" / "requirements" / "REQ-1" / "sub-requirements" / "SR-001" / "design.md", p
        p = artifact_path(root, "visual_acceptance", "REQ-1", sr_id="SR-001")
        assert p == root / ".ai-delivery" / "requirements" / "REQ-1" / "sub-requirements" / "SR-001" / "visual-acceptance.json", p
        # Current archives are status transitions; no manifest path is emitted.
        assert "manifest" not in load_layout(root)["sub_requirement_artifacts"]
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
                    "version": 3,
                    "ai_delivery_path": "governed",
                    "layout": {
                        "requirement_root": "requirements/{req_id}",
                        "sub_requirement_dir": "requirements/{req_id}/sub-requirements/{sr_id}",
                        "requirement_artifacts": {"status": "requirements/{req_id}/status.json"},
                        "sub_requirement_artifacts": {"solution_design": "requirements/{req_id}/sub-requirements/{sr_id}/contracts/design.md"},
                    },
                }
            ),
            encoding="utf-8",
        )
        p = artifact_path(root, "solution_design", "REQ-9", sr_id="SR-002")
        assert p == root / "governed" / "requirements" / "REQ-9" / "sub-requirements" / "SR-002" / "contracts" / "design.md", p
        assert artifact_path(root, "retrospective", "REQ-9") == root / "governed" / "requirements" / "REQ-9" / "retrospective.md"
        assert artifact_path(root, "retrospective_index") == root / "governed" / "retrospectives" / "index.md"

    # 3) canonical_sha256 is stable across cosmetic whitespace
    a = canonical_sha256("line1\nline2  \n")
    b = canonical_sha256("line1\nline2\n")
    assert a == b, (a, b)
    assert len(a) == 64

    # 4) is_new_layout markers
    with tempfile.TemporaryDirectory() as td:
        sr = Path(td) / "SR-001"
        sr.mkdir(parents=True)
        assert not is_new_layout(sr)
        (sr / "design.md").write_text("# design\n", encoding="utf-8")
        assert is_new_layout(sr)

    # 7) workflow policy falls back to defaults outside a governed repo
    with tempfile.TemporaryDirectory() as td:
        policy = load_workflow_policy(Path(td))
        assert policy["review_loop"]["max_rounds"] == 3
        assert policy["design_contract_persistence"]["active"] == "living"

    # 8) the canonical solution-design key retains the stable design.md filename
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        assert artifact_path(root, "solution_design", "REQ-1", sr_id="SR-001").name == "design.md"

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
