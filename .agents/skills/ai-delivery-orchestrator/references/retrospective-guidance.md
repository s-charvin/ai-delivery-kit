# Retrospective Guidance

Retrospective is an optional, requirement-level learning ledger for reducing
repeat rework in client requirement delivery. It is framework-neutral and does
not define product behavior, architecture, or a lifecycle gate.

## Record only reusable problems

Create or update `retrospective.md` when a problem has reuse value, especially:

- a substantive failed attempt or a second attempt at the same symptom;
- a user or review correction that invalidates a previous direction;
- a verification, acceptance, integration, or runtime failure;
- a root cause that could recur in another requirement.

Do not record spelling fixes, isolated command mistakes, or mechanical edits
with no reusable lesson. Record an incorrect AI approach before trying the next
approach, including why it looked plausible and why it failed.

## Required problem record

Keep the document in summary-to-detail order. The summary problem map is a
stable, marked Markdown table. Use a stable `RET-###` ID per problem and link
the row to its detail heading. Each detail must contain: scenario and impact,
shortest reproduction path, expected and actual result, root cause and
evidence, every material AI attempt with outcome and success/failure reason,
final solution and verification, minimal future path, do-not-retry guidance,
open boundaries, and a reusable constraint.

The minimal future path must answer four questions: when does this apply, what
is the smallest discriminating check, what is the smallest correction, and
what is the narrowest verification? State a stop condition when evidence is
ambiguous or the applicability boundary is not met.

After every update, tell the user the recorded ID, what was added, and the
ledger path. This is a visibility aid, not a gate. The user may request an
omission or correction before archive.

## Progressive loading

The project index at `.ai-delivery/retrospectives/index.md` contains only
archived problem rows. It is a routing map, not a second source of truth. Each
row keeps the trigger, applicable scenario, minimal path, status, archive date,
and a link to the exact problem section. Do not place failure history or full
root-cause narratives in the index.

At requirement creation or resume:

1. Read the compact index and the current requirement's problem map, if one exists.
2. Match candidates against the current task's observable trigger and applicability conditions.
3. Read only matching problem sections. Apply their first diagnostic check before their suggested correction.

Re-scan when a new symptom appears. Similar wording alone is not a match. A
historical conclusion is advisory and cannot override current evidence,
architecture constraints, product requirements, or unconfirmed external facts.

## Archive behavior

Archive does not generate or rewrite retrospective content. If the ledger
exists, the archive action reads its marked problem map and idempotently replaces
that requirement's rows in the project index. If no ledger exists, it creates no
ledger and no index entry. The index update copies existing summaries only; it
does not infer missing problems or perform a memory audit.

The requirement-level ledger remains next to its requirement artifacts as the
full historical source. The archive snapshot for sub-requirements and the
delivery report keep their existing responsibilities. Once the requirement is
archived, treat its ledger and index entry as read-only; record later discoveries
in a new requirement and link back to the old problem where useful.
