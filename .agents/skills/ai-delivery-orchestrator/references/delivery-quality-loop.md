# Context and quality loop

Apply [Trellis](https://docs.trytrellis.app/zh) source selection and
[Shopify Helix](https://shopify.engineering/helix) bounded feedback inside the
existing kit contract, router, checkpoints, and UI truth boundaries. Do not
start an upstream Task/checkpoint/journal/Stop hook or add human gates.

## Start and recover

At batch start, resume, stage/scope change, and review, generate context for
the actual requirement directory and explicit slice:

```sh
ai-delivery context --project . --req <req-id> --subreq SR-001 \
  --role implement --changed-path src/owner.go --format json
```

Roles: `analysis`, `design`, `ui`, `implement`, `review`, `recovery`, `finish`.
Stage ownership and UI modes remain unchanged. `context_complete` means required context
was provided completely without detected input errors; it grants no authority.
Use current explicit-scope `check`, design review, and checkpoint evidence for permission.
The CLI does not emit the former queue or global slice-selection authorization.

Repeat `--changed-path` for declared owned scope. Git discovery reports staged,
unstaged, new, deleted, and both sides of renamed paths; `unassigned_paths`
does not assign other people's dirty work to this task. With no declaration,
observed paths are reading candidates only. Declared and observed paths always
both participate in rule selection; declaration never hides actual changes.
Directory declarations include their own AGENTS and matching source rules.
Review independently rechecks actual
changes and the original domain/owner; path matching never proves completeness.

Entries are `provided`, `needs_read`, or `missing`, with source, reason, kind,
and byte hash. Read missing full text directly when over budget; an index or
truncated injection is not full provision. Never remove a required source just
to make `context_complete` true. Every call reads current bytes, not mtime/session authority.
The explicit entry works without hooks or an installed Trellis.

Required sources follow applicability and existing references, even when their
files disappear. Active design stages require the original requirement and
canonical design; referenced slices remain required when missing. Draft intake
and genuinely unsplit requirements retain their applicability exceptions.
Explicit source configuration takes precedence over automatic index hints.

## Project sources

Policy v4 `context.sources` references a single existing body:

```json
{"context":{"sources":[
  {"path":"docs/architecture.md","paths":["src/**"],"roles":["implement","review"],"kind":"standard","required":true,"writable":false},
  {"path":"docs/knowledge/owner.md","paths":["src/**"],"kind":"knowledge","required":true,"writable":false}
]}}
```

Omitted paths/roles match all; paths use case-sensitive `fnmatch` on repository
POSIX paths. Without known paths, analysis/design conservatively includes
registered sources. Only repository-relative paths are allowed; reject `..`
and external symlinks. Root/module AGENTS and user authority cannot be replaced
by ordinary source specificity or budgets. No extra sources is a valid setup.

Kinds are `standard`, `knowledge`, `advice`; required knowledge still describes
observations rather than granting normative authority. `writable` defaults false
and only declares maintenance scope, never product/permission/truth changes or
waiver rights. Existing `.trellis/spec/`, `docs/knowledge/`, `docs/harness/`
leaves may be registered directly. Indexes aid discovery, not upstream workflow
execution. Do not generate empty trees or overwrite competing user automation.

## Bounded feedback

A coherent batch follows observable behavior or an actual state owner with
complete wiring and applicable tests. Prove uncertain architecture, concurrency,
permission, and persistence boundaries early, then expand. File count does not
mandate agents or reviewer gates. The same implementer fixes findings; fresh
review checks original requirements/omissions and standards/architecture in one
pass. Add a specialist only for a distinct evidenced risk.

Run the cheapest native check that actually proves behavior before applicable
integration, visual, and runtime checks. Reuse the production owner and existing
test facilities; do not create duplicate CLI business logic to fit tests. Keep
the required final check scope, rerunning only missing or invalidated evidence.

| result | Meaning and response |
|---|---|
| `passed` | Current inputs and actual raw results; coverage/semantics still need review |
| `failed` | Valid check found a defect; fix implementation/wiring and reverify |
| `invalid` | Wrong capture state/scope or stale input; repair evidence first |
| `not_run` / `blocked` | Unexecuted or unavailable prerequisite; retain the gap |
| `not_applicable` | Sourced scope decision; cannot cover a required AC |
| `waived` | Explicit scoped user authority under existing rules, never self-granted |

UI comparisons bind existing profile/state/scenario, evidence_scope, and host
binding. Match states and regions. Component-only evidence cannot prove a host;
static images cannot accept interaction/motion. Retain same-stack deterministic
goldens rather than generalizing cross-stack pixel-diff limitations.

Findings need location, source, and disposition. Hard defects cannot become
advisories, preferences cannot become mandatory repairs, and false findings may
be rejected with evidence. Never lower expectations/thresholds/standards to fit
current output. Real truth/requirement conflicts use existing design decisions.
Keep `review_loop.max_rounds` (default 3); a new agent/batch name cannot reset it.
On no progress seek discriminating evidence; at budget exhaustion preserve
failures and recovery directions. Normal stop/cancel never marks a gate passed.

## Verification v2

New init seeds policy v4 and `verification_contract_version: 2`. Ordinary upgrade
checks current binding/policy before refreshing managed assets and preserves
compatible metadata. Unsupported data stops dependent operations. Choose either
your own AI/manual migration after backup, or explicit backup-and-reset with
`ai-delivery init --upgrade --reset-data /path/to/repo`. Neither runs automatically.
See [current protocol and upgrade choices](version-upgrade.md) for the copyable
migration prompt, current formats and backup/recovery boundaries.

Keep the sole `verification.md`, its three existing markers, chronological
review rounds, and sign-off. Add exactly one JSON fenced block between
`<!-- ai-delivery-verification:contract:v2 -->` and
`<!-- /ai-delivery-verification:contract:v2 -->`.

The object has `version:2`, `subreq_id`, `inputs`, `checks`, `reviews`. Inputs
contain actual `{path,sha256}` entries for design and related production, test,
resource, dependency, and guideline inputs. Deleted inputs use
`{path,sha256:null,state:absent}` and must remain absent. Do not bind changing
status or verification itself. Compute real bytes and the review input digest:

```sh
ai-delivery evidence fingerprint --project . \
  --input src/owner.go --input tests/owner_test.go \
  --input .ai-delivery/requirements/<req-id>/sub-requirements/SR-001/design.md
```

Each check needs `id`, `acceptance_ids`, `required`, `result`; passed checks also
need `mode` (`executed`/`reused`/`manual`), actual `command`, execution exit code,
and nonempty native evidence `{path,sha256}`. Reuse needs `reuse_reason` after
checking tests, dependencies, toolchain, and runtime preconditions. Manual
verification needs `confirmation`, waivers need `waiver`, each with
`by/at/reason/source_ref`. These are authority records, not authenticated proof
of arbitrary human identity. All ACs need passed or validly waived evidence.

Reviews preserve rounds; the last item covers the current full scope with the
actually visible `reviewer`, `context:fresh`, `result:clean`, `input_sha256`,
`verification_sha256`, and `findings`. The latter digest binds the complete
`version/subreq_id/inputs/checks` object, including commands, results, coverage,
evidence, reuse reasons, and authority records. Reviews themselves are excluded
to avoid self-reference. Compute both digests after finalizing the claims and
have the independent reviewer bind the actual reviewed version:

```sh
ai-delivery evidence review-digest --project . --file <verification-path>
```

This command only computes content identity; it never creates a review or
grants acceptance. Changing claims requires another applicable review.
Findings carry `id/source_ref/disposition`
(`resolved`/`rejected`/`advisory`/`waived`). Open findings cannot coexist with
clean acceptance. Do not invent independent agent identity. Hashes detect drift,
not an incomplete input list: independent original-source review remains vital.

### Optional native execution capture

When a native check has a precise command and known inputs, `ai-delivery run`
can capture its real streams, exit facts and receipt. Register the method in
the canonical `design.md` acceptance section before its applicable design
review. This is optional: omit the entire block when not choosing this runner;
do not insert an empty or placeholder block. Existing external executed/reused
evidence and legitimate manual verification remain available without a native
block, under the same evidence, reuse and confirmation requirements above.

The exact block has `version: 1` and nonempty `checks`. Each check has only
`id`, `acceptance_ids`, `argv`, `cwd`, `parser_id`, `input_paths`, `report_paths`
and `source_refs`. IDs must be unique and cannot occupy core check names.
AC IDs must exist in this design. `argv` is a nonempty string array, not shell
text; `cwd` is a normalized project-relative directory (`.` is valid).
`parser_id` is `exit-code` or `go-test-json`; the latter requires actual
successful test events. `input_paths` and `source_refs` are nonempty arrays
of actual project-relative files, not directories, globs, URLs or `#L` locations.
`report_paths` is always an array, including `[]` when no extra report is
produced. Extra reports must be newly produced within `{run_dir}/...`.

For example, a Go products API with these actual files and AC-001 through
AC-004 covering filtering, invalid parameters and unchanged Store behavior
can register this in its existing acceptance section, before traceability:

````markdown
<!-- ai-delivery:native-methods:v1 -->
```json
{
  "version": 1,
  "checks": [{
    "id": "go-products",
    "acceptance_ids": ["AC-001", "AC-002", "AC-003", "AC-004"],
    "argv": ["go", "test", "-json", "-count=1", "./..."],
    "cwd": ".",
    "parser_id": "go-test-json",
    "input_paths": [
      "go.mod", "api/router.go", "api/handler.go", "api/store.go",
      "api/legacy_test.go", "api/acceptance_test.go", "cmd/server/main.go",
      "notes/preserve.txt"
    ],
    "report_paths": [],
    "source_refs": [
      ".ai-delivery/requirements/F01-D1/sub-requirements/SR-001/requirement-slice.md"
    ]
  }]
}
```
<!-- /ai-delivery:native-methods:v1 -->
````

Use your actual scope, ACs, files and confirmed toolchain; do not invent a
`go.sum` when none exists. If a missing lockfile affects execution, declare
its absence with `--input go.sum`, rather than listing a missing file among
registered `input_paths`. Add relevant inputs not covered by the registration
using repeated `--input`; this mechanism does not discover all host dependencies,
environment, toolchain or device conditions. Keep their applicable evidence.

After the current design bytes have their applicable review and the current
stage permits execution, run from the host root:

```sh
ai-delivery run --project . --req F01-D1 --subreq SR-001 \
  --check go-products --cwd . --timeout 120 --format json \
  -- go test -json -count=1 ./...
```

This runs the full package pattern. The `go-test-json` parser requires at least
one actual test with `run` followed by `pass`, and every started test must pass.
A normally completed package with no test files may end in package-level
`skip`; it contributes no successful test. Actual test skips (including
`t.Skip`) and a command with no actual tests remain `invalid`, even with exit
zero. Package execution does not expand the registered AC coverage or replace
other required evidence.

The argv after `--` and `--cwd` must exactly match the reviewed method. An
absolute Go path is also possible if both places use that exact path. Do not
install/downgrade tools or fetch dependencies merely to fit this example.
Method changes alter design bytes and require the applicable review again.
`run --help` describes current flags; no `--parser` or receipt converter exists.

Consume the returned JSON as follows:

1. Preserve `receipt_path`, its original stdout/stderr and reports, including
   failed/not-run attempts. For `result: passed` with no mapping diagnostics,
   use the returned `check` as that ID's real verification v2 `checks` entry.
   Preserve other results as reported; exit zero alone is not enough.
2. Use returned `inputs` as the execution-input basis. Merge the scope's other
   actual design, production, test, dependency and standard inputs by path with
   their current hashes; resolve conflicting identities instead of overwriting
   them. Do not copy the receipt's entire `inputs_before` (it also contains
   prerequisites). Exclude verification itself and changing status bookkeeping;
   if a test explicitly consumes status, that file is an execution input too.
3. Update the sole verification v2 object (`version: 2`, `subreq_id: SR-001`,
   `inputs`, `checks`, `reviews`) in `verification.md`. Preserve existing rounds
   and record only actual review outcomes. A Go check for AC-001–AC-004 cannot
   claim AC-005's separate structure/draft-integrity checks or a fresh review.
   `run` does not write verification, grant confirmation/waiver, merge or archive.
4. After composing the claims, compute their actual review identities:

   ```sh
   ai-delivery evidence review-digest --project . --file .ai-delivery/requirements/F01-D1/sub-requirements/SR-001/verification.md
   ```

   Give `input_sha256` and `verification_sha256` to the independent reviewer
   for the version actually reviewed. This command accepts verification, not a
   receipt; it does not create a review. Ordinary `check`/`advance` still apply.

Once a native method is registered, its executed/reused checks require the
real receipt. Dropping `receipt_path` or changing check IDs to ordinary external
claims cannot bypass that obligation. Legitimate manual evidence and explicit
waivers retain their existing authority requirements; silently removing a
method cannot replace a reviewed design change. For external evidence,
`evidence fingerprint` computes current explicit file/absence identities only;
an after-the-fact hash does not establish historical execution.

## Current evidence and archived history

Current conversion and evidence reuse require current inputs, reports and
applicable approvals. Only the canonical behavior contract's acceptance section
defines required ACs; historical mentions elsewhere do not add obligations.
The shared validator reports the files it actually consumed, including UI
transitive references and resolved target identity. Archive rechecks that same
set before output replacement; it does not ask AI to duplicate the list.

New archive operations store `archive_evidence` inside the existing status entry,
binding the final entry and original design, verification and applicable UI
contracts. Historical reads check that identity, allowing production sources and
native logs to evolve without rewriting the old task. Changed historical
contracts still fail. Reusing an old result in a new task requires that new task
to validate its current inputs; historical integrity alone never proves reuse.
An archived record without this identity is unsupported. Do not reconstruct
historical approval from current bytes or lower verification to markers alone;
use the upgrade choices above.

## Release and effect evaluation

Implementation completion and default adoption are separate decisions. Before
expanding a candidate, verify consumer agreement, interrupted explicit reset recovery,
unsupported-format diagnostics, installed execution, and consecutive slices that
legitimately change the same owner. Preserve current acceptance strength for
existing v4 hosts. Optional guidance can be disabled without weakening gates.

Measure additional context and review guidance against a safe baseline that
already includes reliability fixes. Freeze task inputs, model, permissions,
budget and acceptance; retain all attempts and failures. Report quality and
actual tool/model cost separately. Character counts, passing structural tests,
or fewer subprocesses do not demonstrate model accuracy or development speed.

## Maintain and evaluate

Collect problems in the sole retrospective; source successful patterns in
design/decisions without invented RETs. Verify stable knowledge and normative
authority, then maintain its single registered writable source. Code alone
proves current behavior, not a permanent rule. Normative promotion needs an
accepted architecture or an explicit decision by the user or a maintainer with documented authority for that scope. Independent review supplies evidence, not self-granted maintenance authority. Keep a proposed rule separate from an accepted standard: record the actual proposal/source, authorized actor, decision, scope, and current source identity in existing decisions/retrospective artifacts before changing the registered standard. `writable` alone is not acceptance; never invent human approval or promote your own suggestion automatically.
Update corresponding checks and source selection without retroactive approval.

Only when no suitable source exists, create a needed `.ai-delivery/standards/`
topic and register it. No success ledger or writeback to read-only imports.
Product/permission/truth changes keep existing gates. A later task in fresh context must apply the current accepted rule in its real production owner and native behavior; source selection or index hits alone do not establish adoption. Prefer an existing module AGENTS or other registered standard instead of a new learning database.

When a current authorized contract supersedes a rule, obtain the scoped maintainer decision under existing authority, update the current standard, and refresh context before implementation. Record withdrawal and its source in the current task; retain the original proposal, acceptance, and archived retrospective/index history. Historical advice cannot override the current contract. Confirm that the old rule actually covered the owner before withdrawal; moving code outside its scope proves nothing. Candidate-only cross-task chains show observed application/withdrawal, not causal speedup or generalized learning benefit.

Evaluate kit changes using fixed versions, initial files, scenarios, acceptance,
and budgets. Preserve every run, failure, blocker, and incomparable case. Mock
scores/keyword hits are not measured model reliability. Track omissions and
false acceptance alongside false blocking, spurious findings, interruptions,
and rework. Reject faster but lower-quality outcomes; remove process overhead
that delivers no demonstrated benefit.

## Single-program query scope

`ai-delivery validate --kind status --project . --req <req-id> --subreq <subreq-id>` checks current status fields, UI mode, and forbidden artifacts only; success does not prove stage or delivery readiness. `validate --kind layout --project .` checks project layout configuration only (`scope: project-layout-configuration`). A scoped layout query must supply `--intent`; `--to` always requires `--intent`.

For complete scoped evidence and transition validation, use `check`, or the exact thin alias `validate --kind layout --project . --req <req-id> --subreq <subreq-id> --intent <intent> --to <target-status>`. The alias calls the same core and returns the same action report. `validate --kind skills|sources|api-policy` checks managed human-readable resources and takes no action/slice arguments. `hook` without `--host` uses the same arguments and JSON as `check`; optional [native transport](native-hooks.md) projects Codex SessionStart/PreToolUse stdin and output in the same program. It never executes a second kit program.
