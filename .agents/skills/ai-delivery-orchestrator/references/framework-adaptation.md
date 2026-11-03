# Framework Adaptation

The orchestrator owns state, gates, blockers, handoffs, and persisted artifact
shape. Installed frameworks contribute reasoning or execution discipline; they
do not add workflow stages or required documents.

## Artifact containment protocol (required)

- Formal process artifacts use canonical paths resolved from
  `.ai-delivery/meta/project-binding.json`. Auxiliary materials stay under their
  owning requirement as described below; no binding key is needed for each kind.
  The sole Stage 3 contract is `design.md`; optional recovery uses `progress.md`.
- Outside `.ai-delivery/`, writes are limited to production source,
  project-native tests, goldens/official previews, and runtime assets.
- Before invoking an external skill, command, agent, or hook, pass the exact
  canonical output map and approved workspace. Defaults such as
  `docs/superpowers/**`, `.superpowers/**`, `.specify/**`, and `openspec/**` are
  disabled.
- If a step cannot honor the map, do not run its persistence phase. Apply the
  useful method in-session and write the canonical artifact directly. Never
  create an external process artifact and move it afterward.
- Fingerprint Git-visible changes and every external default output root at coherent batch entry/exit and before a gate advances, including ignored files, types, symlink targets, and SHA-256 values. A single audit may cover controlled calls within the same batch only when it accounts for every writer and output root; keep output maps enforced throughout. Unknown writers, changed roots or uncertain coverage require a separate full audit. Never reuse by mtime or tracked paths alone. Any new or changed process artifact outside `.ai-delivery/` opens `blocked_verification_failure`; do not delete or rewrite user files.

Existing framework trees are read-only inputs during orchestrated work.

## Lightweight artifact organization

Formal paths still resolve through `project-binding.json` and `layout.py`.
Auxiliary material is allowed under the owning requirement without adding every
file kind to that binding. These conventions guide new writes, not directory
validation, file-count limits, new manifests, naming gates, or a cleanup phase.

Choose the role before writing. Update the existing owner when it can carry the
information; split only for an independent source, review scope, run, or attempt
that needs preservation. A small task needs no empty folders or extra reports.

| Role | Maintenance and boundary |
|---|---|
| Retrospective, design contract, current interpretation/manual checklist | Integrate one authoritative body. Preserve original requirements separately. No supplemental retrospective/design patch or competing latest checklist. |
| Status and progress | `status.json` owns state; progress is a short current summary with links, not repeated logs or a second status table. |
| User inputs, decisions, review and verification rounds | Preserve original order and supersession in their respective records. Review rounds may append in `verification.md`; this is not patch-style retrospective. Do not copy the same round into several summaries. |
| Logs, captures, profiles, source exports, frozen evidence | Preserve original source version/run identity, including failures. Never overwrite old failures, merge independent runs, replace an original under an old confirmation, or pass off a new run as old evidence. |
| Research, coverage/numeric analysis, Mock, diff, failure snapshot | Generate only for a concrete question, source, scope or reproduction. Maintain the topical conclusion in place; keep necessary original observations by run. No empty reports, repeated exports without new information, or whole historical-directory copies. |
| AI handoff and human delivery material | Create only for actual handoff/readership; link authoritative requirements/state/design/evidence. No automatic author notes, duplicate result summaries, parallel effective requirements or completion state. |

Existing prohibitions remain: no competing `spec.md`/`plan.md`/`tasks.md`, external
framework governance output, parallel `ui-contract.html` paint truth, or archive
snapshot copies. These are purpose boundaries, not a global ban on filenames:
native manifests, test fixtures, user attachments and read-only history keep
their real role. Prohibiting redundant copies never permits dropping a problem,
user input, or necessary failure evidence. Never delete existing originals as
part of normalization.

### Default homes by purpose

Reuse existing equivalent folders and keep single-slice material close to that
slice; cross-slice material has one requirement-level owner and links elsewhere.
These are defaults, not a required tree or a schema:

| Material | Default home and discovery |
|---|---|
| User's verbatim inputs | Requirement `prompts/`; one ordered group file per independent task, as below. |
| SDK/API/platform/migration research | Requirement `research/<topic>/` when substantial; one small clearly named report can remain in its existing location. |
| Design structure/exports/source assets | Existing `design-evidence/<topic>/`. A source snapshot is not a production implementation. |
| Mock and fixtures | Existing native fixtures or `self-test-mocks/`. |
| Detailed review, diagnostic, diff, necessary failure preservation | Existing `reviews/<topic-or-batch>/` or equivalent. Simple findings belong directly in `verification.md`; split only when independently useful, and link there. |
| Logs/screenshots/device structure/profiles/official previews | Existing native report and indexed evidence roots. Preserve UI truth index paths/hashes and host acceptance rules; no mass copies into `.ai-delivery`. |
| Manual checklist and AI-written continuation/handoff | Update existing manual entry; optional `handoff/` for substantial material. User-sent continuation text still belongs verbatim in `prompts/`. |

