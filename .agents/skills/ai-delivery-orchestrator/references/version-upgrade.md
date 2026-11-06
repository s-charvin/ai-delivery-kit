# Current protocol and upgrade choices

ai-delivery-kit reads only its current delivery protocol. Unsupported formats stop the operation that consumes them. Ordinary `init --upgrade` checks existing metadata before refreshing managed assets; it does not migrate or reset business data and does not certify every requirement. Malformed current data, missing evidence, failed checks and missing approvals remain specific errors, not proof of an old format.

| Artifact | Required current format |
| --- | --- |
| `meta/project-binding.json` | `version: 3` |
| `meta/workflow-policy.json` | `version: 4`, `verification_contract_version: 2` |
| Requirement `status.json` | `_schema: "2.0"` |
| Applicable `verification.md` | verification contract `version: 2` |
| Applicable `contracts/ui-truth-index.json` | `schema_version: 3` |
| Applicable `visual-acceptance.json` | `schema_version: 2` |
| Archived entry | `archive_evidence.version: 1`, retaining current contract identities |

A new requirement may still be in intake without status. Drafts do not need final verification evidence. Custom current layouts and `context.sources` remain supported. Old or future versions, missing required format declarations, removed bypass fields and checkpoints are rejected. Changing a version number alone does not make data valid.

## Choose either option

**A. Migrate the data you want to continue using.** Back up first, then give the prompt below and the exact error output to your own AI, or perform the migration manually. No model, provider, IDE or AI API is required. The kit does not execute migration or track a migration session.

**B. Back up old data and start a new delivery workspace.** Explicitly run:

```sh
ai-delivery init --upgrade --reset-data /absolute/project/path
```

For an existing custom delivery root, explicitly select its project-relative path:

```sh
ai-delivery init --upgrade --reset-data=tooling/delivery /absolute/project/path
```

The custom root must have an unambiguous project-local metadata boundary. Reset refuses a conflicting existing standard `.ai-delivery` root. A stable project-root `.ai-delivery.lock` serializes reset and archive even when the old root moves. Reset uses the same native project lock as delivery actions; platform support is verified by native CI, not inferred from cross-compilation.

Quote a project path containing spaces. The command preserves the old files in a unique project-local `.ai-delivery-backups/` directory outside the active delivery root, reports its absolute location and initializes current managed delivery assets. Old tasks are not inherited, migrated or required to pass current validation. No AI is called. This never runs automatically after an upgrade failure. If initialization fails after a complete backup, retain that backup and use the reported recovery path and affected scope; the failed command is not a successful reset. Never overwrite an earlier backup. Backup manifests serve file recovery only and are not acceptance evidence.

The two options are equal choices; no ordinary command selects one for you. Retry the original command after your chosen action. Current validators and approvals still apply; neither a backup nor an AI claim of migration waives them. Old files retained in backups do not participate in current task discovery. Explicit asset refresh removes only old entrypoints matching the frozen ownership path/hash list. Modified old files stop the refresh before writes so you can preserve them and resolve the conflict. Do not delete unrelated skills or third-party configuration.

`--upgrade-policy` and `--verify-archive` have been removed. There is no compatibility switch, migration receipt, migration source hash or backup registration required for normal operation. Archived history without a valid current identity must not gain fabricated historical approval from today's bytes.

## Copyable migration prompt

```text
Please help me resolve this project's ai-delivery-kit data upgrade problem.

Use the attached error output for the project, conflicting files, actual formats,
required formats and current specification location. The goal is to make data
that I want to keep using conform to the kit's sole current delivery protocol.
Use your own investigation and tools; no specific AI service or migration command
is required.

First read the project instructions and the current templates, validators and
artifact specifications. Before editing, fully back up old delivery data and all
configuration/files you intend to change outside the active governance directory.
Tell me the absolute backup path and its scope. Preserve original bytes, names and
link relationships; never overwrite an earlier backup. Keep backups outside the
current task discovery scope.

For continuing tasks, preserve original requirements, user input, sources and
confirmed product decisions. Organize design, status, dependencies, verification
and applicable UI contracts in the current format. If existing evidence or
approval cannot support the current stage, state the gaps and return to an
evidence-supported stage or blocked state. Never fabricate executed tests, human
approval, independent review or a new archived identity. Editing an approved
file invalidates its old hash; ask me only when a new decision is actually needed.

Completed records may stay only if they already fully conform to the current
protocol; otherwise retain them in the backup for reference. Do not add old
version parsers, bypass fields or fake acceptance to keep them active. Before
moving old entries out of a mixed requirement, resolve active dependencies and
references; do not manufacture completion by deleting dependencies. Treat reused
historical facts as sourced context, and prove present usability in current tasks.

Do not modify product code, delete third-party configuration, commit or push as
an incidental part of migration. Explain the scope first if product fixes are
actually required.

Finally run current validators and routing checks on affected tasks. Explain
which data is active, which remains backup-only, which evidence is missing, the
actual verification results and next steps. A backup or changed version number
alone does not mean migration succeeded.
```

## Current nested roots

Automatic project-root discovery is bounded to the standard root or one immediate custom directory. To refresh an existing current root nested more deeply, pass that root explicitly: `ai-delivery init --upgrade /project/tooling/delivery`. This validates existing metadata in place; it does not scan project history or create a second delivery root. The same explicit path works with `ai-delivery ide-gates list /project/tooling/delivery` and `ai-delivery ide-gates restore --to <timestamp> /project/tooling/delivery`. For backup/reset, pass the project path and the explicit relative `--reset-data=tooling/delivery` source.

## Current program and resources

Download the selected release’s single `ai-delivery` program. Daily kit operation needs no Go SDK, Python, Node, or zsh. Install declared native host tools separately. `ai-delivery info --project <path>` reports the absolute program path, release/revision, and protocol/resources digests. Missing or mismatched `meta/kit-assets.json` requires explicit `init --upgrade` to refresh resources, not a business-data reset. Updating the program does not refresh projects automatically.

Timestamp fields require RFC3339Nano with a timezone, for example `2026-11-05T12:00:00+08:00`. Space-separated permissive legacy forms are not accepted, and approval times are not normalized automatically. Read current templates with `ai-delivery info --resource kit://ai-delivery-orchestrator/templates/verification-template.md`. `evidence review-digest` returns both `input_sha256` and `verification_sha256`; these identify declared contract content and do not prove execution, review, or approval.

The retrospective `reviewed-at` marker also accepts a valid `YYYY-MM-DD` calendar date. If it contains a time, the same strict timezone-bearing RFC3339Nano rule applies. Previously permissive naive times, single-digit hours, comma fractions, and `+24:00` offsets now require you to resolve and normalize the intended value yourself, or choose the explicit backup/rebuild option. The tool does not infer a timezone or rewrite the original marker.
