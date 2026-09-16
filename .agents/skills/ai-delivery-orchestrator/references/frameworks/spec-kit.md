# Framework Guide: spec-kit

When spec-kit is installed, its requirement and design reasoning may supplement
`solution-design`. It does not own an AI Delivery stage or persisted artifact.

## Detection

Detect `.specify/` or a working `specify` CLI. Never install, initialize, or
upgrade spec-kit. Detection/configuration files are read-only inputs.

## Allowed use

- Feed governed inputs: `requirement-slice.md`, applicable global rules, current
  project architecture, API evidence, dependency graph, and enabled UI truth.
- Use spec-kit questions, ambiguity checks, constitution analysis, and design
  reasoning to improve the one canonical `design.md`.
- Audit `B-###`, `AC-###`, source/UI traceability, state behavior, trade-offs,
  and verification strategy against governed evidence.
- Respect an existing constitution when it does not conflict with AI Delivery
  truth; record conflicts in `decisions.md`, with governed truth taking
  precedence.

## Disabled persistence

Do not run `/speckit-specify`, `/speckit-plan`, `/speckit-tasks`, or another step
that creates or changes `.specify/**`, `spec.md`, `plan.md`, `tasks.md`,
checklists, state, or agent metadata. If a useful reasoning flow cannot run
without those writes, apply its method in-session or use the native tier.

Never create framework output and copy it into `.ai-delivery` afterward. Run the
artifact-boundary audit from
[../framework-adaptation.md](../framework-adaptation.md) before advancing status.

## Review and traceability

Review and approval follow `user_decision_required`, never the presence of
spec-kit. Record the selected reasoning method plus canonical `design.md`
path/hash under `traceability.json` `source_index.design`. Do not emit
`spec_refs` or spec/plan/task entries for schema 2.0.

Implementation and finish use superpowers, ECC, or native discipline according
to [../framework-adaptation.md](../framework-adaptation.md).
