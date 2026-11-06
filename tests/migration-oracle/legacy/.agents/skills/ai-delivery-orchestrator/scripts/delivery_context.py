#!/usr/bin/env python3
"""按当前切片、阶段与变更范围生成只读上下文；不写状态或授权缓存。"""
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys

from design_contract import DESIGN_READY_STATUSES
from layout import (find_ai_delivery_dir, load_workflow_policy, requirement_artifact_path,
                    repo_root_from_ai_delivery_dir, DeliveryInputError, diagnostic as input_diagnostic)

ROLES = ('analysis', 'design', 'ui', 'implement', 'review', 'recovery', 'finish')
STAGE_REFS = {
    'analysis': 'scenario-guidance.md', 'design': 'stage-design-and-spec.md',
    'ui': 'stage-ui-truth.md', 'implement': 'stage-implementation.md',
    'review': 'stage-implementation.md', 'recovery': 'reconcile-rules.md',
    'finish': 'stage-implementation.md',
}


def observed_changes(root: Path) -> list[str]:
    """只读发现实际变更；发现不赋予本任务对这些路径的写/提交权。"""
    result = subprocess.run(['git', '-C', str(root), 'status', '--porcelain=v1',
        '-z', '--untracked-files=all'], capture_output=True, timeout=10,
        env={**os.environ, 'LC_ALL': 'C'})
    if result.returncode:
        # 坏 HEAD 也会被 Git 报为“非仓库”，不能据此隐藏已有仓库损坏。
        git_marker = any((directory / '.git').exists() or (directory / '.git').is_symlink()
                         for directory in (root, *root.parents))
        if (result.returncode == 128 and not git_marker and not os.environ.get('GIT_DIR')
                and result.stderr.startswith(b'fatal: not a git repository')):
            return []
        raise ValueError('无法读取真实 Git 变更范围：' + result.stderr.decode('utf-8', errors='replace').strip())
    records = result.stdout.split(b'\0')
    if records[-1]:
        raise ValueError('Git porcelain 输出缺少记录终止符')
    paths = set()
    records = iter(records[:-1])
    for record in records:
        if len(record) < 4 or record[2:3] != b' ':
            raise ValueError('Git porcelain 路径记录格式错误')
        paths.add(record[3:].decode('utf-8'))
        # -z 的重命名/复制记录按“目标、原路径”排列，第二路径不带状态前缀。
        if b'R' in record[:2] or b'C' in record[:2]:
            original = next(records, None)
            if not original:
                raise ValueError('Git porcelain 重命名记录缺少原路径')
            paths.add(original.decode('utf-8'))
    return sorted(path for path in paths if path != '.ai-delivery.lock'
                  and path != '.ai-delivery-backups' and not path.startswith('.ai-delivery-backups/'))


class ContextPathError(ValueError):
    def __init__(self, path: Path, message: str):
        super().__init__(message)
        self.path = path


def confined(root: Path, value: str) -> Path:
    """来源只允许仓内常规相对路径，解析 symlink 后再次检查。"""
    if not isinstance(value, str) or not value or Path(value).is_absolute() or '..' in Path(value).parts:
        raise ValueError(f'非法仓内路径：{value!r}')
    try:
        target = (root / value).resolve()
    except (OSError, RuntimeError) as exc:
        raise ContextPathError(root / value, f'无法解析来源路径：{exc}') from exc
    if not target.is_relative_to(root):
        raise ValueError(f'来源越出项目：{value}')
    return target


def source_config(policy: dict) -> list[dict]:
    context = policy.get('context', {})
    if not isinstance(context, dict) or not isinstance(context.get('sources', []), list):
        raise ValueError('context.sources 必须是列表')
    sources = context.get('sources', [])
    for source in sources:
        if not isinstance(source, dict) or not isinstance(source.get('path'), str):
            raise ValueError('规范来源必须包含 path')
        for field in ('paths', 'roles'):
            value = source.get(field, [])
            if not isinstance(value, list) or any(not isinstance(x, str) or not x for x in value):
                raise ValueError(f'来源 {source["path"]} 的 {field} 必须为字符串列表')
        if any(role not in ROLES for role in source.get('roles', [])):
            raise ValueError(f'来源 {source["path"]} 有未知角色')
        if source.get('kind', 'standard') not in ('knowledge', 'standard', 'advice'):
            raise ValueError(f'来源 {source["path"]} 有未知性质')
        for field in ('required', 'writable'):
            if field in source and not isinstance(source[field], bool):
                raise ValueError(f'来源 {source["path"]} 的 {field} 必须为布尔值')
    return sources


