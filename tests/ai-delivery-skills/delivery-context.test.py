#!/usr/bin/env python3
"""检查真实上下文 CLI 的来源选择、预算与写权限边界。"""
import json
import hashlib
import importlib.util
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import sys

from fixture_helpers import governed

KIT = Path(__file__).resolve().parents[2]
CLI = KIT / '.agents/skills/ai-delivery-orchestrator/scripts/delivery_context.py'
sys.path.insert(0, str(CLI.parent))
SPEC = importlib.util.spec_from_file_location('context_under_test', CLI)
CONTEXT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CONTEXT)


class ContextTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.req = self.root / '.ai-delivery/requirements/R'
        self.sub = self.req / 'sub-requirements/SR-001'
        self.sub.mkdir(parents=True)
        self.write('AGENTS.md', '根项目约束，不可省略。')
        self.write('src/AGENTS.md', '模块约束。')
        self.write('rules/api.md', 'API 已确认约束。')
        self.write('rules/facts.md', '当前观察，不是强制约束。')
        (self.req / 'status.json').write_text(json.dumps({'_schema':'2.0', 'sub_requirements':{'SR-001':{'status':'draft','ui_truth_mode':'none','ui_bearing':False,'state_flow_required':False,'user_decision_required':False,'design_review':{'review_mode':'none','reviewed_design_sha256':None,'reviewed_at':None,'reviewed_by':None}}}}))
        (self.req / 'requirement.md').write_text('原始需求。')
        self.policy = {'version':4, 'verification_contract_version':2, 'context':{'sources':[
            {'path':'rules/api.md','paths':['src/**'],'roles':['analysis','review'],'kind':'standard','required':True,'writable':False},
            {'path':'rules/facts.md','paths':['src/**'],'kind':'knowledge','required':True,'writable':False}
        ]}}
        self.save_policy()

    def write(self, rel, text):
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)

    def save_policy(self):
        self.write('.ai-delivery/meta/project-binding.json', '{"version":3,"layout": {}}')
        self.write('.ai-delivery/meta/workflow-policy.json', json.dumps(self.policy))

    def run_context(self, *extra):
        return self.run_context_for(['src/new.py'], *extra)

    def run_context_for(self, paths, *extra):
        args = [arg for path in paths for arg in ('--changed-path', path)]
        p = subprocess.run(['python3', str(CLI), '--req-root', str(self.req), '--subreq','SR-001', '--role','analysis', *args, *extra], capture_output=True, text=True)
        self.assertIn(p.returncode, (0,2), p.stderr)
        self.assertTrue(p.stdout.strip(), '上下文 CLI 尚未提供结构化结果：'+p.stderr)
        return p, json.loads(p.stdout)

    def test_scope_selects_root_module_and_typed_sources(self):
        p, result = self.run_context()
        self.assertEqual(p.returncode, 0, result)
        entries = {x['path']:x for x in result['entries']}
        for path in ['AGENTS.md','src/AGENTS.md','rules/api.md','rules/facts.md']:
            self.assertEqual(entries[path]['status'], 'provided')
            self.assertEqual(len(entries[path]['sha256']), 64)
        self.assertEqual(entries['rules/facts.md']['kind'], 'knowledge')
        self.assertFalse(entries['rules/api.md']['writable'])

    def test_required_source_cannot_disappear_under_budget(self):
        _, result = self.run_context('--budget-chars','1')
        self.assertFalse(result['ready'])
        self.assertTrue(any(x['required'] and x['status']=='needs_read' for x in result['entries']))

    def test_missing_required_source_and_unknown_slice_are_diagnostic(self):
        (self.root/'rules/api.md').unlink()
        p, result = self.run_context()
        self.assertEqual(p.returncode,2)
        self.assertFalse(result['ready'])
        self.assertTrue(any(x['status']=='missing' for x in result['entries']))
        p, result = self.run_context('--subreq','SR-999')
        self.assertEqual(p.returncode,2)
        self.assertFalse(result['ready'])

    def test_external_symlink_and_invalid_source_do_not_silently_fallback(self):
        (self.root/'rules/api.md').unlink()
        (self.root/'rules/api.md').symlink_to('/etc/hosts')
        p, result = self.run_context()
        self.assertEqual(p.returncode,2)
        self.assertFalse(result['ready'])
        self.policy['context']['sources'][0]['paths']='src/**'
        self.save_policy()
        p, result = self.run_context()
        self.assertEqual(p.returncode,2)
        self.assertTrue(result['diagnostics'])

    def test_role_filter_and_new_source_bytes_are_observed_without_cache(self):
        p,result=self.run_context('--role','recovery')
        self.assertEqual(p.returncode,0,result)
        self.assertNotIn('rules/api.md',[x['path'] for x in result['entries']])
        self.write('rules/facts.md','已更新的观察；仍不是强制规范。')
        _,result=self.run_context()
        fact=next(x for x in result['entries'] if x['path']=='rules/facts.md')
        self.assertIn('已更新',fact['content'])

    def test_symlinked_module_instructions_are_not_trusted_external_sources(self):
        path=self.root/'src/AGENTS.md'
        path.unlink();path.symlink_to('/etc/hosts')
        p,result=self.run_context()
        self.assertEqual(p.returncode,2,result)
        self.assertFalse(result['ready'])

    def test_git_discovery_includes_staged_unstaged_and_new_paths_without_ownership(self):
        subprocess.run(['git','init','-q',str(self.root)],check=True)
        self.write('src/tracked.py','original')
        subprocess.run(['git','-C',str(self.root),'add','src/tracked.py'],check=True)
        self.write('src/tracked.py','updated')
        self.write('src/untracked.py','new')
        _,result=self.run_context()
        self.assertIn('src/tracked.py',result['observed_changed_paths'])
        self.assertIn('src/untracked.py',result['observed_changed_paths'])
        self.assertIn('src/untracked.py',result['unassigned_paths'])
        self.assertEqual(result['declared_paths'],['src/new.py'])

    def test_runtime_lock_and_backup_are_not_product_changes(self):
        subprocess.run(['git','init','-q',str(self.root)],check=True)
        self.write('.ai-delivery.lock', '')
        self.write('.ai-delivery-backups/backup/status.json', '{old invalid')
        self.write('.ai-delivery-backups/backup/AGENTS.md', '旧备份不可用作当前约束')
        self.write('src/new.py', 'current')
        _, result = self.run_context()
        self.assertIn('src/new.py', result['observed_changed_paths'])
        self.assertFalse(any(p == '.ai-delivery.lock' or p.startswith('.ai-delivery-backups/') for p in result['observed_changed_paths']))
        self.assertFalse(any(p['path'].startswith('.ai-delivery-backups/') for p in result['entries']))

    def test_unrelated_local_diagnostic_does_not_block_selected_context(self):
        status=json.loads((self.req/'status.json').read_text())
        status['sub_requirements']['SR-002']={**status['sub_requirements']['SR-001'],'ui_bearing':'invalid'}
        (self.req/'status.json').write_text(json.dumps(status))
        (self.req/'dependency-graph.json').write_text(json.dumps({'nodes':{'SR-001':{'depends_on':[]},'SR-002':{'depends_on':[]}}}))
        p,result=self.run_context()
        self.assertEqual(p.returncode,0,result.get('diagnostics'))
        self.assertTrue(result['routing']['errors'],'其他切片诊断仍必须可见')

    def test_duplicate_source_cannot_drop_required_and_bad_status_stays_json(self):
        self.policy['context']['sources']=[
            {'path':'rules/missing.md','kind':'standard','required':False},
            {'path':'rules/missing.md','kind':'standard','required':True}]
        self.save_policy()
        p,result=self.run_context()
        self.assertEqual(p.returncode,2,result)
        self.assertFalse(result['ready'])
        (self.req/'status.json').write_text('[]')
        p,result=self.run_context()
        self.assertEqual(p.returncode,2,result)
        self.assertTrue(result['diagnostics'])

    def test_explicit_read_does_not_demote_registered_standard_to_advice(self):
        p,result=self.run_context('--guideline','rules/api.md')
        self.assertEqual(p.returncode,0,result.get('diagnostics'))
        item=next(x for x in result['entries'] if x['path']=='rules/api.md')
        self.assertEqual(item['kind'],'standard')
        self.assertTrue(item['required'])

    def test_nested_binding_preserves_repository_root_and_required_rules(self):
        target=self.root/'tooling/delivery'
        target.parent.mkdir()
        (self.root/'.ai-delivery').rename(target)
        (target/'meta/project-binding.json').write_text(json.dumps({'version':3,'ai_delivery_path':'tooling/delivery','layout':{}}))
        self.req=target/'requirements/R'
        p,result=self.run_context()
        self.assertEqual(p.returncode,0,result)
        entries={x['path']:x for x in result['entries']}
        for path in ['AGENTS.md','src/AGENTS.md','rules/api.md']:
            self.assertEqual(entries[path]['status'],'provided')
            self.assertTrue(entries[path]['required'])

    def test_actual_cross_module_changes_select_rules_without_declared_ownership(self):
        for module in ('finance', 'old', 'new'):
            self.write(f'{module}/AGENTS.md', f'{module} 模块约束。')
            self.write(f'rules/{module}.md', f'{module} 必读规范。')
            self.policy['context']['sources'].append({'path': f'rules/{module}.md',
                'paths': [f'{module}/**'], 'required': True, 'writable': False})
        self.save_policy()
        self.write('finance/changed.py', '旧内容')
        self.write('finance/deleted.py', '删除前内容')
        self.write('old/moved.py', '重命名内容')
        subprocess.run(['git', 'init', '-q', str(self.root)], check=True)
        subprocess.run(['git', '-C', str(self.root), 'add', '.'], check=True)
        subprocess.run(['git', '-C', str(self.root), '-c', 'user.name=fixture', '-c',
                        'user.email=fixture@example.invalid', 'commit', '-qm', 'fixture'], check=True)
        self.write('finance/changed.py', '新内容')
        self.write('finance/added.py', '新增内容')
        (self.root/'finance/deleted.py').unlink()
        subprocess.run(['git', '-C', str(self.root), 'mv', 'old/moved.py', 'new/moved.py'], check=True)
        expected = ['finance/changed.py', 'finance/added.py', 'finance/deleted.py',
                    'old/moved.py', 'new/moved.py']
        for role in ('analysis', 'review'):
            with self.subTest(role=role):
                p, result = self.run_context('--role', role, '--budget-chars', '200000')
                self.assertEqual(p.returncode, 0, result)
                entries = {x['path']: x for x in result['entries']}
                for module in ('finance', 'old', 'new'):
                    self.assertEqual(entries.get(f'{module}/AGENTS.md', {}).get('status'), 'provided')
                    self.assertEqual(entries.get(f'rules/{module}.md', {}).get('status'), 'provided')
                    self.assertFalse(entries[f'rules/{module}.md']['writable'])
                self.assertEqual(result['declared_paths'], ['src/new.py'])
                for path in expected:
                    self.assertIn(path, result['observed_changed_paths'])
                    self.assertIn(path, result['unassigned_paths'])
        p, result = self.run_context_for([], '--role', 'review', '--budget-chars', '200000')
        self.assertEqual(p.returncode, 0, result['diagnostics'])
        self.assertEqual(result['declared_paths'], [])
        self.assertEqual(result['unassigned_paths'], result['observed_changed_paths'])
        self.assertTrue({'finance/AGENTS.md', 'old/AGENTS.md', 'new/AGENTS.md'}.issubset(
            {x['path'] for x in result['entries']}))

    def active_design(self, split=True):
        shutil.rmtree(self.req)
        self.req, self.sub = governed(self.root, status='design_ready', preserve_metadata=True)
        (self.req/'requirement.md').write_text('原始需求。')
        design = self.sub/'design.md'
        source = '[原始需求](../../requirement.md)'
        if split:
            (self.sub/'requirement-slice.md').write_text('拆分需求。')
            source += ' + [切片](requirement-slice.md)'
        design.write_text(design.read_text().replace('| B-001 | R |', f'| B-001 | {source} |'))
        status = json.loads((self.req/'status.json').read_text())
        status['sub_requirements']['SR-001']['design_review']['reviewed_design_sha256'] = hashlib.sha256(design.read_bytes()).hexdigest()
        (self.req/'status.json').write_text(json.dumps(status))

    def test_active_design_keeps_missing_requirement_sources_in_entries(self):
        self.active_design()
        p, result = self.run_context('--role', 'review', '--budget-chars', '200000')
        self.assertEqual(p.returncode, 0, result)
        for target in (self.req/'requirement.md', self.sub/'requirement-slice.md'):
            with self.subTest(target=target.name):
                body = target.read_text()
                target.unlink()
                try:
                    p, result = self.run_context('--role', 'review', '--budget-chars', '200000')
                finally:
                    target.write_text(body)
                self.assertEqual(p.returncode, 2, result['diagnostics'])
                entries = {x['path']: x for x in result['entries']}
                entry = entries.get(target.relative_to(self.root).as_posix(), {})
                self.assertEqual(entry.get('status'), 'missing')
                self.assertTrue(entry.get('required'))
                self.assertFalse(result['ready'])

    def test_non_split_active_design_and_draft_intake_do_not_require_a_slice(self):
        self.active_design(split=False)
        p, result = self.run_context('--role', 'review', '--budget-chars', '200000')
        self.assertEqual(p.returncode, 0, result)
        self.assertNotIn(str((self.sub/'requirement-slice.md').relative_to(self.root)),
                         [x['path'] for x in result['entries']])
        (self.sub/'design.md').unlink()
        (self.req/'requirement.md').unlink()
        status = json.loads((self.req/'status.json').read_text())
        status['sub_requirements']['SR-001'].update(status='draft', design_review={
            'review_mode': 'none', 'reviewed_design_sha256': None,
            'reviewed_at': None, 'reviewed_by': None})
        (self.req/'status.json').write_text(json.dumps(status))
        p, result = self.run_context('--budget-chars', '200000')
        self.assertEqual(p.returncode, 0, result)

    def test_directory_scope_includes_own_rules_with_mixed_and_future_files(self):
        self.write('src/deep/AGENTS.md', '深层目录规则。')
        self.write('empty/AGENTS.md', '空目录规则。')
        for paths in (['src'], ['src/deep/'], ['empty/'],
                      ['src/deep/', 'empty', 'src/not-created.py']):
            with self.subTest(paths=paths):
                p, result = self.run_context_for(paths, '--budget-chars', '200000')
                self.assertEqual(p.returncode, 0, result['diagnostics'])
                entries = {x['path']: x for x in result['entries']}
                for path in paths:
                    directory = Path(path) if (self.root/path).is_dir() else Path(path).parent
                    rule = (directory/'AGENTS.md').as_posix()
                    self.assertEqual(entries.get(rule, {}).get('status'), 'provided')
                if any(path.startswith('src') for path in paths):
                    self.assertEqual(entries.get('rules/api.md', {}).get('status'), 'provided')

    def test_automatic_indexes_preserve_explicit_nature_and_maintenance_scope(self):
        indexes = ('.trellis/spec/index.md', 'docs/knowledge/index.md', 'docs/harness/index.md')
        for index in indexes:
            self.write(index, '索引正文。')
        for kind in ('standard', 'knowledge', 'advice'):
            with self.subTest(kind=kind):
                self.policy['context']['sources'] = [dict(path=index, kind=kind,
                    required=i % 2 == 0, writable=True) for i, index in enumerate(indexes)]
                self.save_policy()
                p, result = self.run_context('--budget-chars', '200000')
                self.assertEqual(p.returncode, 0, result['diagnostics'])
                entries = {x['path']: x for x in result['entries']}
                for i, index in enumerate(indexes):
                    self.assertEqual(entries[index]['kind'], kind)
                    self.assertEqual(entries[index]['required'], i % 2 == 0)
                    self.assertTrue(entries[index]['writable'])
        self.policy['context']['sources'] = [dict(path=indexes[0], kind='standard'),
                                             dict(path=indexes[0], kind='knowledge')]
        self.save_policy()
        p, result = self.run_context('--budget-chars', '200000')
        self.assertEqual(p.returncode, 2, result)
        self.assertTrue(result['diagnostics'])

    def test_automatic_index_discovery_respects_explicit_role_filter(self):
        index = 'docs/harness/index.md'
        self.write(index, '已有框架索引。')
        p, result = self.run_context()
        self.assertEqual(p.returncode, 0, result['diagnostics'])
        item = next(x for x in result['entries'] if x['path']==index)
        self.assertEqual(item['kind'], 'knowledge')
        self.assertFalse(item['required'])
        self.assertFalse(item['writable'])
        self.policy['context']['sources'].append(dict(path=index, kind='standard',
            roles=['review'], required=True, writable=True))
        self.save_policy()
        p, result = self.run_context()
        self.assertEqual(p.returncode, 0, result['diagnostics'])
        self.assertNotIn(index, [x['path'] for x in result['entries']])

    def test_symlink_cycles_return_localized_json_diagnostics(self):
        source = self.root/'rules/api.md'
        source.unlink()
        for double in (False, True):
            with self.subTest(double=double):
                source.symlink_to('other.md' if double else 'api.md')
                if double:
                    (source.parent/'other.md').symlink_to('api.md')
                try:
                    p, result = self.run_context()
                finally:
                    source.unlink()
                    if double:
                        (source.parent/'other.md').unlink()
                self.assertEqual(p.returncode, 2, result)
                self.assertFalse(result['ready'])
                self.assertTrue(any('rules/api.md' in x['path'] for x in result['diagnostics']), result)
                self.assertNotIn('Traceback', p.stderr)

    def test_internal_symlink_chain_retains_source_identity_and_content(self):
        self.write('rules/canonical.md', '合法内部链正文。')
        (self.root/'rules/api.md').unlink()
        (self.root/'rules/api.md').symlink_to('hop.md')
        (self.root/'rules/hop.md').symlink_to('canonical.md')
        p, result = self.run_context()
        self.assertEqual(p.returncode, 0, result)
        item = next(x for x in result['entries'] if x['path']=='rules/canonical.md')
        self.assertEqual(item['content'], '合法内部链正文。')

    def observed_once(self):
        # spy 只统计真实进程；Git 的输出与副作用仍由真实二进制产生。
        real_run = subprocess.run
        with patch.object(CONTEXT.subprocess, 'run', wraps=real_run) as calls:
            paths = CONTEXT.observed_changes(self.root)
        self.assertEqual(calls.call_count, 1)
        return paths

    def test_one_git_status_handles_unborn_index_and_special_untracked_names(self):
        subprocess.run(['git', 'init', '-q', str(self.root)], check=True)
        self.write('src/staged file.py', '暂存内容')
        subprocess.run(['git', '-C', str(self.root), 'add', 'src/staged file.py'], check=True)
        self.write('src/staged file.py', '暂存后工作区修改')
        self.write('src/new\nfile.py', '换行文件名')
        paths = self.observed_once()
        self.assertIn('src/staged file.py', paths)
        self.assertIn('src/new\nfile.py', paths)

    def test_one_git_status_covers_renamed_modified_deleted_and_added_paths(self):
        self.write('src/original\nfile.py', '原始内容')
        self.write('src/deleted file.py', '将被删除')
        subprocess.run(['git', 'init', '-q', str(self.root)], check=True)
        subprocess.run(['git', '-C', str(self.root), 'add', '.'], check=True)
        subprocess.run(['git', '-C', str(self.root), '-c', 'user.name=fixture', '-c',
                        'user.email=fixture@example.invalid', 'commit', '-qm', 'fixture'], check=True)
        self.assertEqual(self.observed_once(), [])
        subprocess.run(['git', '-C', str(self.root), 'mv', 'src/original\nfile.py',
                        'src/renamed file.py'], check=True)
        self.write('src/renamed file.py', '重命名暂存后再次修改')
        (self.root/'src/deleted file.py').unlink()
        self.write('src/new file.py', '新增内容')
        self.assertEqual(self.observed_once(), ['src/deleted file.py', 'src/new file.py',
            'src/original\nfile.py', 'src/renamed file.py'])

    def test_one_git_status_handles_a_normal_non_git_host(self):
        self.assertEqual(self.observed_once(), [])

    def test_git_configuration_failure_is_structured_and_not_treated_as_no_git(self):
        subprocess.run(['git', 'init', '-q', str(self.root)], check=True)
        (self.root/'.git/config').write_text('[broken\n')
        p, result = self.run_context()
        self.assertEqual(p.returncode, 2, result['diagnostics'])
        self.assertFalse(result['ready'])
        self.assertTrue(any('Git' in x['message'] for x in result['diagnostics']))

    def test_invalid_head_is_not_treated_as_a_normal_non_git_host(self):
        subprocess.run(['git', 'init', '-q', str(self.root)], check=True)
        (self.root/'.git/HEAD').write_text('invalid HEAD\n')
        p, result = self.run_context()
        self.assertEqual(p.returncode, 2, result['diagnostics'])
        self.assertFalse(result['ready'])
        self.assertTrue(any('Git' in x['message'] for x in result['diagnostics']))


if __name__ == '__main__':
    unittest.main()
