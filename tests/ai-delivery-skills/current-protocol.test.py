#!/usr/bin/env python3
"""单版本入口：拒绝旧协议并保留当前草稿、历史身份及安全锁。"""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

KIT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KIT / '.agents/skills/ai-delivery-orchestrator/scripts'))
from layout import DeliveryInputError, load_layout_from_ai_delivery_dir, load_workflow_policy, inspect_delivery_inputs
from fixture_helpers import governed, seed_verification


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


class CurrentProtocol(unittest.TestCase):
    def host(self, root):
        req, sub = governed(root, status='draft')
        (root / '.ai-delivery/meta/project-binding.json').write_text('{"version":3,"layout":{}}')
        data = json.loads((req / 'status.json').read_text())
        data['sub_requirements']['SR-001']['design_review'] = {'review_mode':'none','reviewed_design_sha256':None}
        (req / 'status.json').write_text(json.dumps(data))
        return req, sub

    def test_metadata_only_current_versions(self):
        for filename, field, expected, values in [
            ('project-binding.json', 'version', 3, [None, 1, 2, 4, True]),
            ('workflow-policy.json', 'version', 4, [None, 1, 2, 3, 5, True]),
            ('workflow-policy.json', 'verification_contract_version', 2, [None, 1, 3, True]),
        ]:
            for actual in values:
                with self.subTest(filename=filename, field=field, actual=actual), tempfile.TemporaryDirectory() as td:
                    root = Path(td); req, _ = self.host(root)
                    path = root / '.ai-delivery/meta' / filename
                    data = json.loads(path.read_text()); data[field] = actual; path.write_text(json.dumps(data))
                    with self.assertRaises(DeliveryInputError) as caught:
                        if filename == 'project-binding.json': load_layout_from_ai_delivery_dir(path.parent.parent)
                        else: load_workflow_policy(req)
                    self.assertEqual(caught.exception.category, 'compatibility')
                    message = str(caught.exception)
                    for token in (str(path), field, str(expected), '--reset-data', 'version-upgrade.md', 'A.', 'B.'):
                        self.assertIn(token, message)

    def test_missing_metadata_is_damage_not_legacy(self):
        for filename in ('project-binding.json','workflow-policy.json'):
            with self.subTest(filename=filename), tempfile.TemporaryDirectory() as td:
                root=Path(td); req,_=self.host(root)
                (root/'.ai-delivery/meta'/filename).unlink()
                _, issues=inspect_delivery_inputs(req/'status.json',req,json.loads((req/'status.json').read_text()))
                self.assertTrue(issues)
                self.assertNotEqual(issues[0]['category'],'compatibility')

    def test_custom_root_missing_binding_stays_governed_for_real_consumers(self):
        for policy_kind in ('current', 'old', 'malformed', 'dangling'):
            for has_status in (True, False):
                with self.subTest(policy=policy_kind, has_status=has_status), tempfile.TemporaryDirectory() as td:
                    root=Path(td);req,_=self.host(root)
                    (root/'tooling').mkdir()
                    custom=root/'tooling/delivery';(root/'.ai-delivery').rename(custom)
                    (custom/'meta/project-binding.json').unlink()
                    policy=custom/'meta/workflow-policy.json'
                    if policy_kind == 'old': policy.write_text('{"version":1}')
                    elif policy_kind == 'malformed': policy.write_text('{broken')
                    elif policy_kind == 'dangling':
                        policy.unlink();policy.symlink_to('missing-policy.json')
                    req=custom/'requirements/R';status=req/'status.json'
                    if not has_status: status.unlink()
                    if has_status:
                        p=subprocess.run([sys.executable,str(KIT/'scripts/validate-delivery-status.py'),str(status),'--req-root',str(req),'--format','json'],capture_output=True,text=True)
                        self.assertNotEqual(p.returncode,0,p.stdout+p.stderr)
                        report=json.loads(p.stdout)
                        self.assertFalse(report['valid'])
                        self.assertTrue(any(x['category']=='binding' and x['path'].endswith('/meta/project-binding.json') for x in report['diagnostics']),report)
                    p=subprocess.run([sys.executable,str(KIT/'.agents/skills/ai-delivery-orchestrator/scripts/reconcile-delivery.py'),str(status),'--req-root',str(req)],capture_output=True,text=True)
                    self.assertNotEqual(p.returncode,0,p.stdout+p.stderr)
                    self.assertIn('NEXT_ACTION=none',p.stdout)
                    self.assertIn('project-binding.json',p.stdout+p.stderr)

    def test_layout_validator_uses_current_default_and_custom_artifact_paths(self):
        from verification_contract import parse_verification_v2, fingerprint, input_digest, review_digest, render_block
        fixtures=module('current_ui_fixture', KIT/'tests/ai-delivery-skills/evidence-lifecycle.test.py')
        for custom in (False, True):
            with self.subTest(custom=custom), tempfile.TemporaryDirectory() as td:
                ns=fixtures.ui_fixture(Path(td));root,req,sub=ns['repo'],ns['req_root'],ns['subreq']
                originals={'solution_design':'design.md','verification':'verification.md','ui_truth_index':'contracts/ui-truth-index.json','visual_acceptance':'visual-acceptance.json'}
                paths={kind:sub/relative for kind,relative in originals.items()}
                if custom:
                    names={'solution_design':'evidence/solution.md','verification':'evidence/verify.md','ui_truth_index':'truth/index.json','visual_acceptance':'acceptance/result.json'}
                    for kind,relative in names.items():
                        destination=sub/relative;destination.parent.mkdir(exist_ok=True)
                        paths[kind].rename(destination);paths[kind]=destination
                    binding={'version':3,'layout':{'sub_requirement_artifacts':{kind:'requirements/{req_id}/sub-requirements/{sr_id}/'+relative for kind,relative in names.items()}}}
                    (root/'.ai-delivery/meta/project-binding.json').write_text(json.dumps(binding))
                    contract=parse_verification_v2(paths['verification'])
                    contract['inputs']=[fingerprint(root,str(paths['solution_design'].relative_to(root)))]
                    contract['reviews'][-1]['input_sha256']=input_digest(contract['inputs'])
                    contract['reviews'][-1]['verification_sha256']=review_digest(contract)
                    markers='\n'.join('<!-- ai-delivery-verification:'+x+' -->' for x in ('review-rounds','commands-results','sign-off'))
                    paths['verification'].write_text(markers+'\n'+render_block(contract))
                status_validator=[sys.executable,str(KIT/'scripts/validate-delivery-status.py'),str(req/'status.json'),'--req-root',str(req)]
                layout_validator=[sys.executable,str(KIT/'scripts/validate-artifact-layout.py'),str(req)]
                for command in (status_validator,layout_validator):
                    p=subprocess.run(command,capture_output=True,text=True)
                    self.assertEqual(p.returncode,0,p.stdout+p.stderr)
                # 自定义路径必须实际参与 scenario 引用检查，不能仅忽略默认路径缺失。
                design=paths['solution_design'];original=design.read_text();design.write_text(original.replace('default-phone','different-scenario'))
                p=subprocess.run(layout_validator,capture_output=True,text=True)
                self.assertNotEqual(p.returncode,0,p.stdout+p.stderr)
                self.assertIn('default-phone',p.stdout+p.stderr)
                design.write_text(original)
                # 当前模式禁用 UI 时，也必须发现映射路径中的 UI 产物。
                data=json.loads((req/'status.json').read_text());entry=data['sub_requirements']['SR-001'];entry['ui_truth_mode']='none';entry['ui_bearing']=False
                (req/'status.json').write_text(json.dumps(data))
                p=subprocess.run(layout_validator,capture_output=True,text=True)
                self.assertNotEqual(p.returncode,0,p.stdout+p.stderr)
                self.assertIn('forbidden',p.stdout+p.stderr)

    def test_compatibility_recovery_keeps_hash_characters_in_real_project_paths(self):
        import shlex
        for name in ('project#foo', 'project#SR-001', 'project#sub_requirements'):
            for conflict in ('policy', 'entry'):
                with self.subTest(project=name, conflict=conflict), tempfile.TemporaryDirectory() as td:
                    root=Path(td)/name;req,_=self.host(root)
                    if conflict == 'policy':
                        (root/'.ai-delivery/meta/workflow-policy.json').write_text('{"version":3}')
                    else:
                        data=json.loads((req/'status.json').read_text());data['sub_requirements']['SR-001']['design_approved']=True
                        (req/'status.json').write_text(json.dumps(data))
                    p=subprocess.run([sys.executable,str(KIT/'scripts/validate-delivery-status.py'),str(req/'status.json'),'--req-root',str(req),'--format','json'],capture_output=True,text=True)
                    self.assertNotEqual(p.returncode,0,p.stdout+p.stderr)
                    report=json.loads(p.stdout);issues=[x for x in report['diagnostics'] if x['category']=='compatibility']
                    self.assertTrue(issues,report)
                    command='ai-delivery init --upgrade --reset-data '+shlex.quote(str(root.absolute()))
                    for issue in issues:
                        self.assertIn(command,issue['message'])
                        self.assertIn(command,issue['recovery'])

    def test_status_schema_and_removed_checkpoint_rejected_for_terminal_entries(self):
        for schema, checkpoint in [('1.0',None), (None,None), ('3.0',None), ('2.0','CP-001')]:
            with self.subTest(schema=schema, checkpoint=checkpoint), tempfile.TemporaryDirectory() as td:
                root=Path(td); req,_=self.host(root)
                data=json.loads((req/'status.json').read_text()); data['_schema']=schema;data['current_checkpoint']=checkpoint
                data['sub_requirements']['SR-001']['status']='archived'
                _,issues=inspect_delivery_inputs(req/'status.json',req,data)
                self.assertTrue(any(x['category']=='compatibility' for x in issues),issues)

    def test_metadata_removed_participation_is_compatibility_for_all_consumers(self):
        for filename in ('project-binding.json', 'workflow-policy.json'):
            with self.subTest(filename=filename), tempfile.TemporaryDirectory() as td:
                root=Path(td);req,_=self.host(root)
                path=root/'.ai-delivery/meta'/filename
                data=json.loads(path.read_text());data['tools']=[{'participation':'no_design_client'}];path.write_text(json.dumps(data))
                p=subprocess.run([sys.executable,str(KIT/'scripts/validate-delivery-status.py'),str(req/'status.json'),'--req-root',str(req),'--format','json'],capture_output=True,text=True)
                self.assertNotEqual(p.returncode,0,p.stdout+p.stderr)
                report=json.loads(p.stdout)
                self.assertTrue(any(x['category']=='compatibility' and x['path']==str(path) and 'participation' in x['message'] for x in report['diagnostics']),report)

    def test_removed_snapshot_option_preserves_explicit_directory_recovery_root(self):
        import shlex
        for path in (KIT,):
            p=subprocess.run([sys.executable,str(KIT/'scripts/validate-artifact-layout.py'),'--verify-archive'],cwd=path,capture_output=True,text=True)
            self.assertNotEqual(p.returncode,0)
            self.assertIn('ai-delivery init --upgrade --reset-data '+shlex.quote(str(path))+'。',p.stderr)
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            for explicit in (False,True):
                command=[sys.executable,str(KIT/'scripts/validate-artifact-layout.py'),'--verify-archive']
                if explicit: command.append(str(root))
                p=subprocess.run(command,cwd=root,capture_output=True,text=True)
                self.assertNotEqual(p.returncode,0)
                expected=root if explicit else root.resolve()
                self.assertIn('ai-delivery init --upgrade --reset-data '+shlex.quote(str(expected))+'。',p.stderr)

    def test_removed_snapshot_option_does_not_guess_unknown_directory_parent(self):
        with tempfile.TemporaryDirectory() as td:
            missing=Path(td)/'missing-project'
            p=subprocess.run([sys.executable,str(KIT/'scripts/validate-artifact-layout.py'),'--verify-archive',str(missing)],capture_output=True,text=True)
            self.assertNotEqual(p.returncode,0)
            self.assertIn("ai-delivery init --upgrade --reset-data '<project-root>'",p.stderr)
            self.assertIn('项目根无法确定',p.stderr)

    def test_policy_legacy_exemption_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);req,_=self.host(root)
            path=root/'.ai-delivery/meta/workflow-policy.json'
            data=json.loads(path.read_text());data['legacy_terminal_slices']={};path.write_text(json.dumps(data))
            with self.assertRaises(DeliveryInputError): load_workflow_policy(req)

    def test_current_draft_without_verification_and_backup_noise_passes(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);req,_=self.host(root)
            (root/'old-backup').mkdir();(root/'old-backup/status.json').write_text('{bad')
            p=subprocess.run([sys.executable,str(KIT/'scripts/validate-delivery-status.py'),str(req/'status.json'),'--req-root',str(req)],capture_output=True,text=True)
            self.assertEqual(p.returncode,0,p.stdout+p.stderr)

    def test_archived_without_identity_cannot_be_reapproved_from_current_bytes(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);req,sub=self.host(root)
            data=json.loads((req/'status.json').read_text());data['sub_requirements']['SR-001']['status']='archived';(req/'status.json').write_text(json.dumps(data))
            p=subprocess.run([sys.executable,str(KIT/'scripts/validate-delivery-status.py'),str(req/'status.json'),'--req-root',str(req)],capture_output=True,text=True)
            self.assertNotEqual(p.returncode,0)
            self.assertIn('archive_evidence',p.stdout+p.stderr)

    def test_archived_identity_does_not_authorize_old_contract_versions(self):
        from evidence_identity import archive_evidence
        from verification_contract import parse_verification_v2, render_block
        for kind, version in [('verification', 1), ('marker-only', None), ('ui_truth_index', 2), ('visual_acceptance', 1)]:
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as td:
                root=Path(td);req,sub=governed(root,status='archived');seed_verification(root,sub)
                data=json.loads((req/'status.json').read_text());entry=data['sub_requirements']['SR-001']
                if kind == 'verification':
                    contract=parse_verification_v2(sub/'verification.md');contract['version']=version
                    (sub/'verification.md').write_text(render_block(contract))
                elif kind == 'marker-only':
                    (sub/'verification.md').write_text('<!-- ai-delivery-verification:sign-off -->')
                else:
                    entry['ui_truth_mode']='runtime-baseline';entry['ui_bearing']=True
                    (sub/'contracts').mkdir()
                    (sub/'contracts/ui-truth-index.json').write_text(json.dumps({'schema_version':version if kind=='ui_truth_index' else 3}))
                    (sub/'visual-acceptance.json').write_text(json.dumps({'schema_version':version if kind=='visual_acceptance' else 2}))
                entry['archive_evidence']=archive_evidence(req,'SR-001',entry)
                (req/'status.json').write_text(json.dumps(data))
                p=subprocess.run([sys.executable,str(KIT/'scripts/validate-delivery-status.py'),str(req/'status.json'),'--req-root',str(req),'--format','json'],capture_output=True,text=True)
                self.assertNotEqual(p.returncode,0,p.stdout+p.stderr)
                report=json.loads(p.stdout)
                self.assertTrue(any(x['category']=='compatibility' and x['scope']==['SR-001'] for x in report['diagnostics']),report)

    def test_lock_is_stable_project_root_and_rejects_symlink(self):
        archive=module('current_archive', KIT/'scripts/archive-subrequirement.py')
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);req,_=self.host(root)
            with archive.archive_lock(req): self.assertTrue((root/'.ai-delivery.lock').is_file())
            (root/'.ai-delivery.lock').unlink();target=root/'target';target.write_text('unchanged')
            (root/'.ai-delivery.lock').symlink_to(target)
            with self.assertRaises((ValueError,OSError)):
                with archive.archive_lock(req): pass
            self.assertEqual(target.read_text(),'unchanged')

    def test_missing_current_root_cannot_create_a_different_archive_lock(self):
        archive=module('current_archive_missing', KIT/'scripts/archive-subrequirement.py')
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);req,_=self.host(root)
            (root/'tooling').mkdir()
            custom=root/'tooling/delivery';(root/'.ai-delivery').rename(custom)
            (custom/'meta/project-binding.json').write_text('{"version":3,"ai_delivery_path":"tooling/delivery","layout":{}}')
            req=custom/'requirements/R'
            with archive.archive_lock(req): self.assertTrue((root/'.ai-delivery.lock').exists())
            custom.rename(root/'backup')
            # 重建移动旧根后，旧归档调用仍能锁住同一项目根，然后在锁内报告缺材料。
            with archive.archive_lock(req): self.assertFalse((req/'.ai-delivery.lock').exists())

    def test_custom_root_recovery_command_selects_that_exact_root(self):
        import shlex
        from layout import recovery_options
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);req,_=self.host(root)
            (root/'tooling').mkdir()
            custom=root/'tooling/delivery space';(root/'.ai-delivery').rename(custom)
            (custom/'meta/project-binding.json').write_text(json.dumps({'version':3,'ai_delivery_path':'tooling/delivery space','layout':{}}))
            message=recovery_options(custom/'requirements/R/status.json')
            self.assertIn(shlex.quote('--reset-data=tooling/delivery space'),message)
            self.assertIn(shlex.quote(str(root.absolute())),message)

    def test_binding_discovery_never_scans_reserved_backups(self):
        from layout import load_layout, DEFAULT_LAYOUT
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);meta=root/'.ai-delivery-backups/meta';meta.mkdir(parents=True)
            (meta/'project-binding.json').write_text('{invalid backup')
            self.assertEqual(load_layout(root),DEFAULT_LAYOUT)

    def test_marker_only_contract_is_compatibility_diagnostic(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);req,sub=governed(root)
            (sub/'verification.md').write_text('\n'.join('<!-- ai-delivery-verification:'+x+' -->' for x in ('review-rounds','commands-results','sign-off')))
            p=subprocess.run([sys.executable,str(KIT/'scripts/validate-delivery-status.py'),str(req/'status.json'),'--req-root',str(req),'--format','json'],capture_output=True,text=True)
            report=json.loads(p.stdout)
            self.assertNotEqual(p.returncode,0)
            self.assertTrue(any(x['category']=='compatibility' and x['path'].endswith('verification.md') for x in report['diagnostics']),report)

    def test_removed_snapshot_option_is_explicit_error(self):
        p=subprocess.run([sys.executable,str(KIT/'scripts/validate-artifact-layout.py'),'--verify-archive'],capture_output=True,text=True)
        self.assertNotEqual(p.returncode,0)
        self.assertIn('version-upgrade.md',p.stdout+p.stderr)


if __name__=='__main__': unittest.main()
