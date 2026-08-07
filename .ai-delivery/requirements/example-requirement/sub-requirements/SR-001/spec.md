<!-- ai-delivery-meta: {"version":1,"updated_at":"2026-04-05T00:00:00.000Z","updated_by":"system"} -->

# Example SR-001 Spec

Native-tier lightweight spec (used when no spec framework is installed).

## Problem

The zero-based bridge needs a seeded spec artifact to anchor `SR-001`
before any framework-specific pipeline runs.

## Goal

Provide a minimal, traceable spec that reconcile and the bridge can
resolve without depending on spec-kit, OpenSpec, or any other framework.

## Scope

- In scope: seeded spec/tasks artifacts under the sub-requirement directory.
- Out of scope: real implementation work for this example requirement.

## Acceptance Criteria

- `spec.md` and `tasks.md` exist beside `requirement-slice.md`.
- `traceability.json` `spec_refs` points at both artifacts.
