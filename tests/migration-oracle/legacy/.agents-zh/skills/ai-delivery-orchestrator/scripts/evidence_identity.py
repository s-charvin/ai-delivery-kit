"""共享证据身份：当前消费集合与原位归档材料的历史完整性。"""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
import hashlib
import json
from pathlib import Path, PureWindowsPath

from layout import (find_ai_delivery_dir, repo_root_from_ai_delivery_dir, requirement_artifact_path,
                    require_current_format, compatibility_error)

_consumed = ContextVar('delivery_consumed_files', default=None)


def file_identity(root: Path, path: Path) -> dict:
    original_root = root.absolute()
    lexical = path.absolute()
    root = root.resolve()
    try:
        relative = lexical.relative_to(original_root).as_posix()
    except ValueError:
        # 系统路径别名（例如 macOS /var → /private/var）不改变 repo-relative 身份。
        ancestor = next((p for p in lexical.parents if p.resolve() == root), None)
        if ancestor is None:
            raise ValueError(f'证据越出项目根：{path}')
        relative = lexical.relative_to(ancestor).as_posix()
    lexical = root / relative
    resolved = lexical.resolve()
    target = resolved.relative_to(root).as_posix()
    if resolved.is_file():
        digest = hashlib.sha256(resolved.read_bytes()).hexdigest()
    elif not resolved.exists() and not lexical.is_symlink():
        digest = None
    else:
        raise ValueError(f'证据不是普通文件：{relative}')
    return {'path': relative, 'resolved_path': target, 'sha256': digest}


@contextmanager
def capture_consumed(root: Path, governance: Path | None = None):
    records = {}
    token = _consumed.set((root.resolve(), records, governance.resolve() if governance else None))
    try:
        yield records
    finally:
        _consumed.reset(token)


def observe_file(path: Path, expected: str | None = None, *, absent=False) -> None:
    """同一路径漂移不能被后一次读取覆盖；普通调用不建立全局台账。"""
    active = _consumed.get()
    if active is None:
        return
    root, records, _ = active
    identity = file_identity(root, path)
    if (absent or expected is not None) and identity['sha256'] != expected:
        raise ValueError(f'校验期间证据发生版本漂移：{path}')
    previous = records.get(identity['path'])
    if previous is not None and previous != identity:
        raise ValueError(f'校验期间证据身份发生变化：{path}')
    records[identity['path']] = identity


def is_governance_path(root: Path, path: Path) -> bool:
    active = _consumed.get()
    governance = active[2] if active is not None else None
    return path.resolve().is_relative_to(governance or root.resolve() / '.ai-delivery')


def validate_identity(root: Path, identity: dict) -> Path:
    """消费机器结果前校验格式、路径边界及当前身份。"""
    if not isinstance(identity, dict) or set(identity) != {'path', 'resolved_path', 'sha256'}:
        raise ValueError('非法 consumed file identity')
    for field in ('path', 'resolved_path'):
        value = identity[field]
        if (not isinstance(value, str) or not value or Path(value).is_absolute()
                or PureWindowsPath(value).drive or '..' in Path(value).parts
                or '..' in PureWindowsPath(value).parts):
            raise ValueError('证据身份路径必须位于项目内')
    path = root.resolve() / identity['path']
    if file_identity(root, path) != identity:
        raise ValueError(f'归档输入发生版本漂移：{path}')
    return path


def _entry_digest(entry: dict) -> str:
    canonical = {key: value for key, value in entry.items() if key != 'archive_evidence'}
    return hashlib.sha256(json.dumps(canonical, ensure_ascii=False, sort_keys=True,
                                    separators=(',', ':')).encode()).hexdigest()


def archive_evidence(req_root: Path, subreq_id: str, entry: dict) -> dict:
    """存于既有 status entry；固定合同，允许生产源码及原生日志后续演进。"""
    ad = find_ai_delivery_dir(req_root)
    root = repo_root_from_ai_delivery_dir(ad) if ad is not None else req_root
    files = [file_identity(root, requirement_artifact_path(req_root, kind, subreq_id))
             for kind in ('solution_design', 'verification', 'ui_truth_index', 'visual_acceptance')]
    return {'version': 1, 'entry_sha256': _entry_digest(entry), 'files': files}


def check_archive_evidence(req_root: Path, subreq_id: str, entry: dict) -> list[str]:
    saved = entry.get('archive_evidence')
    status_path = requirement_artifact_path(req_root, "status")
    if not isinstance(saved, dict):
        raise compatibility_error(status_path, f"sub_requirements.{subreq_id}.archive_evidence", saved, "current identity version 1; cannot reconstruct historical approval")
    require_current_format(status_path, saved, "version", 1)
    from verification_contract import parse_verification_v2
    verification = requirement_artifact_path(req_root, "verification", subreq_id)
    contract = parse_verification_v2(verification)
    require_current_format(verification, contract, "version", 2)
    if entry.get('ui_truth_mode') in {'figma', 'runtime-baseline'}:
        for kind, version in (("ui_truth_index", 3), ("visual_acceptance", 2)):
            path = requirement_artifact_path(req_root, kind, subreq_id)
            data = json.loads(path.read_text(encoding='utf-8'))
            if not isinstance(data, dict):
                return [f'{path}: JSON 根必须为对象']
            require_current_format(path, data, "schema_version", version)
    try:
        expected = archive_evidence(req_root, subreq_id, entry)
        if saved != expected:
            return ['归档终态记录或固定合同已变化；不得以当前源码重验替代历史完整性']
        if any(record['sha256'] is None for record in expected['files'][:2]):
            return ['归档固定设计或验证材料缺失']
        ad = find_ai_delivery_dir(req_root)
        root = repo_root_from_ai_delivery_dir(ad) if ad is not None else req_root
        for record in saved['files']:
            observe_file(root / record['path'], record['sha256'], absent=record['sha256'] is None)
    except (OSError, ValueError, RuntimeError) as exc:
        return [f'无法核对归档材料身份：{exc}']
    return []
