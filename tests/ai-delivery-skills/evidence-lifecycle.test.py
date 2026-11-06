"""真实消费者回归：最终证据漂移、历史演进、UI 根和规范 AC。"""
import ast
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest

from fixture_helpers import governed

KIT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KIT / '.agents/skills/ai-delivery-orchestrator/scripts'))
from verification_contract import fingerprint, input_digest, review_digest, render_block

MARKERS = '\n'.join('<!-- ai-delivery-verification:' + x + ' -->' for x in ('review-rounds', 'commands-results', 'sign-off'))


def seed_verification(root, sub, sid='SR-001', extra=()):
    (root / 'native.log').write_text('原生结果：1 passed\n')
    inputs = [fingerprint(root, p) for p in [str((sub / 'design.md').relative_to(root)), *extra]]
    data = {'version': 2, 'subreq_id': sid, 'inputs': inputs, 'checks': [
        {'id': 'native', 'acceptance_ids': ['AC-001'], 'required': True, 'result': 'passed',
         'mode': 'executed', 'command': 'python3 -m unittest', 'exit_code': 0,
         'evidence': [fingerprint(root, 'native.log')]}], 'reviews': [
        {'reviewer': 'fixture-reviewer', 'context': 'fresh', 'result': 'clean',
         'input_sha256': input_digest(inputs), 'findings': []}]}
    data['reviews'][-1]['verification_sha256'] = review_digest(data)
    (sub / 'verification.md').write_text(MARKERS + '\n' + render_block(data))
    return data


def ui_fixture(root, *, host=False):
    # 复用现有 shell 测试的夹具构造段；不执行其断言或生产验证代码。
    source = (KIT / 'tests/ai-delivery-skills/visual-acceptance-validator.test.sh').read_text().split("<<'PY'\n", 1)[1].rsplit('\nPY', 1)[0]
    tree = ast.parse(source)
    block = next(n for n in tree.body if isinstance(n, ast.With))
    prefix = [n for n in tree.body[:tree.body.index(block)]
              if not (isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'validator' for t in n.targets))]
    boundary = next(i for i, n in enumerate(block.body) if isinstance(n, ast.FunctionDef) and n.name == 'write_acceptance')
    ns = {'td': str(root), 'validator': KIT / 'scripts/validate-delivery-status.py'}
    exec(compile(ast.Module(body=prefix + block.body[:boundary], type_ignores=[]), 'ui-fixture', 'exec'), ns)
    if host:
        fragment = source[source.index('    host_index = copy.deepcopy(index)'):source.index('    expect_pass("valid runtime host capture"')]
        exec(compile(textwrap.dedent(fragment), 'host-fixture', 'exec'), ns)
    ns['acceptance_path'].write_text(json.dumps(ns['runtime_acceptance'] if host else ns['valid_acceptance']))
    repo, req, sub = ns['repo'], ns['req_root'], ns['subreq']
    meta = repo / '.ai-delivery/meta'; meta.mkdir(exist_ok=True)
    (meta / 'project-binding.json').write_text('{"version":3,"layout":{}}')
    (meta / 'workflow-policy.json').write_text('{"version":4,"verification_contract_version":2}')
    ns['status']['sub_requirements']['SR-001']['status'] = 'merged'
    (req / 'status.json').write_text(json.dumps(ns['status']))
    (req / 'retrospective.md').write_text('<!-- ai-delivery-retrospective:reviewed-at:2026-11-05 -->\n')
    seed_verification(repo, sub)
    return ns