`contracts/` holds existing contracts and their indexed material, not every draft
or diagnostic. Reuse a source export when content/source version is unchanged;
independent runs retain their own identity even when bytes match. Prefer links
to original runs/snapshots; copy only necessary material when the tool would
overwrite it or offline preservation is needed, noting its source. No new global
asset store, content-addressing service, hash inventory or dedup system.
Temporary calculation/conversion intermediates may use host-approved temporary
storage; long-lived conclusions cannot depend solely on `/tmp`.

### Names and sorting for new freely named material

| Role | Format and example |
|---|---|
| Topic document, prompt group, maintained analysis/checklist | `<sequence>_<type>-<topic>.<ext>`; `001_User-input-Implementation-chat-ui.md` |
| Time-distinguished review/diagnostic/capture batch | `<YYYY-MM-DD>_<daily-sequence>_<type>-<topic>.<ext>`; `2026-11-03_001_Review-group-bubbles.md` |

Localize type and topic into the user's language. Type explains the content
(user input, AI handoff, research, review, diagnostic, manual check, source export,
failure preservation); these are examples, not a controlled enum. Use `_` for
the sorting prefix and `-` between type/topic. Avoid bare numbers, `latest`,
`final`, `new`, or a long test method as the entire descriptive name.

Zero-pad month/day and sequences, default three digits (four from the start
when scale needs it). Undated sequences advance within their directory; dated
sequences within that directory and date. Use the next available number after
the existing maximum; don't overwrite, reuse, renumber or close gaps. Numbers
express order, never importance or completion. Follow host collaboration for
collisions; no global counter or registry. Dates express this report/run/capture,
not an inferred historical date. If unknown, use undated naming and disclose.
Maintained files keep their name through edits. Prompt groups default undated;
if deliberately dated, cross-day supplements still use the same file.

For many related files, a `2026-11-03_001_Group-bubble-review/` batch can contain
`001_Review.md`, `002_Coverage.json`; don't repeat the same date at every level.
A few files need no batch directory. Fixed protocol/skill filenames, including
`status.json`, `design.md`, `verification.md`, `retrospective.md`,
`contracts/ui-truth-index.json`, native `result.json`/`profile.json`, bound
previews/goldens, source hash names and user-specified attachment names keep
existing names. Use existing navigation or a controllable parent for ordering;
never make a prefixed duplicate. Source/tests follow host naming. Changing a
formal name would need binding/parser/consumer migration, outside this policy.

### Current entry and evidence availability

Update an existing progress/verification/delivery entry with a short current
conclusion, applicable originals, superseded evidence and remaining boundaries.
Link new detailed reports once; don't register every raw image/JSON or force a
README/manifest in each directory. Complex collections may use a short table in
an existing entry. Resolve relative links from the actual referring file.
Historical code paths/line numbers and superseded reports must be labeled as
historical. A manual checklist explains inspection; results reference actual
verification/user feedback, not an independent completion state.

At resume or handoff, check readability of key evidence being relied on, not all
historical links on every edit. For disposable `build/`/temporary outputs, note
actual location, retention and available durable original/copy through the host's
existing mechanism. If missing: "historical result recorded; original currently
unavailable", with the impact on this conclusion. Missing files do not prove a
historical test failed or never ran. Do not fabricate originals, erase failures,
or rerun devices without authority to fill a directory.

Apply conventions to new material and currently maintained entries. Existing
paths, frozen hashes, STOP evidence, user files and archived requirements retain
their meaning and read-only boundaries. No automatic moving, renaming, dedup or
deletion. A future cleanup needs specific objects, reference impact, reversible
scope and existing authorization. Old names or large file counts do not block
delivery.

## User input preservation

Every actual user input for the requirement is necessary source material: save
its **full original text before interpretation/actions**, including initial
instructions, in-flight supplements, corrections, choices, confirmations, scope
changes and continuation. No importance/reuse filter and no substitution by a
summary, requirement, decision or RET. Use
[the single prompt record template](../templates/user-prompt-record-template.md).

Resolve the owning requirement/task first. Store in its `prompts/`, one file per
independent task, e.g. `001_User-input-Implementation-chat-ui.md`, then
`002_User-input-Acceptance-group-bubbles.md`. Keep initial and all related inputs
in that same file, ordered `Input 001`, `Input 002`, etc.; internal input numbering
is independent of filenames. A new session/day/stage or a supplemental sentence
does not start a new task. Resume locates and extends the original group; a
truly independent task gets the next group number. A user-specified filename
wins; do not rename or create a second conventionally named copy.

Preserve paragraphs, lists, code, links and wording without rewriting, escaping
or truncation. Use a text fence longer than the longest consecutive backtick run
in the original, or an unambiguous plain-text attachment. Optional actual time,
session/message IDs and context can be included when exposed by the environment;
do not guess or require a platform API/hook. Actual repeated user text is a new
input; re-reading the same saved message during recovery is not. Existing inputs
are never replaced by a merged summary. Effective decisions live in the existing
requirement/decision record, with source input links; original superseded inputs
remain intact.

For "continue" or "choose B", keep the exact words and link the real offered
options separately as **AI context**, never as user text or expanded permission.
For a message spanning requirements, preserve one complete primary copy and link
its input section from others, retaining the context. If ownership is unclear,
resolve it before choosing a nearby file. Archived follow-ups enter a new
requirement under existing rules, linking old input rather than editing history.

Preserve accessible permitted attachments near their input, optionally under
`prompts/attachments/001_Chat-ui/`, with relative links; original attachment names
can stay. A fragile external path alone is not attachment preservation. State
inaccessible attachments, partially exposed messages, unavailable edit history
and lost historical context honestly; preserve only actually available originals,
never AI reconstructions presented as complete. Respect host sensitive-data
storage rules; explicitly label required redaction rather than claiming byte
identity. On first adoption, disclose the actual historical coverage/gaps.

Keep AI-written executable prompts/handoffs separate in their auxiliary home.
Do not scatter raw supplements across reviews/progress/temporary files. Add a
stable link to the prompt group in an existing requirement entry when useful;
source decisions/findings link the specific input. No new per-message approvals,
mandatory hashes/schema, global input index, status table, archive gate or full
conversation export. Hidden system messages, AI reasoning and all tool outputs
are not required. This ordered source history is compatible with the integrated
retrospective body; their responsibilities differ.

## Workspace selection (required)

[Workspace and Worktree Policy](workspace-policy.md) is authoritative. The
current checkout is the default. Creating or reusing a worktree requires
explicit confirmation for the current slice and the exact path
`<project-root>/.worktrees/<req-id>-<sr-id>`. No workflow checkpoint or
framework default provides that consent.

## Abstract actions

| Action | Meaning | Trigger |
|--------|---------|---------|
| `requirement-breakdown` | Kit-owned requirement slicing | `draft` |
| `ui-truth-mapping` | Kit-owned controlled visual implementation | eligible `split_ready` slice after CP-UI |
| `solution-design` | Produce and review the single `design.md` contract | `split_ready` or `acceptance_frozen` |
| `implement` | Execute the current contract with TDD and review | dependency-ready `design_ready` or `in_dev` |
| `finish` | Verify, integrate, and close the slice | implementation/acceptance complete |
| `archive` | Converge completed status in place | all applicable slices `merged` |

Do not emit `spec`, `plan`, or `tasks` actions. CP-DESIGN is used only when
`user_decision_required=true`; the resulting approval also authorizes
implementation inside that scope.

## Environment self-check

Once per run, detect installed frameworks without installing or changing them,
and record the selected methods in `decisions.md`:

| Framework | Detection signs | Useful role |
|-----------|-----------------|-------------|
| spec-kit | `.specify/` or `specify` CLI | optional requirement/design reasoning |
| OpenSpec | `openspec/` or `openspec` CLI | optional brownfield delta reasoning |
| superpowers | skills in a user or repository skill tree | design, TDD, review, finish discipline |
| ECC | registered ECC commands/agents | design, execution, and review discipline |
| native | always available | complete fallback |

When detection is ambiguous, use the native tier unless the distinction would
materially change behavior; then ask once and record the answer.

## Tier selection and dispatch

| Action | Preferred method |
|--------|------------------|
| `solution-design` | superpowers or ECC design reasoning; spec-kit/OpenSpec reasoning may supplement the same `design.md`; otherwise native |
| `implement` | superpowers, then ECC, then native |
| `finish` | superpowers, then ECC, then native |

Spec Kit and OpenSpec must not run their artifact-producing feature/change
pipelines. Their analysis may help shape `design.md`, but `.specify/**`,
`openspec/**`, and separate spec/plan/task outputs remain unchanged.

## Closed loop

```text
entry guards → framework method → contract/verification gate → advance, retry, or block
```

Reconcile re-reads governed truth and emits the next abstract action. A failed
gate does not advance status.

## Traceability

Record the canonical `design.md` path, current SHA-256, source relationships,
and selected reasoning method under the existing `traceability.json`
`source_index.design` contract. Do not emit `spec_refs` or `kind=spec|plan|tasks`
for schema 2.0. Historical `spec_refs` may be read only for legacy
`merged`/`archived` records.
