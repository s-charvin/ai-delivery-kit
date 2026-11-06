"""归档真实 CLI：治理前置、只读预览、失败重试及合作入口并发。"""
import hashlib
import fcntl
import time
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from fixture_helpers import governed, seed_verification

ROOT = Path(__file__).resolve().parents[2]
ARCHIVE = ROOT / 'scripts/archive-subrequirement.py'
sys.path.insert(0, str(ROOT / '.agents/skills/ai-delivery-orchestrator/scripts'))
from verification_contract import fingerprint, input_digest, render_block, review_digest
VERIFICATION = '''# 验证
<!-- ai-delivery-verification:review-rounds -->
一轮独立评审通过。
<!-- ai-delivery-verification:commands-results -->
python3 原生测试：通过。
<!-- ai-delivery-verification:sign-off -->
负责人已签署。
'''
REPORT = '# <req-id>\n<archived_at>\n<subreq_count>\n<subreq_rows>\n'
LEDGER = '''<!-- ai-delivery-retrospective:reviewed-at:2026-11-05 -->
<!-- ai-delivery-retrospective:problem-index:v2 -->
| ID | Observable trigger | Applicable scenario | Shortest path | knowledge_type | reuse_scope | index_decision | confidence | importance | Status | Details |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| RET-001 | 恢复失败 | 归档重试 | 重跑命令 | reusable | project | include | confirmed | high | resolved | [详情](#ret-001) |
<!-- /ai-delivery-retrospective:problem-index:v2 -->
<a id="ret-001"></a>
## RET-001: 恢复
归档需幂等。
'''
INDEX = '''<!-- ai-delivery-retrospective:index:v1 -->
| 条目 | 触发 | 场景 | 路径 | 状态 | 时间 | 详情 |
| --- | --- | --- | --- | --- | --- | --- |
<retrospective_rows>
<!-- /ai-delivery-retrospective:index:v1 -->
'''


