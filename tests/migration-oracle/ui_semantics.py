#!/usr/bin/env python3
"""开发期差分；只加载明确固定基线，不参与 Go 发行或安装后判定。"""
import argparse
import importlib.util
import json
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('--baseline', type=Path, required=True)
parser.add_argument('--corpus', type=Path, required=True)
args = parser.parse_args()
source = args.baseline / 'scripts/validate-delivery-status.py'
spec = importlib.util.spec_from_file_location('fixed_ui_baseline', source)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
results = []
for case in json.loads((args.corpus / 'go-results.json').read_text()):
    root = Path(case['root'])
    sub = root / '.ai-delivery/requirements/REQ-UI/sub-requirements/SR-001'
    errors = []
    for function, extra in ((module.check_ui_truth_index, ('figma',)),
                            (module.check_visual_acceptance, ())):
        try:
            errors += function('SR-001', sub, root, 'visual_acceptance_passed', *extra)
        except Exception as error:
            errors.append(f'{type(error).__name__}: {error}')
    valid = not errors
    results.append(dict(name=case['name'], go_valid=case['go_valid'],
                        baseline_valid=valid, match=valid == case['go_valid'],
                        baseline_diagnostics=errors))
output = args.corpus / 'baseline-comparison.json'
output.write_text(json.dumps(results, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(dict(cases=len(results), matches=sum(r['match'] for r in results),
                     output=str(output)), ensure_ascii=False))
raise SystemExit(0 if all(r['match'] for r in results) else 1)
