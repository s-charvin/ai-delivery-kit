# Retrospective Guidance

The requirement-level `retrospective.md` is the single living ledger of known
delivery problems. Collect problems when encountered in UI, logic, migration,
architecture, integration, tests, and tools under the same rule; no category
has collection priority. Normal edits and successful execution are not problems.
This ledger adds no stage, persona, product specification, or approval chain.

Maintain stable knowledge through the [quality loop](delivery-quality-loop.md)
in one registered, writable project source. Current behavior and unconfirmed
hypotheses do not automatically become mandatory rules. Source successful
patterns in existing design/decisions without inventing RETs. Maintenance
authority is not a waiver: never lower standards to close a current finding.

## Admission is separate from reuse

Every problem explicitly raised by the user must be represented, including a
one-line or mechanical correction, an already-fixed, deferred, unreplicated,
unknown-cause, or requirement-only issue. Preserve the user's description,
source, actual observation, and current disposition. Record AI, review,
verification and runtime findings too. Green tests never exclude a user report.

Do not use `importance`, `confidence`, `reuse_scope`, `knowledge_type`, or
`index_decision` as admission filters. They describe the recorded knowledge and
its project-index eligibility. Do not invent a confirmed cause, high importance,
or general usefulness to admit a local issue. A short requirement-only record
is sufficient when there is no general lesson. Preserve reports judged to be a
misunderstanding, changed product decision, or no longer reproducible, with the
reason and evidence; do not silently remove them or label every decision a bug.

## Capture, integrate, cross-check

1. On a user correction or a discovered implementation/review/verification
   problem, record the symptom, source, current hypothesis and evidence **before
   the next attempt**. An unknown cause stays unknown. Save the user's complete
   input in its requirement prompt group first; see
   [framework-adaptation.md](framework-adaptation.md).
2. Match by trigger, cause, and smallest correction path. A shared mechanism
   updates its existing RET, retaining each specific report and material attempt.
   Similar words alone do not justify merging. Independent mechanisms get new
   stable `RET-###` IDs and are integrated into classification and problem map.
3. At batch close, cross-check every known user issue and other known finding
   against a specific RET case and disposition. Reuse existing `verification.md`
   findings and prompt input anchors; add RET references there, not a second
   coverage ledger. An existing similar RET is insufficient unless this issue's
   concrete observation and outcome are actually in it.
4. Before archive, reverse-check from those original records, integrate omissions
   directly, then update the sole reviewed-at marker. Reuse established links
   and valid evidence; do not repeatedly scan all historical logs.

Completeness means all **known** issues are locatable, especially every problem
the user raised. It does not mean every latent defect has been discovered.
A RET link does not close a source finding. Distinguish pending reproduction,
confirmed deviation with unproven cause, fixed but not run, partial verification,
and formal acceptance. `confidence=confirmed` applies only to the conclusion
actually supported; it does not accept all UI states. Keep STOPs, waivers,
withdrawn hypotheses and untested scope explicit.

## One coherent body, never revision batches

`retrospective.md` must always be one coherent requirement retrospective.
Integrate every new finding into its classification and record. **Do not append
revision-batch sections** such as dated supplemental reviews, "this round
additions", or "additional retrospective", or leave detached notes at the end.
Do not create a UI-only retrospective, stage copy, supplemental ledger, or
second issue list. Modification notes belong in Git history.

Maintain one complete account per mechanism. Classification and the problem
map route to it rather than duplicating its history. Preserve stable IDs,
anchors, failed attempts, evidence, and the basis for retractions. Move later
outcomes back to their record. Real failure dates, changed-source versions and
verification dates belong **inside** the relevant record; chronology in source
review/decision/run records is valid. Never implement this rule as a ban on dates.

## Record shape

Use [the template](../templates/retrospective-template.md), summary to detail:
classification routes → marked v2 problem map → stable RET records. Each map
row declares the existing five qualification fields and links to its own detail
heading or explicit stable anchor. Preserve existing valid anchors; for new
records an explicit `ret-001` anchor avoids title-dependent links. No new
required machine metadata or second table protocol is introduced.

In the detail, keep the specific reports/sources and dispositions; scenario,
expected/actual observation and smallest reproduction; cause and confidence
with evidence; material AI attempts and why each seemed plausible but failed;
correction, actual verification and uncovered scope. For unresolved/local issues
keep this compact and mark unknown/not run/not generalizable honestly. Do not
force a generic lesson or fictional failed test. Where reuse is established,
give applicability, first discriminating check, smallest correction, narrowest
verification, stop condition and disproven paths. "Be more careful" or "add more
tests" is not a discriminating method.

