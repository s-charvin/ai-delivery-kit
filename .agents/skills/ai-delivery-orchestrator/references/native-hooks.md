# Optional native hooks

The explicit `ai-delivery context`, `check`, `run`, `advance`, and `archive`
workflow remains complete without hooks. Skills and external frameworks supply
methods; the installed CLI evaluates current protocol, applicability, evidence,
and actions. A hook is a transport, not another permission engine or task store.

## Scope and support

`hook` without `--host` remains the same-process `check` alias with kit JSON.
`hook --host codex --event SessionStart|PreToolUse` reads one native JSON object
from stdin. Provide an absolute `--project`; `cwd` must resolve inside it,
including subdirectories. No Git requirement is added. Provide both `--req` and
`--subreq`, then `--role` for SessionStart or `--intent`/optional `--to` for
PreToolUse. Never infer these from command text, session IDs, transcripts, or a
recent task. Partial scope is an error. With neither scope ID, the adapter emits
only a bounded explicit-CLI reminder and performs no check.

SessionStart calls the existing context entry in the same process. Optional
`--path` may repeat; `--budget-chars` defaults to 4000 (0..64000). Required
sources marked `needs_read` or `missing` still require attention. Context
completeness is not permission. PreToolUse calls the same scoped check service;
a passing result never outputs `permissionDecision:allow` or rewrites the tool.
Use a narrow, explicitly chosen write-tool matcher; do not gate every shell
command and accidentally block reading the material needed to resolve a gate.
The adapter does not parse a shell command or patch to assign task ownership.

Input is limited to 1 MiB. Duplicate keys (including nested keys), trailing
JSON, invalid encoding/types, mismatched events, unsupported events/hosts, and
out-of-project cwd fail with exit 2 plus stderr. Unknown extension keys are
accepted. `transcript_path` may be absent, null, or a string; other types are rejected. The adapter never reads that transcript. A core decision denying the scoped action produces exit 0 with
native `permissionDecision:deny` and its diagnostic reason. Core errors such as
resource drift use exit 2 plus stderr, including the recovery direction.
SessionStart reports incomplete context without manufacturing permission;
input/core errors use exit 2. No Stop event, continuation loop, permission
override, task tree, journal, or model API is introduced.

Output text is limited to 12000 Unicode characters. Truncation is labeled and
requires the explicit CLI for complete sources/diagnostics. Codex can also spill
additional context; injection alone does not prove full reading or application.

## Reviewable opt-in example

Default installation adds no kit command hook and does not create, enable,
disable, or rewrite `.codex/config.toml`. Existing `features.hooks` true/false
and third-party definitions remain the user's choices. The three optional host
JSON files are neither installed nor required by the kit resource manifest:
`.codex/hooks.json`, `.claude/settings.json`, and `.cursor/hooks.json` may be
absent or omit `hooks`. Existing files remain byte-for-byte unchanged on
init, upgrade, and reset; this also preserves large integers and formatting.
Users create or edit their own opt-in definitions. The kit does not parse,
re-encode, migrate, or remove them; any remaining old hook must be reviewed by
its owner. Explicit historical backup restore still preserves original bytes.
Current managed skills, AGENTS sections, and business contracts keep their
identity checks. Refresh an earlier kit resource manifest through explicit
`init --upgrade`, not by bypassing its identity.

Only after choosing the exact project/slice/action, merge a reviewed definition
into the user's existing project hooks configuration. Replace the absolute
paths and scope below; quote paths for the actual platform shell. This example
uses a POSIX command. Windows command/quoting must follow the host's documented
`commandWindows` mechanism and needs its own runtime verification.

```json
{
  "hooks": {
    "SessionStart": [{"hooks": [{
      "type": "command",
      "command": "\"/absolute/path/ai-delivery\" hook --host codex --event SessionStart --project \"/absolute/project\" --req R --subreq SR-001 --role implement --path src --budget-chars 4000",
      "additionalContextLimit": 4000
    }]}],
    "PreToolUse": [{"matcher": "apply_patch", "hooks": [{
      "type": "command",
      "command": "\"/absolute/path/ai-delivery\" hook --host codex --event PreToolUse --project \"/absolute/project\" --req R --subreq SR-001 --intent implement --to in_dev"
    }]}]
  }
}
```

This fixed scope is not suitable for unrelated tasks: update or disable the
definition when scope changes. Do not overwrite other hooks, set global trust,
or approve the host's hash review on the user's behalf. Non-managed hooks and
project sources require the host's own trust flow; changed definitions require
review again. CLI `/hooks` or desktop Review hooks handles that choice.

## Evidence boundary

The transport follows official Codex command-hook documentation retrieved on
2026-11-05: [hooks](https://learn.chatgpt.com/docs/hooks) and
[configuration](https://learn.chatgpt.com/docs/config-file/config-reference).
Native protocol fixtures and real binary stdin/stdout/exit tests do not prove
local Codex enablement, trust, connectivity, or callbacks. Those host behaviors
remain unverified here; no specific installed host version is certified.
Unsupported host releases should use the explicit CLI. Claude and Cursor native
transports are not implemented. Host callback errors, timeouts, or malformed responses can
continue tools in some paths, so hooks are guardrails rather than an exhaustive
execution boundary. Final explicit action checks remain required.
