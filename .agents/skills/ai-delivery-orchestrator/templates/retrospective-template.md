<!-- ai-delivery-template-language
Before using this template, translate every human-readable heading, label, and
prose passage into the user's current conversation language. Keep IDs, status
values, paths, commands, timestamps, hashes, anchors, and placeholders
unchanged. Remove this comment from the instantiated document.
-->

# Retrospective - <req-id>

> This is a required, living requirement-level ledger. The file must exist at
> archive time even when there are no problem records. Record reusable delivery
> failures and corrections while they happen. It is not a framework, product,
> or implementation specification.

## 1. Summary

- Requirement: <req-id>
- Scope: <short scope>
- Status: active
- Last reviewed at: <reviewed-at>

<!-- ai-delivery-retrospective:reviewed-at:<reviewed-at> -->

### 1.1 Problem Map

<!-- ai-delivery-retrospective:problem-index:v1 -->
| ID | Observable trigger | Applicable scenario | Shortest path | Status | Details |
| --- | --- | --- | --- | --- | --- |
<!-- /ai-delivery-retrospective:problem-index:v1 -->

### 1.2 Reusable Constraints

- <constraint that prevents recurrence>

## 2. Problem Records

### RET-001: <short problem name>

#### Problem Scenario and Impact

<What happened, who or what was affected, and why it matters.>

#### Shortest Reproduction Path

1. <minimal setup>
2. <minimal action>
3. <observable actual result>

Expected: <expected result>

#### Root Cause and Evidence

- Category: <requirement misread | architecture deviation | implementation defect | verification defect | evidence boundary | external dependency>
- Cause: <specific causal explanation>
- Evidence: <observations, logs, tests, or decisions supporting the conclusion>

#### AI Attempts

| Attempt | Outcome | Why it was tried | Why it succeeded or failed |
| --- | --- | --- | --- |
| <approach> | failed | <reason> | <specific cause> |
| <approach> | successful | <reason> | <specific cause> |

#### Final Solution and Verification

- Solution: <smallest confirmed correction>
- Verification: <exact behavior, test, or evidence that confirms it>

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
