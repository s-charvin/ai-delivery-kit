<!-- ai-delivery-template-language
Before using this template, translate every human-readable heading, label, and
prose passage into the user's current conversation language. Keep IDs, status
values, paths, commands, timestamps, hashes, anchors, and placeholders
unchanged. Remove this comment from the instantiated document.
-->

# Retrospective - <req-id>

> This is a required, living requirement-level ledger. The file must exist at
> archive time even when there are no problem records. Record all known delivery
> problems while they happen, including every user-raised issue regardless of
> size, certainty, resolution or reuse value. It is not a framework, product,
> or implementation specification.

## 1. Summary

- Requirement: <req-id>
- Scope: <short scope>
- Status: active
- Last reviewed at: <reviewed-at>

<!-- ai-delivery-retrospective:reviewed-at:<reviewed-at> -->

### 1.1 Problem Map

<!-- ai-delivery-retrospective:problem-index:v2 -->
| ID | Observable trigger | Applicable scenario | Shortest path | knowledge_type | reuse_scope | index_decision | confidence | importance | Status | Details |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
<!-- /ai-delivery-retrospective:problem-index:v2 -->

Use the five qualification fields to decide whether a problem belongs in the
project routing index. Use `reusable` + `project`/`domain` + `include` +
`confirmed` + `high`/`critical` only for problems that are broadly reusable,
verified, and valuable. Use `temporary-decision`, `requirement`, `exclude`,
`partial`/`unverified`, or `normal`/`low` for records that must remain in this
ledger but must not be routed to future requirements. Missing or invalid
qualification fields are treated as not indexable.

### 1.2 Classification Routes

<Use relevant categories such as UI source/control/typography/composition/state/
motion/wiring, logic, migration, architecture, integration, verification, tools
or product-decision clarification. Categories are navigation, not priority or
admission gates. Route each category to its RETs without copying their details.>

### 1.3 Reusable Constraints

- <constraint that prevents recurrence>

Keep the whole document integrated by mechanism, never by revision batches.
Update an existing RET for the same cause/path, retaining every specific report
and material failed attempt. Add a RET only for an independent mechanism and
update classification/map. No supplemental review, "this round additions", end
notes or second UI ledger. Real failure/version dates inside records are valid.
At batch close and before reviewed-at, reverse-check original user inputs and
known findings against specific cases and dispositions; metadata never filters
admission. Remove instructional placeholders from the instance.

## 2. Problem Records

<a id="ret-001"></a>
### RET-001: <short problem name>

#### Problem Scenario and Impact

<Specific user/AI/review findings and source links (including prompt input
sections), observation, expected/actual behavior, affected scope and current
handling state per case. Shared mechanism may contain multiple cases; none may
be lost. A user product decision is not automatically an implementation defect.>

#### Shortest Reproduction Path

1. <minimal setup>
2. <minimal action>
3. <observable actual result>

Expected: <expected result>

#### Root Cause and Evidence

- Category: <applicable classification route; no mandatory category enum>
- Cause: <evidenced cause or explicitly unknown/hypothesis; do not invent certainty>
- Evidence: <observations, logs, tests, or decisions supporting the conclusion>

For UI, use relevant lenses from [retrospective guidance](../references/retrospective-guidance.md):
source/page/parent/theme/state/Collection; real control/resource and typography;
canvas versus slot, constraints/mask/full composition; final property writer,
transitions/motion; production entry/shared consumers/rebind/return/first draw.
Connect visible deviation to authority, mistaken judgment, correction and actual
verification. Do not force every lens onto every issue. Remove this template
link or replace with a valid installed-skill reference in the instance.

#### AI Attempts

| Attempt | Outcome | Why it was tried | Why it succeeded or failed |
| --- | --- | --- | --- |
| <approach> | failed | <reason> | <specific cause> |
| <approach> | successful | <reason> | <specific cause> |

#### Final Solution and Verification

- Solution: <smallest confirmed correction>
- Verification: <actual check/result and remaining untested scope; distinguish not run, partial and accepted; green tests do not close a user report>

Use a compact record for local or unresolved issues; unknown/not run/no general
lesson are valid. Keep their source and disposition even without a reusable
constraint. For a reusable mechanism, fill the applicable path below.

#### Minimal Path for Future Work

- Apply when: <observable applicability conditions>
- First distinguish: <smallest diagnostic check>
- Then change: <smallest correction>
- Verify with: <narrowest confirmation>
- Stop and reassess when: <boundary or conflicting evidence>

#### Do Not Retry and Open Boundaries

- Do not retry: <superseded or disproven approach>
- Unknown: <facts that remain unconfirmed>
- Constraint: <rule for future work>
