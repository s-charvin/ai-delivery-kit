#!/usr/bin/env python3
"""verification.md v2：校验真实输入/报告引用与覆盖，不能证明自然语言或身份真伪。"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

START = '<!-- ai-delivery-verification:contract:v2 -->'
END = '<!-- /ai-delivery-verification:contract:v2 -->'
RESULTS = {'passed', 'failed', 'invalid', 'not_run', 'blocked', 'not_applicable', 'waived'}


def input_digest(inputs: list) -> str:
    return hashlib.sha256(json.dumps(inputs, ensure_ascii=False, sort_keys=True,
                                     separators=(',', ':')).encode()).hexdigest()


def review_digest(data: dict) -> str:
    # 排除 reviews 本身，绑定完整的结果声明且避免摘要自引用。
    claims={key:data.get(key) for key in ('version','subreq_id','inputs','checks')}
    return hashlib.sha256(json.dumps(claims,ensure_ascii=False,sort_keys=True,
                                     separators=(',', ':')).encode()).hexdigest()


def render_block(data: dict) -> str:
    return START+'\n```json\n'+json.dumps(data,ensure_ascii=False,indent=2)+'\n```\n'+END+'\n'


def fingerprint(root: Path, path: str) -> dict:
    relative=Path(path)
    if not path or relative.is_absolute() or '..' in relative.parts:
        raise ValueError(f'非法相对证据路径：{path}')
    target=(root/relative).resolve()
    if not target.is_relative_to(root.resolve()):
        raise ValueError(f'证据越界：{path}')
    from evidence_identity import observe_file
    observe_file(root/relative)
    if not target.exists():
        return {'path':relative.as_posix(), 'sha256':None, 'state':'absent'}
    return {'path':relative.as_posix(), 'sha256':hashlib.sha256(target.read_bytes()).hexdigest()}


def validate_contract(data: dict, root: Path, design: Path, subreq: str,
                      acceptance_ids: set[str]) -> list[str]:
    errors=[]
    if not isinstance(data,dict) or data.get('version')!=2:
        return ['verification contract 必须为 version 2 对象']
    if data.get('subreq_id')!=subreq: errors.append('verification subreq_id 不匹配')
    inputs=data.get('inputs')
    if not isinstance(inputs,list) or not inputs:
        return errors+['verification inputs 不能为空']
    def check_files(entries, label, allow_absent=False):
        if not isinstance(entries,list) or not entries:
            errors.append(f'{label} 缺少文件证据');return set()
        seen=set()
        for entry in entries:
            if not isinstance(entry,dict) or not isinstance(entry.get('path'),str):
                errors.append(f'{label} 非法文件条目');continue
            path=entry['path']
            if path in seen: errors.append(f'{label} 路径重复：{path}')
            seen.add(path)
            digest=entry.get('sha256')
            if allow_absent and entry.get('state')=='absent' and digest is None:
                try:
                    if fingerprint(root,path).get('state')!='absent':
                        errors.append(f'{label} 已删除输入重新出现：{path}')
                except (OSError,ValueError) as exc: errors.append(f'{label} {exc}')
                continue
            if not isinstance(digest,str) or not re.fullmatch('[0-9a-f]{64}',digest):
                errors.append(f'{label} 缺少有效 SHA-256：{path}');continue
            try:
                current=fingerprint(root,path)
                if current.get('state')=='absent' or current['sha256']!=digest:
                    errors.append(f'{label} 输入已变化：{path}')
            except (OSError,ValueError) as exc: errors.append(f'{label} {exc}')
        return seen
    input_paths=check_files(inputs,'inputs',allow_absent=True)
    try:
        design_rel=design.resolve().relative_to(root.resolve()).as_posix()
        if design_rel not in input_paths: errors.append('inputs 必须绑定当前 design.md')
    except ValueError: errors.append('design 越出项目根')
    checks=data.get('checks')
    if not isinstance(checks,list) or not checks: return errors+['verification checks 不能为空']
    if not any(isinstance(c,dict) and c.get('required') is True for c in checks):
        errors.append('至少需要一项必需检查')
    covered=set();ids=set()
    def authority(value):
        return isinstance(value,dict) and all(isinstance(value.get(k),str) and value[k].strip()
            for k in ('by','at','reason','source_ref'))
    for check in checks:
        if not isinstance(check,dict): errors.append('非法 check');continue
        cid=check.get('id')
        if not isinstance(cid,str) or not cid.strip() or cid in ids:
            errors.append('check ID 缺失或重复')
        else: ids.add(cid)
        result=check.get('result'); required=check.get('required')
        if not isinstance(required,bool): errors.append(f'{cid} required 必须明确为布尔值')
        if result not in RESULTS: errors.append(f'{cid} 未知 result')
        acs=check.get('acceptance_ids')
        if not isinstance(acs,list) or any(not isinstance(x,str) or x not in acceptance_ids for x in acs):
            errors.append(f'{cid} acceptance_ids 非法');acs=[]
        accepted=False
        if result=='passed':
            mode=check.get('mode')
            if mode not in ('executed','reused','manual'): errors.append(f'{cid} 缺少 mode')
            if not isinstance(check.get('command'),str) or not check['command'].strip(): errors.append(f'{cid} 缺少实际命令/步骤')
            if mode!='manual' and (type(check.get('exit_code')) is not int or check['exit_code']!=0):
                errors.append(f'{cid} passed 与实际退出码不一致')
            if mode=='reused' and not check.get('reuse_reason'): errors.append(f'{cid} 缺少复用依据')
            if mode=='manual' and not authority(check.get('confirmation')): errors.append(f'{cid} 手工验证缺少确认来源')
            evidence=check_files(check.get('evidence'),str(cid))
            # 验证材料不能以合同自身代替原始命令输出。
            if any(Path(p).name=='verification.md' for p in evidence): errors.append(f'{cid} 不能自引用 verification.md 作为运行证据')
            accepted=True
        elif result=='waived':
            if not authority(check.get('waiver')): errors.append(f'{cid} 豁免缺少明确授权来源')
            accepted=True
        elif result=='not_applicable':
            if not check.get('source_ref') or not check.get('reason'): errors.append(f'{cid} 不适用缺少范围依据')
        elif required:
            errors.append(f'{cid} 必需检查未通过：{result}')
        if accepted: covered.update(acs)
    if not acceptance_ids: errors.append('design 没有可定位的 AC')
    if acceptance_ids-covered: errors.append('AC 缺少通过/有效豁免证据：'+', '.join(sorted(acceptance_ids-covered)))
    reviews=data.get('reviews')
    if not isinstance(reviews,list) or not reviews: return errors+['缺少新鲜上下文评审记录']
    # 历史轮次可保留；最后一项是当前完整范围的适用评审。
    review=reviews[-1]
    if not isinstance(review,dict): return errors+['非法评审条目']
    if not isinstance(review.get('reviewer'),str) or not review['reviewer'].strip(): errors.append('缺少实际可见 reviewer')
    if review.get('context')!='fresh' or review.get('result')!='clean': errors.append('最新适用评审不为 fresh/clean')
    if review.get('input_sha256')!=input_digest(inputs): errors.append('评审绑定的输入摘要已失效')
    if review.get('verification_sha256')!=review_digest(data): errors.append('评审绑定的验证结果摘要已失效')
    findings=review.get('findings')
    if not isinstance(findings,list): errors.append('评审 findings 必须为列表')
    else:
        for finding in findings:
            if not isinstance(finding,dict) or finding.get('disposition') not in ('resolved','rejected','advisory','waived') or not finding.get('source_ref'):
                errors.append('存在未处置/无来源 finding')
    return errors


def parse_verification_v2(path: Path) -> dict:
    text=path.read_text(encoding='utf-8')
    from layout import compatibility_error, require_current_format
    if START not in text:
        raise compatibility_error(path, 'verification contract version', 'missing current contract block', 2)
    if text.count(START)!=1 or text.count(END)!=1:
        raise ValueError('需要唯一 verification contract v2 结果块')
    block=text.split(START,1)[1].split(END,1)[0].strip()
    match=re.fullmatch(r'```json\s*\n(.*?)\n```',block,re.S)
    if not match: raise ValueError('verification contract 需要完整 JSON fenced block')
    data=json.loads(match[1])
    if not isinstance(data,dict): raise ValueError('verification contract 必须为对象')
    require_current_format(path, data, 'version', 2)
    return data


def check_verification_v2(path: Path, root: Path, design: Path, subreq: str) -> list[str]:
    try:
        data=parse_verification_v2(path)
        from design_contract import acceptance_ids
        acs=acceptance_ids(design.read_text(encoding='utf-8'))
        return validate_contract(data,root,design,subreq,acs)
    except (OSError,ValueError,TypeError) as exc: return [f'verification contract 无效：{exc}']


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo-root',type=Path,required=True)
    parser.add_argument('--input',action='append',default=[])
    parser.add_argument('--verification',type=Path)
    parser.add_argument('--design',type=Path)
    parser.add_argument('--subreq')
    parser.add_argument('--review-digest',action='store_true',help='只计算评审绑定摘要，不生成评审或通过结论')
    args=parser.parse_args()
    if args.review_digest:
        if not args.verification: parser.error('--review-digest 需要 --verification')
        try:
            data=parse_verification_v2(args.verification)
            print(json.dumps({'input_sha256':input_digest(data.get('inputs')),
                              'verification_sha256':review_digest(data)},indent=2));return 0
        except (OSError,ValueError,TypeError) as exc:
            print(json.dumps({'errors':[str(exc)]},ensure_ascii=False));return 2
    if args.verification:
        if not args.design or not args.subreq: parser.error('验证需要 --design 与 --subreq')
        errors=check_verification_v2(args.verification,args.repo_root,args.design,args.subreq)
        print(json.dumps({'errors':errors},ensure_ascii=False,indent=2));return 2 if errors else 0
    try:
        inputs=[fingerprint(args.repo_root,p) for p in sorted(set(args.input))]
        print(json.dumps({'inputs':inputs,'input_sha256':input_digest(inputs)},ensure_ascii=False,indent=2));return 0
    except (OSError,ValueError) as exc:
        print(json.dumps({'errors':[str(exc)]},ensure_ascii=False));return 2


if __name__=='__main__': sys.exit(main())
