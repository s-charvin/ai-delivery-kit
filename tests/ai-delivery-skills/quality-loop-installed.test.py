#!/usr/bin/env python3
"""在真实 bootstrap 安装副本贯通上下文、原生测试、v2、失败恢复和单版本拒绝。"""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from fixture_helpers import governed

KIT=Path(__file__).resolve().parents[2]


class InstalledTest(unittest.TestCase):
    def test_installed_current_loop_rejects_unsupported_data_without_legacy_helper(self):
        with tempfile.TemporaryDirectory(prefix='kit-quality-installed-') as t:
            root=Path(t)/'host';root.mkdir()
            env={**os.environ,'GOCACHE':os.environ.get('AI_DELIVERY_GOCACHE','/private/tmp/ai-delivery-kit-go-cache')}
            def run(args, want=0, cwd=root):
                p=subprocess.run([str(x) for x in args],cwd=cwd,env=env,capture_output=True,text=True,timeout=120)
                self.assertEqual(p.returncode,want,p.stdout+p.stderr)
                return p
            binary=Path(t)/'ai-delivery'
            run(['go','build','-o',binary,'./cmd/ai-delivery'],cwd=KIT)
            run(['git','init','-q',root])
            run([binary,'init',root])
            req,sub=governed(root,preserve_metadata=True)
            (req/'requirement.md').write_text('对相同值重复保存不能添加重复项。')
            (root/'owner.py').write_text('def save(items, value):\n    if value not in items:\n        items.append(value)\n    return items\n')
            (root/'test_owner.py').write_text('import unittest\nfrom owner import save\nclass SaveTest(unittest.TestCase):\n    def test_duplicate(self):\n        values=[]\n        save(values,"A");save(values,"A")\n        self.assertEqual(values,["A"])\n')
            (root/'docs').mkdir(exist_ok=True)
            (root/'docs/owner-standard.md').write_text('对重复请求保持幂等，复用正式owner。')
            policy_path=root/'.ai-delivery/meta/workflow-policy.json'
            policy=json.loads(policy_path.read_text())
            self.assertEqual(policy['version'],4)
            policy['context']['sources']=[{'path':'docs/owner-standard.md','paths':['owner.py'],'kind':'standard','required':True,'writable':False}]
            policy_path.write_text(json.dumps(policy))
            (sub/'verification.md').write_text('尚未验证')
            scripts=root/'.agents/skills/ai-delivery-orchestrator/scripts'
            context=['python3',scripts/'delivery_context.py','--req-root',req,'--subreq','SR-001','--role','review','--changed-path','owner.py']
            # merged 但证据缺失：上下文应显示诊断，而不是凭状态声称可交付。
            view=json.loads(run(context,want=2).stdout)
            self.assertFalse(view['ready'])
            native=run(['python3','-m','unittest','test_owner.py'])
            (root/'reports').mkdir();(root/'reports/result.txt').write_text(native.stdout+native.stderr)
            inputs=['owner.py','test_owner.py','docs/owner-standard.md',str((sub/'design.md').relative_to(root))]
            command=['python3',scripts/'verification_contract.py','--repo-root',root]
            for path in inputs: command+=['--input',path]
            identity=json.loads(run(command).stdout)
            evidence=json.loads(run(['python3',scripts/'verification_contract.py','--repo-root',root,'--input','reports/result.txt']).stdout)['inputs']
            data={'version':2,'subreq_id':'SR-001','inputs':identity['inputs'],'checks':[{'id':'native-save','acceptance_ids':['AC-001'],'required':True,'mode':'executed','result':'passed','command':'python3 -m unittest test_owner.py','exit_code':0,'evidence':evidence}],'reviews':[{'reviewer':'integration-fixture','context':'fresh','result':'clean','input_sha256':identity['input_sha256'],'findings':[]}]}
            markers='\n'.join('<!-- ai-delivery-verification:'+x+' -->' for x in ['review-rounds','commands-results','sign-off'])
            (sub/'verification.md').write_text(markers+'\n<!-- ai-delivery-verification:contract:v2 -->\n'+chr(96)*3+'json\n'+json.dumps(data)+'\n'+chr(96)*3+'\n<!-- /ai-delivery-verification:contract:v2 -->\n')
            digest=json.loads(run(['python3',scripts/'verification_contract.py','--repo-root',root,'--verification',sub/'verification.md','--review-digest']).stdout)
            data['reviews'][-1].update(digest)
            (sub/'verification.md').write_text(markers+'\n<!-- ai-delivery-verification:contract:v2 -->\n'+chr(96)*3+'json\n'+json.dumps(data)+'\n'+chr(96)*3+'\n<!-- /ai-delivery-verification:contract:v2 -->\n')
            view=json.loads(run(context).stdout)
            self.assertTrue(view['ready'])
            self.assertIn('docs/owner-standard.md',[x['path'] for x in view['entries']])
            validator=['python3',root/'.ai-delivery/scripts/validate-delivery-status.py',req/'status.json','--req-root',req]
            run(validator)
            original=(root/'owner.py').read_text()
            (root/'owner.py').write_text(original+'# changed\n')
            self.assertNotEqual(subprocess.run([str(x) for x in validator],capture_output=True).returncode,0)
            (root/'owner.py').write_text(original)
            template=root/'report-template.md';template.write_text('# 交付 <req-id>\n<archived_at>\n<subreq_count>\n<subreq_rows>\n')
            archive=['python3',root/'.ai-delivery/scripts/archive-subrequirement.py','--req-root',req,'--subreq','SR-001','--now','2026-11-05T00:00:00+00:00','--delivery-report-template',template]
            (req/'delivery-report.md').mkdir()
            failure=subprocess.run([str(x) for x in archive],capture_output=True,text=True)
            self.assertNotEqual(failure.returncode,0)
            self.assertEqual(json.loads((req/'status.json').read_text())['sub_requirements']['SR-001']['status'],'merged')
            (req/'delivery-report.md').rmdir()
            run(archive)
            self.assertTrue((req/'delivery-report.md').is_file())
            run(validator)
            # 真实安装入口的历史读取允许后续源码演进及原生日志清理。
            (root/'owner.py').write_text(original+'# subsequent task\n')
            (root/'reports/result.txt').unlink()
            run(validator)
            # 真正安装中保留旧 helper；当前入口不得 import 或调用它。
            (scripts/'legacy_terminal.py').write_text('raise RuntimeError("old helper must never execute")')
            run(validator)
            current_policy=policy_path.read_bytes()
            current_status=(req/'status.json').read_bytes()
            policy['version']=3;policy.pop('verification_contract_version',None)
            policy_path.write_text(json.dumps(policy))
            old=policy_path.read_bytes()
            failure=subprocess.run([str(binary),'init','--upgrade',str(root)],capture_output=True,text=True)
            self.assertNotEqual(failure.returncode,0)
            self.assertIn('--reset-data',failure.stdout+failure.stderr)
            self.assertEqual(policy_path.read_bytes(),old)
            failure=subprocess.run([str(x) for x in validator],capture_output=True,text=True)
            self.assertNotEqual(failure.returncode,0)
            self.assertIn('version-upgrade.md',failure.stdout+failure.stderr)
            # 元数据恢复为当前格式仍不意味着全部需求数据兼容。
            policy_path.write_bytes(current_policy)
            state=json.loads(current_status);state['_schema']='1.0'
            (req/'status.json').write_text(json.dumps(state))
            run([binary,'init','--upgrade',root])
            self.assertTrue((scripts/'legacy_terminal.py').is_file())
            failure=subprocess.run([str(x) for x in validator],capture_output=True,text=True)
            self.assertNotEqual(failure.returncode,0)
            self.assertIn('_schema',failure.stdout+failure.stderr)
            self.assertIn('A.',failure.stdout+failure.stderr)
            self.assertIn('B.',failure.stdout+failure.stderr)
            self.assertNotIn('old helper must never execute',failure.stdout+failure.stderr)
            # 用户自行恢复已有合法当前材料，无需迁移收据或备份登记。
            (req/'status.json').write_bytes(current_status)
            run(validator)



if __name__=='__main__': unittest.main()
