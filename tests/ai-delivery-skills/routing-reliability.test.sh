#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd -- "$(dirname -- "$0")/../.." && pwd)
export KIT_ROOT="$ROOT"
python3 - <<'PY'
import ast
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

root = Path(os.environ['KIT_ROOT'])
scripts = root / '.agents/skills/ai-delivery-orchestrator/scripts'
sys.path.insert(0, str(scripts))
def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod
route = load('routing_reliability', scripts / 'reconcile-delivery.py')
import layout
source = (root / 'tests/ai-delivery-skills/reconcile-delivery.test.sh').read_text().split("python3 - <<'PY'\n", 1)[1].rsplit('\nPY', 1)[0]
helpers = [n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef) and n.name in {'entry', 'design_text', 'make_ready'}]
env = {'Path': Path, 'hashlib': hashlib}
exec(compile(ast.Module(body=helpers, type_ignores=[]), '<fixtures>', 'exec'), env)
validator = root / 'scripts/validate-delivery-status.py'

with tempfile.TemporaryDirectory() as tmp:
    host = Path(tmp)
    meta=host/'.ai-delivery/meta';meta.mkdir(parents=True)
    (meta/'project-binding.json').write_text('{"version":3,"layout":{}}')
    (meta/'workflow-policy.json').write_text('{"version":4,"verification_contract_version":2,"context":{"sources":[]}}')
    req = host / '.ai-delivery/requirements/REQ-001'
    req.mkdir(parents=True)
    status = req / 'status.json'
    graph = req / 'dependency-graph.json'
    ready = env['make_ready'](req, 'SR-002')
    independent = env['make_ready'](req, 'SR-003')
    values = {'SR-001': env['entry']('blocked_verification_failure'), 'SR-002': ready}
    def save():
        status.write_text(json.dumps({'_schema':'2.0', 'sub_requirements':values}))
    def run():
        save()
        return route.reconcile(status, req, validator)
    def blocked(result):
        assert result['next_action'] == 'none', result
        assert result['runtime_mode'] == 'blocker_recovery', result
        assert result['errors'] and result['diagnostics'], result
        for item in result['diagnostics']:
            assert all(key in item for key in ('path', 'category', 'scope', 'recovery')), item
    graph.write_text(json.dumps({'nodes':{'SR-002':{'depends_on':['SR-001']}}}))
    assert run()['next_action'] == 'none'
    graph.write_text('{broken')
    blocked(run())
    values['SR-003'] = independent
    for deps in ('SR-001', ['UNKNOWN'], ['SR-001', 'SR-001'], ['SR-002']):
        graph.write_text(json.dumps({'nodes':{'SR-002':{'depends_on':deps}}}))
        result = run()
        assert result['next_action'] == 'implement' and result['next_subreq'] == 'SR-003', result
        assert any(d['scope'] == ['SR-002'] for d in result['diagnostics']), result
    graph.write_text(json.dumps({'nodes':{'SR-002':{'depends_on':['SR-003']}, 'SR-003':{'depends_on':['SR-002']}}}))
    blocked(run())
    graph.write_text(json.dumps({'nodes':{'UNKNOWN':{'depends_on':[]}}}))
    blocked(run())
    values = {'SR-002': ready}
    graph.write_text(json.dumps({'nodes':{}}))
    save()
    for name, code in [('silent', 'raise SystemExit(7)'), ('invalid', 'print("OK")'), ('contradiction', 'print(\'{"valid": true, "errors": [], "diagnostics": []}\'); raise SystemExit(4)')]:
        bad = host / (name + '.py')
        bad.write_text(code)
        blocked(route.reconcile(status, req, bad))
    blocked(route.reconcile(status, req, host / 'missing.py'))
    slow = host / 'slow.py'
    slow.write_text('import time; time.sleep(5)')
    route.VALIDATOR_TIMEOUT_SECONDS = 0.05
    blocked(route.reconcile(status, req, slow))
    route.VALIDATOR_TIMEOUT_SECONDS = 30
    values = {'SR-002': env['entry']('invented_status')}
    blocked(run())
    values = {'SR-002': env['entry']('blocked_invented')}
    blocked(run())
    for value in (None, [], {}, 7):
        values = {'SR-002': env['entry'](value)}
        blocked(run())
    values = {'SR-002': ready, 'SR-003': independent, 'SR-004': env['make_ready'](req, 'SR-004')}
    graph.write_text(json.dumps({'nodes':{'SR-002':{'depends_on':False}, 'SR-003':{'depends_on':['SR-002']}}}))
    result = run()
    assert result['next_subreq'] == 'SR-004' and result['next_action'] == 'implement', result
    graph.unlink()
    blocked(run())
    graph.write_text(json.dumps({'nodes':{}}))
    values = {'SR-002': ready}
    save()
    for identifier in ('../escape', '/absolute', '..', 'bad/path', 'bad\\path'):
        try:
            layout.requirement_subdir(req, identifier)
        except ValueError:
            pass
        else:
            raise AssertionError('非法 ID 不得解析为路径：' + identifier)
        try:
            layout.artifact_path(host, 'solution_design', req_id='REQ-001', sr_id=identifier)
        except ValueError:
            pass
        else:
            raise AssertionError('artifact 路径不得接受非法 ID：' + identifier)
    values = {'../escape': env['entry']('draft'), 'SR-002': ready}
    result = run()
    assert result['next_action'] == 'implement' and result['next_subreq'] == 'SR-002' and result['diagnostics'], result
    values = {'SR-002': ready}
    save()
    binding = host / '.ai-delivery/meta/project-binding.json'
    binding.parent.mkdir(parents=True,exist_ok=True)
    for raw in ('{broken', '[]', '{"layout": []}', '{"layout": {"requirement_artifacts": {"dependency_graph": "../escape"}}}'):
        binding.write_text(raw)
        try:
            layout.load_layout(host)
        except ValueError:
            pass
        else:
            raise AssertionError('损坏 binding 不得退回默认布局: ' + raw)
        blocked(run())
    binding.write_text(json.dumps({'version':3, 'layout':{'requirement_artifacts':{'dependency_graph':'requirements/{req_id}/relations.json'}}}))
    graph.unlink()
    (req / 'relations.json').write_text(json.dumps({'nodes':{'SR-002':{'depends_on':['SR-001']}}}))
    values['SR-001'] = env['entry']('blocked_verification_failure')
    assert run()['next_action'] == 'none'
    binding.write_text(json.dumps({'version':3, 'layout':{'requirement_artifacts':{'status':'requirements/{req_id}/state.json', 'dependency_graph':'requirements/{req_id}/relations.json'}, 'sub_requirement_dir':'requirements/{req_id}/slices/{sr_id}', 'sub_requirement_artifacts':{'solution_design':'requirements/{req_id}/slices/{sr_id}/contract.md', 'verification':'requirements/{req_id}/slices/{sr_id}/evidence.md'}}}))
    values = {'SR-002': ready}
    save()
    status.rename(req / 'state.json')
    sub = req / 'slices/SR-002'
    sub.mkdir(parents=True)
    shutil.move(req / 'sub-requirements/SR-002/design.md', sub / 'contract.md')
    (req / 'relations.json').write_text(json.dumps({'nodes':{}}))
    result = route.reconcile(req / 'state.json', req, validator)
    assert result['next_action'] == 'implement', result
    blocked(route.reconcile(status, req, validator))
    binding.write_text('{"version":3,"layout":{}}')
    policy = binding.parent / 'workflow-policy.json'
    for raw in ('{broken', '[]', '{"version":99}', '{"version":[]}', '{"version":4,"verification_policy":[]}'):
        policy.write_text(raw)
        blocked(run())
    policy.write_text('{"version":4,"verification_contract_version":2,"context":{"sources":[]}}')
    copied = host / '.agents/skills/ai-delivery-orchestrator/scripts'
    copied.mkdir(parents=True)
    for name in ('reconcile-delivery.py', 'layout.py', 'design_contract.py', 'evidence_identity.py'):
        shutil.copyfile(scripts / name, copied / name)
    save()
    cli = subprocess.run([sys.executable, '-B', str(copied / 'reconcile-delivery.py'), str(status), '--req-root', str(req)], capture_output=True, text=True)
    assert cli.returncode != 0 and 'NEXT_ACTION=none' in cli.stdout and 'validator' in cli.stdout, cli
    graph.write_text('{broken')
    status.write_text('{broken')
    blocked(route.reconcile(status, req, validator))
    status.write_text('[]')
    blocked(route.reconcile(status, req, validator))
    status.write_text(json.dumps({'_schema':'2.0', 'sub_requirements':{}}))
    graph.unlink()
    assert route.reconcile(status, req, validator)['runtime_mode'] == 'bootstrap'
    status.unlink()
    assert route.reconcile(status, req, validator)['runtime_mode'] == 'bootstrap'
    cli = subprocess.run([sys.executable, '-B', str(scripts / 'reconcile-delivery.py'), str(status), '--req-root', str(req)], capture_output=True, text=True)
    assert cli.returncode == 0 and 'RUNTIME_MODE=bootstrap' in cli.stdout and 'NEXT_ACTION=requirement-breakdown' in cli.stdout, cli
    status.write_text('{broken')
    cli = subprocess.run([sys.executable, '-B', str(scripts / 'reconcile-delivery.py'), str(status), '--req-root', str(req)], capture_output=True, text=True)
    assert cli.returncode != 0 and 'RUNTIME_MODE=blocker_recovery' in cli.stdout and 'NEXT_ACTION=none' in cli.stdout, cli
print('PASS: routing reliability')
PY
