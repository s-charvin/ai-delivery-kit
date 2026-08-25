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
- Summary:

<!-- ai-delivery-verification:commands-results -->
## 2. Verification Commands and Results
- Static analysis: `<command>` -> `<result>`
- Tests: `<command>` -> `<result>`

## 3. Visual Acceptance
- Evidence: `<visual-acceptance.md or contracts screenshot path>`
- Result: passed / failed

<!-- ai-delivery-verification:sign-off -->
## 4. Sign-off
- Implementer:
- Reviewer:
- Date:
