#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
TMP_WORK=$(mktemp -d "${TMPDIR:-/tmp}/ai-delivery-reset.XXXXXX")
trap 'rm -rf "$TMP_WORK"' EXIT
GOMODCACHE="$TMP_WORK/mod-cache" go build -o "$TMP_WORK/ai-delivery" "$ROOT/cmd/ai-delivery"
python3 - "$TMP_WORK" <<'PY'
import hashlib,json,os,subprocess,sys
from pathlib import Path
work=Path(sys.argv[1]);cli=work/'ai-delivery'
root=work/'repo 空格';root.mkdir()
subprocess.run(['git','init','-q',str(root)],check=True)
def run(*args,ok=True):
    result=subprocess.run([str(cli),*args,str(root)],capture_output=True,text=True)
    assert (result.returncode==0)==ok,(args,result.stdout,result.stderr)
    return result
run('init')
policy=root/'.ai-delivery/meta/workflow-policy.json'
policy.write_bytes(b'{"version":3,"original":"\xff"}')
old_helper=root/'.agents/skills/ai-delivery-orchestrator/scripts/legacy_terminal.py'
old_helper.write_text('raise RuntimeError("old helper must not run")')
third=root/'.agents/skills/third-party/SKILL.md';third.parent.mkdir();third.write_bytes(b'third-party bytes')
product=root/'product.go';product.write_bytes(b'product bytes')
requirement=root/'.ai-delivery/requirements/old/requirement.md';requirement.parent.mkdir(parents=True);requirement.write_bytes(b'original requirement\x00\xff')
def snapshot():
    return {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest()
            for parent in [root/'.ai-delivery',root/'.agents'] for p in parent.rglob('*') if p.is_file()}
before=snapshot()
failed=run('init','--upgrade',ok=False)
assert str(policy) in failed.stderr and '--reset-data' in failed.stderr
assert before==snapshot(),'ordinary failed upgrade wrote data/assets'
assert 'Upgraded' not in failed.stdout
# Users must be able to obtain full current instructions before upgrading old assets.
guide=root/'.agents/skills/ai-delivery-orchestrator/references/version-upgrade.md';guide.unlink()
failed=run('init','--upgrade',ok=False)
assert 'Copyable migration prompt' in failed.stderr,failed.stderr
assert not guide.exists(),'displaying instructions mutated old host'
result=run('init','--upgrade','--reset-data')
assert '备份重建完成' in result.stdout,result.stdout
assert json.loads(policy.read_text())['version']==4
assert not requirement.exists() and not old_helper.exists()
backups=list((root/'.ai-delivery-backups').iterdir());assert len(backups)==1
backup=backups[0];manifest=json.loads((backup/'manifest.json').read_text())
assert (backup/'files/.ai-delivery/meta/workflow-policy.json').read_bytes()==b'{"version":3,"original":"\xff"}'
assert (backup/'files/.ai-delivery/requirements/old/requirement.md').read_bytes()==b'original requirement\x00\xff'
assert (backup/'original-data/requirements/old/requirement.md').is_file()
assert third.read_bytes()==b'third-party bytes' and product.read_bytes()==b'product bytes'
assert any(x['type']=='file' and x.get('sha256') for x in manifest['entries'])
run('init','--upgrade')
# A current metadata upgrade does not certify an old requirement. Installed readers reject it.
status=root/'.ai-delivery/requirements/old/status.json';status.parent.mkdir(parents=True,exist_ok=True)
status.write_text('{"_schema":"1.0","sub_requirements":{}}')
result=subprocess.run(['python3',str(root/'.ai-delivery/scripts/validate-delivery-status.py'),str(status)],capture_output=True,text=True)
assert result.returncode!=0,(result.stdout,result.stderr)
assert '--reset-data' in result.stdout+result.stderr,(result.stdout,result.stderr)
# Users may complete their own migration; no migration receipt is needed for ordinary refresh.
status.unlink()
run('init','--upgrade')
# An explicitly supplied nested current root is sufficient; no recursive root scanner is needed.
nested=root/'tooling/delivery';nested.parent.mkdir()
(root/'.ai-delivery').rename(nested)
binding=nested/'meta/project-binding.json';data=json.loads(binding.read_text());data['ai_delivery_path']='tooling/delivery';binding.write_text(json.dumps(data))
result=subprocess.run([str(cli),'init','--upgrade',str(nested)],capture_output=True,text=True)
assert result.returncode==0,(result.stdout,result.stderr)
assert not (root/'.ai-delivery').exists(),'explicit nested upgrade created a shadow root'
assert (nested/'scripts/validate-delivery-status.py').is_file()
hooks=root/'.cursor/hooks.json'
original_hooks=b'{"hooks":{"PostToolUse":[{"hooks":[{"type":"command","command":"validate-ui-contract.sh"}]}]}}'
hooks.write_bytes(original_hooks)
result=subprocess.run([str(cli),'init','--upgrade',str(nested)],capture_output=True,text=True)
assert result.returncode==0,(result.stdout,result.stderr)
result=subprocess.run([str(cli),'ide-gates','list',str(nested)],capture_output=True,text=True)
assert result.returncode==0 and 'No IDE' not in result.stdout,(result.stdout,result.stderr)
stamp=result.stdout.strip().splitlines()[0]
result=subprocess.run([str(cli),'ide-gates','restore','--to',stamp,str(nested)],capture_output=True,text=True)
assert result.returncode==0 and hooks.read_bytes()==original_hooks,(result.stdout,result.stderr)
assert not (root/'.ai-delivery').exists(),'nested IDE restore created a shadow root'
old_policy=nested/'meta/workflow-policy.json';old_policy.write_text('{"version":3}')
result=subprocess.run([str(cli),'init','--upgrade',str(nested)],capture_output=True,text=True)
assert result.returncode!=0 and str(old_policy) in result.stderr and '--reset-data=tooling/delivery' in result.stderr,(result.stdout,result.stderr)
print('PASS: real CLI rejects before writing, emits embedded prompt, resets with complete backup, preserves third-party files, and installed current readers reject old status.')
PY
