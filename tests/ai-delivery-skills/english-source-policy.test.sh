#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "$0")" && pwd)
ROOT=$(cd -- "$SCRIPT_DIR/../.." && pwd)

for rel in \
  .agents/skills/ai-delivery-orchestrator/references/retrospective-guidance.md \
  .agents/skills/ai-delivery-orchestrator/templates/retrospective-template.md \
  .agents/skills/ai-delivery-orchestrator/templates/retrospective-index-template.md
do
  [[ -f "$ROOT/$rel" ]] || { printf '%s\n' "[english-source-policy.test] missing $rel" >&2; exit 1; }
done

python3 - "$ROOT" <<'PY'
from pathlib import Path
import re
import sys
root=Path(sys.argv[1])
# Bundled prose remains the English default. AGENTS explicitly permits localized
# diagnostics, necessary comments, and real Unicode behavior fixtures in code.
errors=[]
for path in (root/'.agents/skills').rglob('*.md'):
    body=path.read_text(encoding='utf-8')
    if re.search('[\u4e00-\u9fff]',body):
        errors.append(f'English bundled prose contains Han text: {path.relative_to(root)}')
for path in (root/'.agents/skills').rglob('*.py'):
    body=path.read_text(encoding='utf-8')
    compile(body,str(path),'exec')
    mirror=root/'.agents-zh'/path.relative_to(root/'.agents')
    if mirror.exists() and mirror.read_bytes()!=path.read_bytes():
        errors.append(f'Nonlocalized script mirror drift: {path.relative_to(root)}')
if errors:
    print('\n'.join(errors),file=sys.stderr)
    raise SystemExit(1)
PY

printf '%s\n' 'PASS: English bundled prose, UTF-8 scripts, and nonlocalized mirrors are consistent.'