class EvidenceLifecycle(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)

    def validate(self, req):
        p = subprocess.run([sys.executable, str(KIT / 'scripts/validate-delivery-status.py'), str(req / 'status.json'), '--req-root', str(req), '--format', 'json'], capture_output=True, text=True)
        self.assertNotIn('Traceback', p.stderr)
        return p

    def archive(self, req, sid='SR-001', wrapper=None):
        args = [str(KIT / 'scripts/archive-subrequirement.py'), '--req-root', str(req), '--subreq', sid, '--no-delivery-report']
        return subprocess.run([sys.executable, *(['-c', wrapper] if wrapper else []), *args], capture_output=True, text=True)

    def test_archived_history_allows_next_slice_and_detects_contract_tampering(self):
        req, sub = governed(self.root)
        owner = self.root / 'owner.py'; owner.write_text('value = 1\n')
        seed_verification(self.root, sub, extra=['owner.py'])
        other = sub.parent / 'SR-002'; other.mkdir()
        (other / 'design.md').write_bytes((sub / 'design.md').read_bytes())
        status = json.loads((req / 'status.json').read_text())
        draft = copy.deepcopy(status['sub_requirements']['SR-001']); draft['status'] = 'draft'
        draft['design_review'] = {'review_mode': 'none', 'reviewed_design_sha256': None, 'reviewed_at': None, 'reviewed_by': None}
        status['sub_requirements']['SR-002'] = draft
        (req / 'status.json').write_text(json.dumps(status))
        p = self.archive(req); self.assertEqual(p.returncode, 0, p.stderr)
        old_entry = json.loads((req / 'status.json').read_text())['sub_requirements']['SR-001']
        old_contract = (sub / 'verification.md').read_bytes()
        owner.write_text('value = 2\n')
        status = json.loads((req / 'status.json').read_text())
        entry = copy.deepcopy(status['sub_requirements']['SR-001']); entry.pop('archive_evidence', None); entry['status'] = 'merged'
        status['sub_requirements']['SR-002'] = entry
        (req / 'status.json').write_text(json.dumps(status))
        seed_verification(self.root, other, 'SR-002', ['owner.py'])
        p = self.validate(req); self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        p = self.archive(req, 'SR-002'); self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(json.loads((req / 'status.json').read_text())['sub_requirements']['SR-001'], old_entry)
        self.assertEqual((sub / 'verification.md').read_bytes(), old_contract)
        (self.root / 'native.log').unlink()
        self.assertEqual(self.validate(req).returncode, 0, '历史不要求原生日志永久存在')
        (sub / 'verification.md').write_bytes(old_contract + b'\nchanged')
        self.assertNotEqual(self.validate(req).returncode, 0, '旧合同篡改必须被发现')

    def test_only_canonical_acceptance_creates_obligations(self):
        req, sub = governed(self.root)
        design = sub / 'design.md'; design.write_text(design.read_text() + '\n历史 AC-999 已移除。\n')
        status = json.loads((req / 'status.json').read_text())
        status['sub_requirements']['SR-001']['design_review']['reviewed_design_sha256'] = hashlib.sha256(design.read_bytes()).hexdigest()
        (req / 'status.json').write_text(json.dumps(status)); seed_verification(self.root, sub)
        p = self.validate(req); self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        design.write_text(design.read_text().replace('| AC-001 |', '| AC-002 |'))
        status['sub_requirements']['SR-001']['design_review']['reviewed_design_sha256'] = hashlib.sha256(design.read_bytes()).hexdigest()
        (req / 'status.json').write_text(json.dumps(status)); seed_verification(self.root, sub)
        self.assertNotEqual(self.validate(req).returncode, 0)

    def test_ui_root_is_shared_with_verification_without_git(self):
        ns = ui_fixture(self.root); repo, req = ns['repo'], ns['req_root']
        self.assertEqual(self.validate(req).returncode, 0)
        (repo / '.git').rmdir(); (repo / 'tooling').mkdir()
        ad = repo / 'tooling/delivery'; (repo / '.ai-delivery').rename(ad)
        (ad / 'meta/project-binding.json').write_text('{"version":3,"ai_delivery_path":"tooling/delivery","layout":{}}')
        req = ad / 'requirements/REQ-UI'; seed_verification(repo, req / 'sub-requirements/SR-001')
        p = self.validate(req); self.assertEqual(p.returncode, 0, p.stdout + p.stderr)

    def test_native_capture_rejects_governance_alias_but_accepts_native_alias(self):
        ns = ui_fixture(self.root, host=True); repo, req = ns['repo'], ns['req_root']
        self.assertEqual(self.validate(req).returncode, 0)
        for governed in (False, True):
            with self.subTest(governed=governed):
                target = repo / ('.ai-delivery/captures' if governed else 'native-captures'); target.mkdir()
                for source, name in [(ns['runtime_capture'], 'capture.png'), (ns['assertion_report'], 'report.json')]:
                    shutil.copyfile(source, target / name)
                alias = repo / 'native-evidence'; alias.unlink(missing_ok=True); alias.symlink_to(target, target_is_directory=True)
                index = copy.deepcopy(ns['host_index']); index['units'][0]['scenarios'][0]['host_binding']['evidence_root'] = 'native-evidence'
                ns['index_path'].write_text(json.dumps(index))
                acceptance = copy.deepcopy(ns['runtime_acceptance']); acceptance['ui_truth_index_sha256'] = hashlib.sha256(ns['index_path'].read_bytes()).hexdigest()
                ev = acceptance['scenarios'][0]['evidence'][0]; ev['path'] = 'native-evidence/capture.png'; ev['assertion_report_path'] = 'native-evidence/report.json'
                ns['acceptance_path'].write_text(json.dumps(acceptance))
                p = self.validate(req)
                if governed: self.assertNotEqual(p.returncode, 0, p.stdout)
                else: self.assertEqual(p.returncode, 0, p.stdout + p.stderr)

    def test_final_write_covers_transitive_ui_files_under_current_policy(self):
        for version in (4,):
            for role in ('component', 'preview', 'motion_preview', 'host_component', 'runtime_capture', 'assertion_report'):
                with self.subTest(version=version, role=role), tempfile.TemporaryDirectory() as t:
                    ns = ui_fixture(Path(t), host=True); repo, req, sub = ns['repo'], ns['req_root'], ns['subreq']
                    p = self.validate(req); self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
                    # 第一个报告替换后漂移；下一次状态写入前必须重新比对同一消费集合。
                    report = repo / 'report.md'; report.write_text('# <req-id>\n<archived_at>\n<subreq_count>\n<subreq_rows>\n')
                    target = ns[role]
                    wrapper = '''import os, pathlib, runpy, sys
real = os.replace
changed = False
def replace(src, dst):
 global changed
 real(src, dst)
 if not changed:
  changed = True
  pathlib.Path(TARGET).write_bytes(b'changed after first output')
os.replace = replace
sys.argv = sys.argv[1:]
runpy.run_path(sys.argv[0], run_name='__main__')
'''.replace('TARGET', repr(str(target)))
                    args = [str(KIT / 'scripts/archive-subrequirement.py'), '--req-root', str(req), '--subreq', 'SR-001', '--delivery-report-template', str(report)]
                    before = (req / 'status.json').read_bytes()
                    p = subprocess.run([sys.executable, '-c', wrapper, *args], capture_output=True, text=True)
                    self.assertNotEqual(p.returncode, 0, '写前已知输入漂移不可归档')
                    self.assertEqual((req / 'status.json').read_bytes(), before)


if __name__ == '__main__': unittest.main()
