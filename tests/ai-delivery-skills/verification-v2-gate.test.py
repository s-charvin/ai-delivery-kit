#!/usr/bin/env python3
"""通过真实 status validator 检查 v4 的协议不能降为 marker gate。"""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from fixture_helpers import governed

KIT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(KIT/'.agents/skills/ai-delivery-orchestrator/scripts'))
from verification_contract import fingerprint,input_digest,render_block,review_digest


class V2GateTest(unittest.TestCase):
    def test_removed_terminal_exemption_never_authorizes_marker_only_history(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);req,sub=governed(root,status='archived')
            (sub/'verification.md').write_text('<!-- ai-delivery-verification:sign-off -->')
            policy=root/'.ai-delivery/meta/workflow-policy.json'
            data=json.loads(policy.read_text());data['legacy_terminal_slices']={};policy.write_text(json.dumps(data))
            p=subprocess.run(['python3',str(KIT/'scripts/validate-delivery-status.py'),str(req/'status.json'),'--req-root',str(req)],capture_output=True,text=True)
            self.assertNotEqual(p.returncode,0)
            self.assertIn('legacy_terminal_slices',p.stdout+p.stderr)
            self.assertIn('--reset-data',p.stdout+p.stderr)

    def test_v4_requires_current_structured_evidence_and_cannot_downgrade(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);req,sub=governed(root)
            markers='\n'.join('<!-- ai-delivery-verification:'+x+' -->' for x in ['review-rounds','commands-results','sign-off'])
            path=sub/'verification.md';path.write_text(markers)
            def validate():
                return subprocess.run(['python3',str(KIT/'scripts/validate-delivery-status.py'),str(req/'status.json'),'--req-root',str(req)],capture_output=True,text=True)
            self.assertNotEqual(validate().returncode,0,'v4 只有 markers 不可通过')
            (root/'reports').mkdir();(root/'reports/result.txt').write_text('原始结果：1 passed\n')
            inputs=[fingerprint(root,str((sub/'design.md').relative_to(root)))]
            data={'version':2,'subreq_id':'SR-001','inputs':inputs,'checks':[{'id':'native','acceptance_ids':['AC-001'],'required':True,'mode':'executed','result':'passed','command':'python3 -m unittest','exit_code':0,'evidence':[fingerprint(root,'reports/result.txt')]}],'reviews':[{'reviewer':'fixture-reviewer','context':'fresh','result':'clean','input_sha256':input_digest(inputs),'findings':[]}]}
            data['reviews'][-1]['verification_sha256']=review_digest(data)
            path.write_text(markers+'\n'+render_block(data))
            p=validate();self.assertEqual(p.returncode,0,p.stdout+p.stderr)
            # 自定义嵌套治理目录不改变 inputs 的仓库相对语义。
            (root/'tooling').mkdir()
            ad=root/'tooling/delivery';(root/'.ai-delivery').rename(ad)
            req=ad/'requirements/R';sub=req/'sub-requirements/SR-001';path=sub/'verification.md'
            (ad/'meta/project-binding.json').write_text(json.dumps({'version':3,'ai_delivery_path':'tooling/delivery','layout':{}}))
            data['inputs']=[fingerprint(root,str((sub/'design.md').relative_to(root)))]
            data['reviews'][-1]['input_sha256']=input_digest(data['inputs'])
            data['reviews'][-1]['verification_sha256']=review_digest(data)
            path.write_text(markers+'\n'+render_block(data))
            p=validate();self.assertEqual(p.returncode,0,p.stdout+p.stderr)
            (root/'reports/result.txt').write_text('新结果：failed\n')
            self.assertNotEqual(validate().returncode,0,'原始结果漂移不可保留通过')
            policy=ad/'meta/workflow-policy.json'
            policy.write_text('{"version":4,"verification_contract_version":1}')
            path.write_text(markers)
            self.assertNotEqual(validate().returncode,0,'v4不能自选弱协议绕过')


if __name__=='__main__': unittest.main()
