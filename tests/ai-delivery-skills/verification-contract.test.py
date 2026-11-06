#!/usr/bin/env python3
"""对真实 v2 证据解析器验证空证据、伪通过与输入漂移。"""
import hashlib
import importlib.util
import json
import copy
import subprocess
from pathlib import Path
from fixture_helpers import governed
import sys
import tempfile
import unittest

KIT = Path(__file__).resolve().parents[2]
SCRIPTS = KIT/'.agents/skills/ai-delivery-orchestrator/scripts'
sys.path.insert(0,str(SCRIPTS))


class ContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module_path = SCRIPTS/'verification_contract.py'

    def setUp(self):
        self.assertTrue(self.module_path.is_file(), '尚无 v2 证据解析器')
        spec=importlib.util.spec_from_file_location('verification_contract',self.module_path)
        self.module=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        _, self.sub=governed(self.root)
        (self.root/'src').mkdir();(self.root/'src/owner.py').write_text('def save(): return 1\n')
        (self.root/'reports').mkdir();(self.root/'reports/test.txt').write_text('1 passed\n')
        inputs=[{'path':p,'sha256':hashlib.sha256((self.root/p).read_bytes()).hexdigest()} for p in ['.ai-delivery/requirements/R/sub-requirements/SR-001/design.md','src/owner.py']]
        self.data={'version':2,'subreq_id':'SR-001','inputs':inputs,
            'checks':[{'id':'test-save','acceptance_ids':['AC-001'],'required':True,'result':'passed','mode':'executed','command':'python3 -m unittest','exit_code':0,'evidence':[{'path':'reports/test.txt','sha256':hashlib.sha256((self.root/'reports/test.txt').read_bytes()).hexdigest()}]}],
            'reviews':[{'reviewer':'visible-reviewer','context':'fresh','result':'clean','input_sha256':self.module.input_digest(inputs),'findings':[]}]}
        self.refresh_review()

    def refresh_review(self):
        self.data['reviews'][-1]['verification_sha256']=self.module.review_digest(self.data)

    def validate(self):
        return self.module.validate_contract(self.data,self.root,self.sub/'design.md','SR-001',{'AC-001'})

    def test_valid_run_and_unchanged_reuse(self):
        self.assertEqual(self.validate(),[])
        self.data['checks'][0]['mode']='reused'
        self.assertTrue(self.validate(), '复用缺依据不能通过')
        self.data['checks'][0]['reuse_reason']='内容、测试、依赖与工具链未变；原始运行报告仍可读。'
        self.refresh_review()
        self.assertEqual(self.validate(),[])

    def test_empty_checks_and_self_reported_pass_rejected(self):
        self.data['checks']=[]
        self.assertTrue(self.validate())
        self.data['checks']=[{'id':'fake','required':True,'result':'passed','acceptance_ids':['AC-001'],'command':'echo ok','exit_code':7,'mode':'executed','evidence':[]}]
        self.assertTrue(self.validate())

    def test_input_and_report_tampering_invalidate_review(self):
        (self.root/'src/owner.py').write_text('def save(): return 2\n')
        self.assertTrue(self.validate())
        self.data['inputs'][1]['sha256']=hashlib.sha256((self.root/'src/owner.py').read_bytes()).hexdigest()
        self.assertTrue(self.validate(), '只更新输入 hash，旧评审仍必须失效')

    def test_invalid_not_run_skipped_or_unknown_do_not_cover_ac(self):
        for result in ['invalid','not_run','blocked','skipped','mystery']:
            self.data['checks'][0]['result']=result
            self.assertTrue(self.validate(),result)

    def test_missing_coverage_duplicate_check_and_unresolved_finding(self):
        self.data['checks'][0]['acceptance_ids']=[]
        self.assertTrue(self.validate())
        self.data['checks'][0]['acceptance_ids']=['AC-001']
        self.data['checks'].append(dict(self.data['checks'][0]))
        self.assertTrue(self.validate())
        self.data['checks'].pop()
        self.data['reviews'][0]['findings']=[{'id':'F1','disposition':'open','source_ref':'src/owner.py:1'}]
        self.assertTrue(self.validate())

    def test_contract_marker_requires_one_json_block(self):
        path=self.sub/'verification.md'
        path.write_text('<!-- ai-delivery-verification:review-rounds -->\n<!-- ai-delivery-verification:commands-results -->\n<!-- ai-delivery-verification:sign-off -->')
        self.assertTrue(self.module.check_verification_v2(path,self.root,self.sub/'design.md','SR-001'))
        path.write_text(self.module.render_block(self.data))
        self.assertEqual(self.module.check_verification_v2(path,self.root,self.sub/'design.md','SR-001'),[])

    def test_deleted_input_is_bound_to_absence_and_cannot_be_output_evidence(self):
        item=self.module.fingerprint(self.root,'src/deleted.py')
        self.assertEqual(item,{'path':'src/deleted.py','sha256':None,'state':'absent'})
        self.data['inputs'].append(item)
        self.data['reviews'][0]['input_sha256']=self.module.input_digest(self.data['inputs'])
        self.refresh_review()
        self.assertEqual(self.validate(),[])
        (self.root/'src/deleted.py').write_text('reintroduced')
        self.assertTrue(self.validate())

    def test_all_passed_checks_cannot_be_optional_or_waived_without_source(self):
        self.data['checks'][0]['required']=False
        self.assertTrue(self.validate(),'必须至少有真正的必需检查')
        self.data['checks'][0]['required']=True
        self.data['checks'][0]['result']='waived'
        self.assertTrue(self.validate(),'自报waived不能通过')

    def test_review_binds_all_verification_claims_and_cli_only_computes_digest(self):
        original=copy.deepcopy(self.data)
        for key,value in [('command','different command'),('required',False),
                          ('mode','manual'),('acceptance_ids',[]),
                          ('result','waived'),('evidence',[]),
                          ('confirmation',{'by':'someone'}),('reuse_reason','changed')]:
            self.data=copy.deepcopy(original)
            self.data['checks'][0][key]=value
            self.assertTrue(any('验证结果摘要' in e for e in self.validate()),key)
        self.data=original
        path=self.sub/'verification.md';path.write_text(self.module.render_block(self.data))
        p=subprocess.run([sys.executable,str(self.module_path),'--repo-root',str(self.root),
                          '--verification',str(path),'--review-digest'],capture_output=True,text=True)
        self.assertEqual(p.returncode,0,p.stdout+p.stderr)
        self.assertEqual(json.loads(p.stdout),{
            'input_sha256':self.module.input_digest(self.data['inputs']),
            'verification_sha256':self.module.review_digest(self.data)})


if __name__=='__main__': unittest.main()