def context_view(req_root: Path, subreq: str, role: str, changed_paths: list[str],
                 guidelines: list[str], budget: int) -> dict:
    result = {'version': 1, 'selected_subreq': subreq, 'role': role, 'ready': False,
              'entries': [], 'diagnostics': [], 'routing': None}
    def diagnostic(path, message):
        result['diagnostics'].append({'path': str(path), 'category': 'context_input',
            'scope': [subreq], 'message': message, 'recovery': '修复来源或显式补读后重新生成上下文'})
    try:
        ad = find_ai_delivery_dir(req_root)
        if ad is None:
            raise ValueError('缺少项目 binding，无法确定规范来源根')
        root = repo_root_from_ai_delivery_dir(ad).resolve()
        policy = load_workflow_policy(req_root)
        sources = source_config(policy)
        status_path = requirement_artifact_path(req_root, 'status')
        status = json.loads(status_path.read_text(encoding='utf-8'))
        if not isinstance(status,dict) or not isinstance(status.get('sub_requirements'),dict):
            raise ValueError('status 与 sub_requirements 必须为对象')
        if subreq not in status['sub_requirements']:
            raise ValueError(f'未知切片：{subreq}')
        # 只调用已有 reconcile，不能自行从 status 推断授权。
        spec = importlib.util.spec_from_file_location('delivery_context_reconcile', Path(__file__).with_name('reconcile-delivery.py'))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        routing = module.reconcile(status_path, req_root)
        result['routing'] = routing
        routing_diagnostics = routing.get('diagnostics', [])
        for item in routing_diagnostics:
            scope=item.get('scope','requirement')
            if scope=='requirement' or isinstance(scope,list) and subreq in scope:
                result['diagnostics'].append(item)
        # 完整诊断仍在 routing 保留；无结构化作用域时按需求级保守处理。
        if not routing_diagnostics:
            for error in routing.get('errors', []): diagnostic(status_path, error)
        # 路由的全局下一切片不代表所选切片已授权；保留原结果，不生成额外执行动作。
        paths = []
        directories = set()
        for path in changed_paths:
            target = confined(root, path)
            relative = Path(path).as_posix()
            paths.append(relative)
            if target.is_dir() or path.endswith('/'):
                directories.add(relative)
        observed=observed_changes(root)
        result['declared_paths']=paths.copy()
        result['observed_changed_paths']=observed
        result['unassigned_paths']=[p for p in observed if p not in paths]
        # 只扩大阅读候选范围，不把第三方脏文件归为本任务。
        paths = list(dict.fromkeys(paths + observed))
        requested = []
        def add(path, kind, required, reason, writable=False):
            if kind != 'guidance':
                confined(root, path.relative_to(root).as_posix())
            requested.append((path, kind, required, reason, writable))
        add(root / 'AGENTS.md', 'standard', (root / 'AGENTS.md').exists() or (root / 'AGENTS.md').is_symlink(), '项目入口')
        for relative in paths:
            parent = Path(relative) if relative in directories or (root / relative).is_dir() else Path(relative).parent
            for directory in reversed(parent.parents):
                if str(directory) != '.':
                    path = root / directory / 'AGENTS.md'
                    if path.exists() or path.is_symlink(): add(path, 'standard', True, f'作用域 {relative}')
            path = root / parent / 'AGENTS.md'
            if path.exists() or path.is_symlink(): add(path, 'standard', True, f'作用域 {relative}')
        entry = status['sub_requirements'][subreq]
        active_design = entry.get('status') in DESIGN_READY_STATUSES - {'archived'}
        design = requirement_artifact_path(req_root, 'solution_design', subreq)
        design_text = design.read_text(encoding='utf-8') if design.is_file() else ''
        def referenced(path):
            # 来源名只用于判定已声明的阅读义务，不创建第二份需求/设计合同。
            return bool(re.search(r'(?<![\w.-])' + re.escape(path.name) + r'(?![\w.-])', design_text))
        for kind in ('requirement', 'global_rules'):
            path = requirement_artifact_path(req_root, kind)
            required = kind == 'requirement' and (active_design or referenced(path))
            if required or path.exists(): add(path, 'task', True, '当前需求来源')
        for kind in ('requirement_slice', 'solution_design', 'decisions'):
            path = requirement_artifact_path(req_root, kind, subreq)
            required = kind == 'solution_design' and active_design or kind == 'requirement_slice' and referenced(path)
            if required or path.exists(): add(path, 'task', True, '当前切片合同')
        ref = Path(__file__).parent.parent / 'references' / STAGE_REFS[role]
        add(ref, 'guidance', True, f'{role} 阶段规则')
        registered = set()
        selection_paths = paths + [p.rstrip('/') + '/' for p in directories]
        for source in sources:
            target = confined(root, source['path'])
            registered.add(target)
            roles = source.get('roles', [])
            patterns = source.get('paths', [])
            if roles and role not in roles: continue
            # 尚无 diff 的分析/设计应加载已登记领域来源，不仅依赖扩展名。
            if patterns and selection_paths and not any(fnmatch.fnmatchcase(p, pat) for p in selection_paths for pat in patterns): continue
            add(target, source.get('kind', 'standard'), source.get('required', True),
                '登记来源与角色/范围匹配', source.get('writable', False))
        for value in guidelines:
            add(confined(root, value), 'advice', True, '显式补充')
        # 已有框架入口只作为索引阅读提示，不自动安装或运行其生命周期。
        for value in ('.trellis/spec/index.md', 'docs/knowledge/index.md', 'docs/harness/index.md'):
            target = confined(root, value)
            if target not in registered and target.is_file():
                add(target, 'knowledge', False, '已有框架索引；按需登记叶子来源')
        merged = {}
        for path, kind, required, reason, writable in requested:
            path=path.resolve()
            if path in merged:
                previous=merged[path]
                if previous[0]!=kind and reason!='显式补充':
                    diagnostic(path,'同一来源的性质冲突，不能自动升级知识为规范')
                merged[path]=(previous[0],previous[1] or required,
                              previous[2]+'; '+reason,previous[3] and writable)
            else: merged[path]=(kind,required,reason,writable)
        for path, (kind, required, reason, writable) in merged.items():
            # kit 自带规则可能在外部已安装技能目录；用户来源始终 confined。
            relative = str(path.relative_to(root)) if path.is_relative_to(root) else str(path)
            entry = {'path': relative, 'kind': kind, 'required': required, 'reason': reason,
                     'writable': writable, 'sha256': None, 'status': 'missing'}
            try:
                if path.is_relative_to(root): confined(root, relative)
                raw = path.read_bytes()
                body = raw.decode('utf-8')
                if not body.strip(): raise ValueError('来源为空')
                entry['sha256'] = hashlib.sha256(raw).hexdigest()
                entry['status'] = 'provided' if len(body) <= budget else 'needs_read'
                if entry['status'] == 'provided':
                    entry['content'] = body
                    budget -= len(body)
            except (OSError, UnicodeError, ValueError) as exc:
                if required: diagnostic(path, str(exc))
            result['entries'].append(entry)
        result['ready'] = not result['diagnostics'] and all(not x['required'] or x['status']=='provided' for x in result['entries'])
    except (OSError, ValueError, KeyError, TypeError, subprocess.TimeoutExpired) as exc:
        if isinstance(exc, DeliveryInputError):
            result['diagnostics'].append(input_diagnostic(exc.path, exc.category, str(exc)))
        else:
            diagnostic(getattr(exc, 'path', req_root), str(exc))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--req-root', type=Path, required=True)
    parser.add_argument('--subreq', required=True)
    parser.add_argument('--role', choices=ROLES, required=True)
    parser.add_argument('--changed-path', action='append', default=[])
    parser.add_argument('--guideline', action='append', default=[])
    parser.add_argument('--budget-chars', type=int, default=64000)
    parser.add_argument('--format', choices=('json',), default='json')
    args = parser.parse_args()
    result = context_view(args.req_root.resolve(), args.subreq, args.role,
                          args.changed_path, args.guideline, max(0,args.budget_chars))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['ready'] else 2


if __name__ == '__main__':
    sys.exit(main())