class ArchiveReliability(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.req, self.sub = governed(self.root, version=4)
        seed_verification(self.root, self.sub)
        self.status = self.req / 'status.json'
        self.template = self.root / 'report.md'
        self.template.write_text(REPORT)
        self.index_template = self.root / 'index.md'
        self.index_template.write_text(INDEX)

    def command(self, *extra, subreq='SR-001'):
        return [sys.executable, str(ARCHIVE), '--req-root', str(self.req), '--subreq', subreq,
                '--now', '2026-11-05T00:00:00+00:00', *extra]

    def run_archive(self, *extra, subreq='SR-001'):
        return subprocess.run(self.command(*extra, subreq=subreq), capture_output=True, text=True)

    def snapshot(self):
        return {str(p.relative_to(self.root)): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}

    def assert_merged_failure(self, result, before):
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertNotIn('ARCHIVED ', result.stdout)
        self.assertEqual(self.status.read_bytes(), before)

    def test_merged_without_design_or_verification_is_rejected(self):
        for filename in ('design.md', 'verification.md'):
            with self.subTest(filename=filename):
                path = self.sub / filename
                content = path.read_bytes(); path.unlink()
                before = self.status.read_bytes()
                result = self.run_archive('--no-delivery-report')
                self.assert_merged_failure(result, before)
                path.write_bytes(content)

    def test_invalid_binding_is_rejected_without_writes(self):
        (self.root / '.ai-delivery/meta/project-binding.json').write_text('{broken')
        before = self.status.read_bytes()
        self.assert_merged_failure(self.run_archive('--no-delivery-report'), before)

    def test_invalid_validator_protocol_cannot_archive(self):
        seeded = self.root / '.ai-delivery/scripts/validate-delivery-status.py'
        seeded.parent.mkdir()
        for body in ('pass', 'print("not json")', 'print(\'{"valid": true,"errors":[],"diagnostics":[]}\'); raise SystemExit(1)', 'print(\'{"valid": false,"errors":[],"diagnostics":[]}\')', 'raise RuntimeError("broken")'):
            with self.subTest(body=body):
                seeded.write_text(body)
                before = self.status.read_bytes()
                self.assert_merged_failure(self.run_archive('--no-delivery-report'), before)

    def test_preview_is_pure_read_only_even_with_final_outputs(self):
        (self.req / 'retrospective.md').write_text(LEDGER)
        before = self.snapshot()
        result = self.run_archive('--no-status-write', '--delivery-report-template', str(self.template), '--retrospective-index-template', str(self.index_template))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('WOULD_ARCHIVE', result.stdout)
        self.assertEqual(before, self.snapshot())

    def test_preview_does_not_create_validator_bytecode(self):
        scripts=self.root/'.ai-delivery/scripts'; scripts.mkdir()
        (scripts/'archive_probe.py').write_text('value = True')
        (scripts/'validate-delivery-status.py').write_text('import archive_probe\nprint(\'{"valid":true,"errors":[],"diagnostics":[],"consumed_files":[]}\')')
        before=self.snapshot()
        result=self.run_archive('--no-status-write','--no-delivery-report')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(before,self.snapshot())

    def test_report_directory_failure_keeps_merged_and_retry_succeeds(self):
        target = self.req / 'delivery-report.md'; target.mkdir()
        before = self.status.read_bytes()
        self.assert_merged_failure(self.run_archive('--delivery-report-template', str(self.template)), before)
        target.rmdir()
        result = self.run_archive('--delivery-report-template', str(self.template))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(self.status.read_text())['sub_requirements']['SR-001']['status'], 'archived')
        self.assertIn('| SR-001 | archived |', target.read_text())
        self.assertEqual(len(list(self.req.rglob('design.md'))), 1)

    def test_index_target_failure_is_preflighted_before_report(self):
        (self.req / 'retrospective.md').write_text(LEDGER)
        index = self.root / '.ai-delivery/retrospectives/index.md'; index.mkdir(parents=True)
        before = self.status.read_bytes()
        result = self.run_archive('--delivery-report-template', str(self.template), '--retrospective-index-template', str(self.index_template))
        self.assert_merged_failure(result, before)
        self.assertFalse((self.req / 'delivery-report.md').exists())

    def test_status_replace_failure_can_retry_without_duplicate_index(self):
        (self.req / 'retrospective.md').write_text(LEDGER)
        command = self.command('--delivery-report-template', str(self.template), '--retrospective-index-template', str(self.index_template))
        wrapper = '''import os,runpy,sys
original=os.replace
fail_target=os.path.realpath(sys.argv[1])
def fail_status(src,dst):
    if os.path.realpath(dst)==fail_target: raise OSError("injected status replace failure")
    return original(src,dst)
os.replace=fail_status
sys.argv=sys.argv[2:]
runpy.run_path(sys.argv[0],run_name="__main__")
'''
        before = self.status.read_bytes()
        result = subprocess.run([sys.executable, '-c', wrapper, str(self.status), *command[1:]], capture_output=True, text=True)
        self.assert_merged_failure(result, before)
        self.assertTrue((self.req / 'delivery-report.md').is_file())
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        index = self.root / '.ai-delivery/retrospectives/index.md'
        self.assertEqual(index.read_text().count('| R/RET-001 |'), 1)
        self.assertFalse(list(self.req.rglob('*.archive-tmp')))

    def test_observed_status_drift_is_not_overwritten(self):
        seeded = self.root / '.ai-delivery/scripts/validate-delivery-status.py'; seeded.parent.mkdir()
        seeded.write_text('import pathlib,sys\np=pathlib.Path(sys.argv[1]); p.write_text(p.read_text()+"\\n")\nprint(\'{"valid":true,"errors":[],"diagnostics":[]}\')')
        before = self.status.read_bytes()
        result = self.run_archive('--no-delivery-report')
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('ARCHIVED ', result.stdout)
        self.assertEqual(self.status.read_bytes(), before+b'\n')

    def test_status_change_between_load_and_snapshot_is_not_overwritten(self):
        command=self.command('--no-delivery-report')
        wrapper = 'import pathlib,os,runpy,sys\noriginal=pathlib.Path.read_text\ntarget=os.path.realpath(sys.argv[1])\ndef mutate_after_read(path,*args,**kwargs):\n    text=original(path,*args,**kwargs)\n    if os.path.realpath(path)==target:\n        path.write_text(text+"\\n")\n    return text\npathlib.Path.read_text=mutate_after_read\nsys.argv=sys.argv[2:]\nrunpy.run_path(sys.argv[0],run_name="__main__")\n'
        before=self.status.read_bytes()
        result=subprocess.run([sys.executable,'-c',wrapper,str(self.status),*command[1:]],capture_output=True,text=True)
        self.assertNotEqual(result.returncode,0,result.stdout)
        self.assertEqual(self.status.read_bytes(),before+b'\n')

    def test_concurrent_slices_do_not_lose_status_updates(self):
        second = self.sub.parent / 'SR-002'; second.mkdir()
        for filename in ('design.md', 'verification.md'):
            (second / filename).write_bytes((self.sub / filename).read_bytes())
        seed_verification(self.root, second, 'SR-002')
        data=json.loads(self.status.read_text()); data['sub_requirements']['SR-002']=dict(data['sub_requirements']['SR-001'])
        self.status.write_text(json.dumps(data))
        commands=[self.command('--no-delivery-report', subreq=s) for s in ('SR-001', 'SR-002')]
        processes=[subprocess.Popen(c, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for c in commands]
        for process in processes:
            stdout,stderr=process.communicate(timeout=15)
            self.assertEqual(process.returncode,0,stdout+stderr)
        self.assertTrue(all(e['status']=='archived' for e in json.loads(self.status.read_text())['sub_requirements'].values()))

    def test_new_legacy_transition_also_requires_design_and_verification(self):
        self.status.write_text(json.dumps({'requirement_id':'R', 'sub_requirements':{'SR-001':{'status':'merged'}}}))
        (self.sub / 'design.md').unlink()
        (self.sub / 'verification.md').unlink()
        (self.sub / 'spec').mkdir()
        for filename in ('spec.md','plan.md','tasks.md'):
            (self.sub / 'spec' / filename).write_text('# 历史规格')
        before = self.status.read_bytes()
        self.assert_merged_failure(self.run_archive('--no-delivery-report'), before)

    def test_full_binding_paths_are_used_for_status_evidence_and_report(self):
        ad = self.root / '.ai-delivery'
        binding = {'version':3,'layout': {'requirement_root':'work/{req_id}', 'sub_requirement_dir':'work/{req_id}/slices/{sr_id}',
            'requirement_artifacts': {'status':'work/{req_id}/meta/state.json', 'dependency_graph':'work/{req_id}/meta/dependencies.json',
                'retrospective':'work/{req_id}/knowledge/notes.md', 'delivery_report':'work/{req_id}/results/final.md'},
            'sub_requirement_artifacts': {'solution_design':'work/{req_id}/slices/{sr_id}/evidence/solution.md',
                'verification':'work/{req_id}/slices/{sr_id}/evidence/check.md'}}}
        (ad / 'meta/project-binding.json').write_text(json.dumps(binding))
        original = self.req
        self.req = ad / 'work/R'; self.req.mkdir(parents=True)
        self.status = self.req / 'meta/state.json'; self.status.parent.mkdir()
        self.status.write_bytes((original / 'status.json').read_bytes())
        self.sub = self.req / 'slices/SR-001'; evidence=self.sub/'evidence'; evidence.mkdir(parents=True)
        for source,destination in [('design.md','solution.md'),('verification.md','check.md')]:
            (evidence/destination).write_bytes((original/'sub-requirements/SR-001'/source).read_bytes())
        from verification_contract import parse_verification_v2
        contract=parse_verification_v2(evidence/'check.md')
        contract['inputs']=[fingerprint(self.root,str((evidence/'solution.md').relative_to(self.root)))]
        contract['reviews'][-1]['input_sha256']=input_digest(contract['inputs'])
        contract['reviews'][-1]['verification_sha256']=review_digest(contract)
        (evidence/'check.md').write_text(VERIFICATION+'\n'+render_block(contract))
        ledger = self.req/'knowledge/notes.md'; ledger.parent.mkdir(); ledger.write_text('<!-- ai-delivery-retrospective:reviewed-at:2026-11-05 -->')
        result=self.run_archive('--delivery-report-template', str(self.template))
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(self.status.read_text())['sub_requirements']['SR-001']['status'],'archived')
        report=self.req/'results/final.md'
        self.assertIn('slices/SR-001/evidence/check.md', report.read_text())
        self.assertFalse((self.req/'status.json').exists())
        self.assertFalse((self.req/'delivery-report.md').exists())

    def test_index_binding_cannot_overwrite_design_input(self):
        (self.req/'retrospective.md').write_text(LEDGER)
        (self.root/'.ai-delivery/meta/project-binding.json').write_text(json.dumps({'version':3,'layout':{'project_artifacts':{'retrospective_index':'requirements/{req_id}/sub-requirements/SR-001/design.md'}}}))
        before=self.status.read_bytes(); design=(self.sub/'design.md').read_bytes()
        result=self.run_archive('--no-delivery-report','--retrospective-index-template',str(self.index_template))
        self.assert_merged_failure(result,before)
        self.assertEqual((self.sub/'design.md').read_bytes(),design)

    def test_project_index_preserves_concurrent_requirements(self):
        (self.req/'retrospective.md').write_text(LEDGER)
        other=self.req.parent/'R2'
        import shutil
        shutil.copytree(self.req,other)
        seed_verification(self.root, other/'sub-requirements/SR-001')
        data=json.loads((other/'status.json').read_text()); data['requirement_id']='R2'; (other/'status.json').write_text(json.dumps(data))
        commands=[self.command('--no-delivery-report','--retrospective-index-template',str(self.index_template))]
        commands.append([v if v!=str(self.req) else str(other) for v in commands[0]])
        processes=[subprocess.Popen(c,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True) for c in commands]
        for process in processes:
            stdout,stderr=process.communicate(timeout=15)
            self.assertEqual(process.returncode,0,stdout+stderr)
        content=(self.root/'.ai-delivery/retrospectives/index.md').read_text()
        self.assertEqual(content.count('| R/RET-001 |'),1)
        self.assertEqual(content.count('| R2/RET-001 |'),1)

    def test_lock_wait_is_bounded_and_leaves_status_unchanged(self):
        lock=self.root/'.ai-delivery.lock'
        with lock.open('a+b') as handle:
            fcntl.flock(handle,fcntl.LOCK_EX | fcntl.LOCK_NB)
            before=self.status.read_bytes()
            started=time.monotonic()
            self.assert_merged_failure(self.run_archive('--no-delivery-report'),before)
            self.assertLess(time.monotonic()-started,8)

    def test_index_drift_during_validation_is_preserved(self):
        (self.req/'retrospective.md').write_text(LEDGER)
        index=self.root/'.ai-delivery/retrospectives/index.md'; index.parent.mkdir(); index.write_text(INDEX.replace('<retrospective_rows>',''))
        seeded=self.root/'.ai-delivery/scripts/validate-delivery-status.py'; seeded.parent.mkdir()
        seeded.write_text('import pathlib\np=pathlib.Path('+repr(str(index))+'); p.write_text(p.read_text()+"外部更新\\n")\nprint(\'{"valid":true,"errors":[],"diagnostics":[]}\')')
        before=self.status.read_bytes()
        self.assert_merged_failure(self.run_archive('--no-delivery-report'),before)
        self.assertTrue(index.read_text().endswith('外部更新\n'))

    def prepare_v2(self, extra_inputs=()):
        (self.root/'owner.py').write_text('def save(): return True\n')
        (self.root/'raw.log').write_text('原生测试通过\n')
        deleted=self.root/'removed.py'
        if deleted.is_file(): deleted.unlink()
        data=json.loads(self.status.read_text()); data['sub_requirements']['SR-001']['status']='merged'; self.status.write_text(json.dumps(data))
        (self.root/'.ai-delivery/meta/workflow-policy.json').write_text(json.dumps({'version':4,'verification_contract_version':2,'context':{'sources':[]}}))
        inputs=[fingerprint(self.root,str((self.sub/'design.md').relative_to(self.root))),fingerprint(self.root,'owner.py'),fingerprint(self.root,'removed.py')]
        inputs.extend(fingerprint(self.root,path) for path in extra_inputs)
        contract={'version':2,'subreq_id':'SR-001','inputs':inputs,
                  'checks':[{'id':'native','required':True,'acceptance_ids':['AC-001'],'result':'passed','mode':'executed','command':'python3 -m unittest','exit_code':0,'evidence':[fingerprint(self.root,'raw.log')]}],
                  'reviews':[{'reviewer':'fresh-reviewer','context':'fresh','result':'clean','input_sha256':input_digest(inputs),'findings':[]}]}
        contract['reviews'][-1]['verification_sha256']=review_digest(contract)
        (self.sub/'verification.md').write_text(VERIFICATION+'\n'+render_block(contract))
        validator=[sys.executable,str(ROOT/'scripts/validate-delivery-status.py'),str(self.status),'--req-root',str(self.req)]
        checked=subprocess.run(validator,capture_output=True,text=True)
        self.assertEqual(checked.returncode,0,checked.stdout+checked.stderr)

    def test_v2_actual_inputs_and_native_evidence_drift_after_valid_are_rejected(self):
        scripts=self.root/'.ai-delivery/scripts'; scripts.mkdir()
        seeded=scripts/'validate-delivery-status.py'
        for relative in ('owner.py','raw.log','removed.py'):
            with self.subTest(relative=relative):
                self.prepare_v2()
                target=self.root/relative
                seeded.write_text('import pathlib,subprocess,sys\n'+
                    'result=subprocess.run([sys.executable,'+repr(str(ROOT/'scripts/validate-delivery-status.py'))+',*sys.argv[1:]],capture_output=True,text=True)\n'+
                    'assert result.returncode==0, result.stdout+result.stderr\n'+
                    'pathlib.Path('+repr(str(target))+').write_text("验证后发生变化")\n'+
                    'sys.stdout.write(result.stdout);sys.stderr.write(result.stderr);raise SystemExit(result.returncode)\n')
                before=self.status.read_bytes()
                result=self.run_archive('--no-delivery-report')
                self.assert_merged_failure(result,before)
                self.assertIn('版本漂移',result.stderr)

    def test_v2_actual_files_are_rechecked_before_each_replace(self):
        for relative,create_directory in [('owner.py',False),('raw.log',False),('removed.py',False),('removed.py',True)]:
            with self.subTest(relative=relative,directory=create_directory):
                self.prepare_v2()
                command=self.command('--delivery-report-template',str(self.template))
                wrapper = 'import os,pathlib,runpy,sys\noriginal=os.replace\nfirst=True\ntarget=pathlib.Path(sys.argv[1])\ncreate_directory='+repr(create_directory)+'\n'+'def drift_after_report(src,dst):\n    global first\n    result=original(src,dst)\n    if first:\n        first=False\n        if create_directory: target.mkdir()\n        else: target.write_text("首个输出替换后发生变化")\n    return result\nos.replace=drift_after_report\nsys.argv=sys.argv[2:]\nrunpy.run_path(sys.argv[0],run_name="__main__")\n'
                before=self.status.read_bytes()
                result=subprocess.run([sys.executable,'-c',wrapper,str(self.root/relative),*command[1:]],capture_output=True,text=True)
                self.assert_merged_failure(result,before)
                self.assertIn('版本漂移',result.stderr)
                self.assertTrue((self.req/'delivery-report.md').is_file())
                if create_directory: (self.root/relative).rmdir()

    def test_v2_output_path_cannot_also_be_a_contract_input(self):
        self.prepare_v2([str(self.status.relative_to(self.root))])
        before=self.status.read_bytes()
        result=self.run_archive('--no-delivery-report')
        self.assert_merged_failure(result,before)
        self.assertIn('覆盖治理输入',result.stderr)

    def test_v2_unfinished_draft_sibling_does_not_block_valid_archive(self):
        self.prepare_v2()
        data=json.loads(self.status.read_text())
        data['sub_requirements']['SR-002']={'status':'draft','ui_bearing':False,'ui_truth_mode':'none','state_flow_required':False,'user_decision_required':False,'design_review':{'review_mode':'none','reviewed_design_sha256':None,'reviewed_at':None,'reviewed_by':None}}
        self.status.write_text(json.dumps(data))
        sibling=self.sub.parent/'SR-002'; sibling.mkdir()
        (sibling/'verification.md').write_text('<!-- ai-delivery-verification:contract:v2 -->\n尚未完成的草稿')
        result=self.run_archive('--no-delivery-report')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(self.status.read_text())['sub_requirements']['SR-001']['status'],'archived')
        self.assertEqual(json.loads(self.status.read_text())['sub_requirements']['SR-002']['status'],'draft')

    def test_v2_unused_optional_check_evidence_is_not_a_new_gate(self):
        self.prepare_v2()
        from verification_contract import parse_verification_v2
        contract=parse_verification_v2(self.sub/'verification.md')
        contract['checks'].append({'id':'optional','required':False,'acceptance_ids':[],'result':'not_run','evidence':None})
        contract['reviews'][-1]['verification_sha256']=review_digest(contract)
        (self.sub/'verification.md').write_text(VERIFICATION+'\n'+render_block(contract))
        result=self.run_archive('--no-delivery-report')
        self.assertEqual(result.returncode,0,result.stderr)

    def test_old_archived_sibling_is_rejected_without_rebuilding_identity(self):
        self.prepare_v2()
        data=json.loads(self.status.read_text())
        entry=dict(data['sub_requirements']['SR-001']); entry['status']='archived'
        data['sub_requirements']['SR-002']=entry; self.status.write_text(json.dumps(data))
        before=self.status.read_bytes()
        result=self.run_archive('--no-delivery-report')
        self.assert_merged_failure(result,before)
        self.assertIn('archive_evidence', result.stderr)

    def test_validator_without_consumed_files_cannot_archive_non_ui(self):
        seeded=self.root/'.ai-delivery/scripts/validate-delivery-status.py';seeded.parent.mkdir()
        seeded.write_text('print(\'{"valid":true,"errors":[],"diagnostics":[]}\')')
        before=self.status.read_bytes()
        result=self.run_archive('--no-delivery-report')
        self.assert_merged_failure(result,before)
        self.assertIn('consumed_files',result.stderr)

    def test_v2_snapshot_parser_failure_is_not_ignored(self):
        self.prepare_v2()
        command=self.command('--no-delivery-report')
        wrapper='import sys,runpy\nsys.path.insert(0,'+repr(str(ROOT/'.agents/skills/ai-delivery-orchestrator/scripts'))+')\n'+'import verification_contract\ndef fail_parse(path):\n    raise ValueError("注入共享快照解析失败")\nverification_contract.parse_verification_v2=fail_parse\nsys.argv=sys.argv[1:]\nrunpy.run_path(sys.argv[0],run_name="__main__")\n'
        before=self.status.read_bytes()
        result=subprocess.run([sys.executable,'-c',wrapper,*command[1:]],capture_output=True,text=True)
        self.assert_merged_failure(result,before)
        self.assertIn('共享快照解析失败',result.stderr)

    def test_malformed_v2_is_rejected_by_shared_validator_before_output(self):
        self.prepare_v2()
        (self.sub/'verification.md').write_text(VERIFICATION+'\n<!-- ai-delivery-verification:contract:v2 -->\n```json\n{broken\n```\n<!-- /ai-delivery-verification:contract:v2 -->')
        before=self.status.read_bytes()
        result=self.run_archive('--delivery-report-template',str(self.template))
        self.assert_merged_failure(result,before)
        self.assertIn('归档治理校验失败',result.stderr)
        self.assertFalse((self.req/'delivery-report.md').exists())

    def test_archived_history_is_not_reset_by_retry(self):
        data=json.loads(self.status.read_text()); data['sub_requirements']['SR-001']['status']='archived'; self.status.write_text(json.dumps(data))
        before=self.status.read_bytes()
        self.assert_merged_failure(self.run_archive('--no-delivery-report'), before)


if __name__ == '__main__':
    unittest.main()