After updates, report the RET IDs, material change and ledger path concisely;
batch the notice with the normal progress update rather than a new interruption.

## UI investigation lenses (when applicable)

These lenses apply to all UI delivery, including `figma`, `runtime-baseline`,
and `existing`; they do not expand any mode's existing acceptance gates and do
not require visual records for non-UI tasks. Use the relevant lenses, not a
per-dimension quota or mandatory fields on every RET.

| Lens | Discriminating questions |
|---|---|
| Source and applicability | Correct page, complete parent, theme, state, variable Collection and latest user decision? What does this source actually prove? |
| Control, resource, typography | Why this real control/asset? Check weight, size, line box, fontPadding, gradient, spacing, radius, icon transform and canvas versus slot. |
| Layout and full composition | Are hug/fill/fixed, anchors, clipping, underlay, masks and production host composition correct? A correct child is insufficient for its parent. |
| Runtime state and motion | Which assignment wins last? Do theme/background/IME/panel/send/failure/quote/loading transitions restore old UI? A static loading image is not motion evidence. |
| Production wiring and regression | Is the new UI enabled from the actual entry? Check shared consumers, rebinding, return and first draw at the proven scope. |

Connect visible deviation → authoritative source → mistaken AI judgment or
omission → correction → actual verification and remaining boundary. Preserve
concrete wrong attempts, including ones that looked reasonable. Do not promote
project-specific token values, fields or product choices into universal rules.

## Progressive loading

The project index at `.ai-delivery/retrospectives/index.md` contains only
archived problem rows that are explicitly qualified for reuse. A row is
indexable only when `knowledge_type=reusable`, `reuse_scope=project` or
`domain`, `index_decision=include`, `confidence=confirmed`, and
`importance=high` or `critical`. Missing or invalid qualification fields are
not indexable. The index is a routing map, not a second source of truth. Each
row keeps the trigger, applicable scenario, minimal path, status, archive date,
and a link to the exact problem section. Do not place failure history or full
root-cause narratives in the index.

### Legacy ledger upgrade before archive

When an older `retrospective.md` uses `problem-index:v1` or the former
six-column problem map, the AI must upgrade it before invoking the archive
script. Read the full problem records, preserve their IDs, detail headings,
anchors, evidence, and conclusions, then add the v2 qualification columns and
change only the map marker/schema needed for the upgrade. Classify from recorded
evidence; do not infer reuse or importance from the title alone. If the record
cannot establish reuse scope, confidence, or importance, use conservative
non-indexable metadata (`index_decision=exclude`, `confidence=unverified`) and
keep the full record in the ledger. The archive script rejects legacy maps so
an incomplete migration cannot silently lose or over-index knowledge.

At requirement creation or resume:

1. Read the compact index and the current requirement's problem map, if one exists.
2. Match candidates against the current task's observable trigger and applicability conditions.
3. Read only matching problem sections. Apply their first diagnostic check before their suggested correction.

Re-scan when a new symptom appears. Similar wording alone is not a match. A
historical conclusion is advisory and cannot override current evidence,
architecture constraints, product requirements, or unconfirmed external facts.

## Archive behavior and limits

The ledger is required even with no known problems. Keep exactly one
`<!-- ai-delivery-retrospective:reviewed-at:<reviewed-at> -->` marker, updated after
final source-to-RET review; its calendar date must match archive. A genuinely
empty ledger is valid. Never use an empty ledger to bypass known findings.

Archive does not generate, rewrite or semantically audit the ledger. It checks
the review marker and objective map/detail structure, then keeps only explicitly qualified
rows and idempotently replaces this requirement's project-index rows. Structural
checks detect duplicate markers/IDs, missing or orphan details, broken anchors,
and recognized revision-batch headings with file/line diagnostics. They cannot
prove all user reports were collected or all duplicate mechanisms were merged;
source cross-check and behavioral evaluation carry that responsibility. Novel
patch prose may require review even when the script accepts the structure.

Temporary decisions, requirement-only issues, unconfirmed causes and mechanical
corrections remain in the ledger; nonqualifying rows create no index entries.
Keep the full historical source next to the requirement, with no archive copy.
Once archived, its ledger and index entry are read-only; later discoveries use
a new requirement and may link the earlier problem.

Use `YYYY-MM-DD` (for example `2026-11-05`) or RFC3339Nano with a timezone (for example `2026-11-05T12:00:00+08:00`). Datetimes without a timezone, single-digit hours, comma fractions, and offsets such as `+24:00` are invalid. The marker’s own calendar date must match the archive date.
