#!/usr/bin/env python3
"""独立审查发现的路由边界，使用真实解析、校验进程和宿主文件。"""
import copy
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from fixture_helpers import governed, seed_verification

KIT = Path(__file__).resolve().parents[2]
SCRIPTS = KIT / '.agents/skills/ai-delivery-orchestrator/scripts'
sys.path.insert(0, str(SCRIPTS))
import layout
spec = importlib.util.spec_from_file_location('routing_review', SCRIPTS / 'reconcile-delivery.py')
route = importlib.util.module_from_spec(spec)
spec.loader.exec_module(route)
VALIDATOR = KIT / 'scripts/validate-delivery-status.py'


class RoutingReviewTest(unittest.TestCase):
    def test_malformed_required_markers_cannot_authorize_empty_verification(self):
        with tempfile.TemporaryDirectory() as tmp:
            host = Path(tmp)
            req, sub = governed(host, version=4)
            (sub / 'verification.md').write_text('')
            policy = host / '.ai-delivery/meta/workflow-policy.json'
            for markers in ([None], [], [''], ['   '], ['valid', None], 'not-a-list'):
                with self.subTest(markers=markers):
                    policy.write_text(json.dumps({'version':4, 'verification_contract_version':2, 'verification_policy':{'required_markers':markers}}))
                    result = route.reconcile(req / 'status.json', req, VALIDATOR)
                    self.assertEqual(result['next_action'], 'none', result)
                    self.assertTrue(any(d['category']=='policy' for d in result['diagnostics']), result)
            policy.write_text(json.dumps({'version':4, 'verification_contract_version':2, 'verification_policy':{'required_markers':['valid-marker']}}))
            seed_verification(host, sub)
            verification=sub/'verification.md';verification.write_text('valid-marker\n'+verification.read_text())
            self.assertEqual(route.reconcile(req / 'status.json', req, VALIDATOR)['next_action'], 'archive')

    def test_binding_declared_root_must_match_actual_binding_location(self):
        with tempfile.TemporaryDirectory() as tmp:
            host = Path(tmp)
            req, _ = governed(host, version=4, status='design_ready')
            binding = host / '.ai-delivery/meta/project-binding.json'
            binding.write_text(json.dumps({'version':3,'ai_delivery_path':'governed', 'layout':{}}))
            result = route.reconcile(req / 'status.json', req, VALIDATOR)
            self.assertEqual(result['next_action'], 'none', result)
            self.assertTrue(any(d['category']=='binding' for d in result['diagnostics']), result)
            with self.assertRaises(ValueError):
                layout.artifact_path(host, 'status', req_id='R')
            (host / '.ai-delivery').rename(host / 'governed')
            req = host / 'governed/requirements/R'
            result = route.reconcile(req / 'status.json', req, VALIDATOR)
            self.assertEqual(result['next_action'], 'implement', result)
            self.assertEqual(layout.artifact_path(host, 'status', req_id='R'), layout.requirement_artifact_path(req, 'status'))

    def test_symlinked_subrequirement_cannot_read_external_design(self):
        with tempfile.TemporaryDirectory() as tmp:
            host = Path(tmp)
            req, sub = governed(host, version=4, status='design_ready')
            external = host / 'external'
            sub.rename(external)
            sub.symlink_to(external, target_is_directory=True)
            result = route.reconcile(req / 'status.json', req, VALIDATOR)
            self.assertEqual(result['next_action'], 'none', result)
            self.assertTrue(result['diagnostics'], result)
            with self.assertRaises(ValueError):
                layout.subreq_artifact_path(sub, 'solution_design')
            with self.assertRaises(ValueError):
                layout.artifact_path(host, 'solution_design', req_id='R', sr_id='SR-001')
            (host / '.ai-delivery/meta/project-binding.json').unlink()
            result = route.reconcile(req / 'status.json', req, VALIDATOR)
            self.assertEqual(result['next_action'], 'none', result)
            self.assertTrue(result['diagnostics'], result)

    def test_symlinked_artifact_targets_stay_inside_governed_root(self):
        for with_binding in (True, False):
            for kind, relative in (('solution_design','design.md'), ('verification','verification.md'), ('ui_truth_index','contracts/ui-truth-index.json')):
                with self.subTest(binding=with_binding, kind=kind), tempfile.TemporaryDirectory() as tmp:
                    host = Path(tmp)
                    req, sub = governed(host, version=4, status='design_ready')
                    if not with_binding:
                        (host / '.ai-delivery/meta/project-binding.json').unlink()
                    target = sub / relative
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.unlink(missing_ok=True)
                    external = host / 'outside.json'
                    external.write_text('{}')
                    target.symlink_to(external)
                    with self.assertRaises(ValueError):
                        layout.requirement_artifact_path(req, kind, sr_id='SR-001')
                    with self.assertRaises(ValueError):
                        layout.subreq_artifact_path(sub, kind)

    def test_symlinked_requirement_cannot_lose_governed_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            host = Path(tmp)
            req, _ = governed(host, version=4, status='design_ready')
            external = host / 'external-requirement'
            req.rename(external)
            req.symlink_to(external, target_is_directory=True)
            result = route.reconcile(req / 'status.json', req, VALIDATOR)
            self.assertEqual(result['next_action'], 'none', result)
            cli = subprocess.run([sys.executable, str(SCRIPTS / 'reconcile-delivery.py'), str(req / 'status.json'), '--req-root', str(req)], capture_output=True, text=True)
            self.assertNotEqual(cli.returncode, 0, cli.stdout + cli.stderr)
            self.assertIn('NEXT_ACTION=none', cli.stdout)

    def test_local_malformed_index_does_not_block_independent_slice(self):
        with tempfile.TemporaryDirectory() as tmp:
            host = Path(tmp)
            req, sub = governed(host, version=4, status='design_ready')
            status = req / 'status.json'
            values = json.loads(status.read_text())
            second = req / 'sub-requirements/SR-002'
            second.mkdir()
            shutil.copyfile(sub / 'design.md', second / 'design.md')
            values['sub_requirements']['SR-002'] = copy.deepcopy(values['sub_requirements']['SR-001'])
            values['sub_requirements']['SR-001'].update(ui_truth_mode='figma', ui_bearing=True)
            status.write_text(json.dumps(values))
            (req / 'dependency-graph.json').write_text(json.dumps({'nodes':{'SR-001':{'depends_on':[]}, 'SR-002':{'depends_on':[]}}}))
            index = sub / 'contracts/ui-truth-index.json'
            index.parent.mkdir()
            for data in ({'units':None}, {'units':[{'scenarios':None}]}, {'ui_truth_mode':[], 'units':[]}, {'ui_truth_mode':'figma', 'design_source':{'evidence_origin':[]}, 'units':[]}):
                with self.subTest(index=data):
                    index.write_text(json.dumps(data))
                    result = route.reconcile(status, req, VALIDATOR)
                    self.assertEqual((result['next_action'], result['next_subreq']), ('implement','SR-002'), result)
                    self.assertTrue(result['errors'], result)
                    self.assertTrue(result['diagnostics'], result)
                    self.assertTrue(all(d['scope']==['SR-001'] for d in result['diagnostics']), result)


if __name__ == '__main__':
    unittest.main()
