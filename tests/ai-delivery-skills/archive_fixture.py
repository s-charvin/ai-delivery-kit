"""归档测试使用真实当前设计与结构化验证夹具。"""
import json
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / '.agents/skills/ai-delivery-orchestrator/scripts'))
from fixture_helpers import governed, seed_verification

VERIFICATION = '''# 验证记录
<!-- ai-delivery-verification:review-rounds -->
独立评审第一轮通过。
<!-- ai-delivery-verification:commands-results -->
原生测试执行成功。
<!-- ai-delivery-verification:sign-off -->
测试负责人确认通过。
'''


def govern_existing(req):
    req = Path(req)
    status_path = req / 'status.json'
    data = json.loads(status_path.read_text())
    with tempfile.TemporaryDirectory() as tmp:
        _, canonical = governed(Path(tmp))
        design = (canonical / 'design.md').read_bytes()
        exemplar = json.loads((canonical.parent.parent / 'status.json').read_text())['sub_requirements']['SR-001']
    data['_schema'] = '2.0'
    for sid, entry in data['sub_requirements'].items():
        sub = req / 'sub-requirements' / sid
        sub.mkdir(parents=True, exist_ok=True)
        (sub / 'design.md').write_bytes(design)
        data['sub_requirements'][sid] = {**exemplar, **{'status': entry['status']}}
    status_path.write_text(json.dumps(data, indent=2) + '\n')
    ad = next(p for p in req.parents if p.name == '.ai-delivery' or (p / 'meta/project-binding.json').exists())
    (ad / 'meta').mkdir(parents=True, exist_ok=True)
    binding = ad / 'meta/project-binding.json'
    if not binding.exists():
        binding.write_text('{"version":3,"layout": {}}')
    binding_data=json.loads(binding.read_text()); binding_data['version']=3; binding.write_text(json.dumps(binding_data))
    (ad / 'meta/workflow-policy.json').write_text(json.dumps({'version': 4, 'verification_contract_version': 2, 'context': {'sources': []}}))

    from layout import repo_root_from_ai_delivery_dir
    root=repo_root_from_ai_delivery_dir(ad)
    for sid in data['sub_requirements']:
        seed_verification(root, req/'sub-requirements'/sid, sid)


if __name__ == '__main__':
    govern_existing(sys.argv[1])
