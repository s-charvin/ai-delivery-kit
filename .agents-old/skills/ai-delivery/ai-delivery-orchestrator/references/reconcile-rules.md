# Reconcile Rules

- Re-read `.ai-delivery` before trusting `todo.md`.
- Treat `todo.md` as an execution panel rather than business truth.
- Never create `todo.json`.
- Any completed step must be proven by `.ai-delivery` guards.
- If outputs exist but the guard is unsatisfied, re-run or block. Do not skip.
- Treat `spec-kit-input.md` and `spec-kit-binding.json` as derived bridge artifacts, not business truth.
- If governed source artifacts change, regenerate bridge artifacts from `.ai-delivery` instead of editing official Spec Kit outputs in place.
- `todo.md` may compress an official Spec Kit run plus local bind into one action, but the completion check still comes from `.ai-delivery` guards.
