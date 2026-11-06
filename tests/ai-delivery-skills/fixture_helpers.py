"""测试夹具：生成独立期望的最小有效治理切片；不替代生产校验。"""
import hashlib
import json
from pathlib import Path


def governed(root: Path, *, version=4, status='merged', preserve_metadata=False):
    req=root/'.ai-delivery/requirements/R'
    sub=req/'sub-requirements/SR-001'
    sub.mkdir(parents=True)
    meta=root/'.ai-delivery/meta';meta.mkdir(parents=True,exist_ok=True)
    if not preserve_metadata:
        (meta/'project-binding.json').write_text('{"version":3,"layout": {}}')
        (meta/'workflow-policy.json').write_text(json.dumps({'version':version,'verification_contract_version':2 if version==4 else 1,'context':{'sources':[]}}))
    design=sub/'design.md'
    design.write_text('''# 测试设计
<!-- ai-delivery:behavior-contract:start -->
<!-- ai-delivery:behavior-contract:scope -->
## 范围
保存请求一次。
<!-- ai-delivery:behavior-contract:behavior -->
## 行为
| ID | Given | When | Then |
|---|---|---|---|
| B-001 | 请求 | 提交 | 保存一次 |
<!-- ai-delivery:behavior-contract:acceptance -->
## 验收
| ID | Outcome | Evidence |
|---|---|---|
| AC-001 | B-001 可观察 | 原生测试 |
<!-- ai-delivery:behavior-contract:traceability -->
## 追溯
| Behavior | Requirement | UI | Acceptance |
|---|---|---|---|
| B-001 | R | not_applicable | AC-001 |
<!-- ai-delivery:behavior-contract:end -->
<!-- ai-delivery:user-decisions -->
## 用户决定
not_applicable
''')
    data={'_schema':'2.0','requirement_id':'R','runtime_mode':'closing','current_checkpoint':None,'sub_requirements':{'SR-001':{'status':status,'ui_truth_mode':'none','ui_bearing':False,'state_flow_required':False,'user_decision_required':False,'design_review':{'review_mode':'self','reviewed_design_sha256':hashlib.sha256(design.read_bytes()).hexdigest(),'reviewed_at':'2026-11-05T00:00:00Z','reviewed_by':'fixture'}}}}
    (req/'status.json').write_text(json.dumps(data))
    (req/'retrospective.md').write_text('<!-- ai-delivery-retrospective:reviewed-at:2026-11-05 -->\n')
    return req,sub


def seed_verification(root: Path, sub: Path, sid='SR-001', verification=None):
    """独立生成当前验证协议夹具；只用于测试，不构造生产验收结论。"""
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / '.agents/skills/ai-delivery-orchestrator/scripts'))
    from verification_contract import fingerprint, input_digest, review_digest, render_block
    report = root / 'native.log'
    report.write_text('测试夹具原生日志：1 passed\n')
    inputs = [fingerprint(root, str((sub / 'design.md').relative_to(root)))]
    data = {'version': 2, 'subreq_id': sid, 'inputs': inputs, 'checks': [
        {'id': 'native', 'acceptance_ids': ['AC-001'], 'required': True, 'result': 'passed',
         'mode': 'executed', 'command': 'python3 -m unittest', 'exit_code': 0,
         'evidence': [fingerprint(root, 'native.log')]}], 'reviews': [
        {'reviewer': 'fixture-reviewer', 'context': 'fresh', 'result': 'clean',
         'input_sha256': input_digest(inputs), 'findings': []}]}
    data['reviews'][-1]['verification_sha256'] = review_digest(data)
    markers = '\n'.join('<!-- ai-delivery-verification:' + x + ' -->' for x in ('review-rounds', 'commands-results', 'sign-off'))
    (verification or sub / 'verification.md').write_text(markers + '\n' + render_block(data))
    return data
