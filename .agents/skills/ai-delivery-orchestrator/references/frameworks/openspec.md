# Framework Guide: OpenSpec

When OpenSpec is installed, its brownfield delta reasoning may supplement
`solution-design`. It does not own an AI Delivery stage or persisted artifact.

## Detection

Detect an existing `openspec/` tree or a working `openspec` CLI. Never install or
initialize OpenSpec. Existing OpenSpec content is read-only evidence.

## Allowed use

- Compare the requirement slice with current behavior and identify the minimal
  observable delta.
- Use proposal and technical-design reasoning to improve scope, `B-###`
  behavior, `AC-###` acceptance, risks, state transitions, and verification in
  the canonical `design.md`.
- For UI truth, reference current unit/scenario IDs, evidence origins, and frozen
  scopes without restating visual truth or Runtime Coverage.
- Run read-only validation only when it does not create or update OpenSpec state.

## Disabled persistence

Do not create an OpenSpec change, proposal, design, task list, archive, state, or
session metadata. Do not run `openspec archive`. If a command requires writes
under `openspec/**` or separate `spec.md`, `plan.md`, or `tasks.md` files, skip
that command and apply the useful reasoning in-session or use the native tier.

Never create framework output and copy it back afterward. Run the
artifact-boundary audit from
[../framework-adaptation.md](../framework-adaptation.md) before advancing status.

## Review and traceability

Review and approval follow `user_decision_required`, not framework presence.
Record the selected method plus canonical `design.md` path/hash under
`traceability.json` `source_index.design`. Do not emit `spec_refs` or
spec/plan/task entries for schema 2.0.

Implementation and finish use superpowers, ECC, or native discipline according
to [../framework-adaptation.md](../framework-adaptation.md).
