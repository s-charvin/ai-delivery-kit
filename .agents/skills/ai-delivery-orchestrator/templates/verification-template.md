<!-- ai-delivery-template-language
When instantiating this template, write every human-readable heading, label, result summary, and review note in the user's current conversation language. Keep IDs, paths, commands, code symbols, status values, placeholders, and `ai-delivery-verification:*` markers unchanged. Remove this comment from the finished artifact.
-->

# Verification Evidence: {{subreq_id}}

> This file is the **required evidence** for `verify-before-completion`. The validator rejects `merged` or `archived` when required language-neutral markers are missing.
> Append every review round to the end of section 1. If the review budget is exhausted without a clean result, escalate to the user and **never auto-merge**.

<!-- ai-delivery-verification:review-rounds -->
## 1. Review Rounds
### Round 1 - <date>
- Reviewer:
- Result: clean / changes required
- Reviewed batch / input identity:
- Summary:
- Findings and dispositions: <each known finding/source -> RET case; keep unresolved feedback open>

At batch close, cross-check all known user/AI/review/validation problems against
specific RET observations and dispositions; tiny or non-reusable issues still
belong. User issues may link prompt group input sections. Use existing findings,
not a separate coverage ledger. Chronological review rounds stay here; integrate
knowledge in the single retrospective body.

<!-- ai-delivery-verification:commands-results -->
## 2. Verification Commands and Results
- Static analysis: `<command>` -> `<result>`
- Tests: `<command>` -> `<result>`

Record raw results once in native reports. For reused evidence, include the original command/run, current input/toolchain/variant identity, output hashes, scope and reuse validation; never call it a fresh execution. Optional progress links this record.

- Evidence availability: <key originals readable; retention/durable reference when disposable; historical result recorded but original currently unavailable, if applicable>

Keep detailed reports only when independently useful, link them from here, and
follow [artifact conventions](../references/framework-adaptation.md) when
creating them. New freely named reports use e.g.
`2026-11-03_001_Review-group-bubbles.md`; fixed `verification.md`, native report
names and bound evidence paths are unchanged. This template link is guidance;
remove it or replace it with a valid installed-skill reference in the instance.

### Requirement and Test Coverage
| Requirement source / B-### / AC-### | Actual test path and name | Result / evidence | Uncovered risk or approved deviation |
|---|---|---|---|
| ... | ... | ... | ... |

- Original-source recheck: <omissions, contradictions, and user decision references>
- Boundary, failure and event-order coverage: <tested cases and material exclusions>
- Regression evidence: <reproduced failure and passing result after the fix, when applicable>

## 3. Visual Acceptance
- Structured evidence: `visual-acceptance.json`
- Bound UI truth index SHA-256: `<64-lowercase-hex-sha256>`
- Scenario coverage: `<all indexed scenario ids passed or explicitly waived>`
- Stable Figma bitmap comparison: `<reference/candidate/diff and threshold, or not available>`
- Result: passed / failed

### Final User Acceptance (enabled UI truth only)
- Reviewed scenario/unit IDs and absolute preview paths:
- Current UI truth index SHA-256 and static/motion evidence hashes:
- User response, reviewer and time:
- Static acceptance and separate motion/no-motion acceptance or scoped waiver:
- Rejected, deferred or unreviewed items:

One explicit batch response may cover all listed current evidence. Do not infer
motion acceptance from static approval or treat omitted items as approved.

<!-- ai-delivery-verification:sign-off -->
## 4. Sign-off
- Implementer:
- Reviewer:
- Date:
