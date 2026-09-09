---
name: ai-delivery-orchestrator
description: Use when a requirement document needs governed end-to-end delivery through Figma UI contracts, a spec pipeline, and merge gates. Use as the single entry when `.ai-delivery` state exists or the user provides a new requirement doc.
---

# AI Delivery Orchestrator

Single entry for requirement → implementation. Leaf skills (`requirement-breakdown`, `ui-truth-mapping`) are pure tools — no pipeline awareness. This skill owns state, gates, blockers, and handoffs.

```
Requirement → [Breakdown?] → Capability review → Solution Design? → Spec → Plan → Tasks → Implement → Merge → Archive
```

The orchestrator is **framework-agnostic**: it emits abstract stage actions and adapts them to whatever AI development framework the user has installed. It never requires installing anything.

## Scenario guidance

During ordinary requirement analysis, scan the scenario registry in
[references/scenario-guidance.md](references/scenario-guidance.md) for triggers
that match the requirement or delivery context. Select only matching scenarios
before making scenario-sensitive decisions; if none matches, continue with the
ordinary workflow rules. The catalog is optional, trigger-based, and advisory:
this scan is part of existing analysis and does not add a stage, artifact, gate,
or downstream maintenance obligation. Put material decisions in the host
workflow's existing record or current action report. If a selected scenario's
relationship is unclear, record `unknown` and ask rather than assuming
compatibility. The reference does not replace the host workflow's own rules.

## Retrospective ledger

Use the requirement-level `retrospective.md` ledger as a lightweight memory aid
for delivery problems and final review. Read [references/retrospective-guidance.md](references/retrospective-guidance.md)
before creating or updating it. The file is required before archive, even when
there are no problem records. Record a reusable failure, a wrong AI attempt, a
user/review correction, or a verification failure while the evidence is
available; record the failed attempt before trying the next approach. Do not
record trivial mechanical fixes. Keep the marked summary problem map and the
detailed problem records in summary-to-detail order, and update the reviewed-at
marker during the final review.

After every ledger update, tell the user the `RET-###` ID, what was added, and
the file path. On resume, read the current
problem map; when a new symptom appears, use the project retrospective index
as a routing map and load only matching historical problem sections. Similar
keywords are not sufficient: applicability conditions and current evidence
must match.

## Artifact language

- Treat bundled template prose as an English source default, not as the output language. Resolve the output language from the user's current conversation, not from the repository, framework, or source template.
- Human-readable content includes Markdown headings, table headers and cells, list labels, explanatory prose, review evidence, solution-design/spec/plan/task text, risk and open-question descriptions, and Mermaid node, edge, and participant labels. Write all of these in the user's current conversation language, including when updating an existing artifact.
- Preserve machine-readable keys, enum values, IDs, paths, commands, code symbols, Mermaid syntax keywords, and literal protocol tokens exactly. Mermaid syntax such as `flowchart`, `stateDiagram-v2`, and `sequenceDiagram` stays English; the labels attached to those constructs are human-readable and must be localized.
- Keep a standard technical term in English only when it is the actual API, library, protocol, code symbol, or a term whose English form is needed for precision. For other technical terms, write the localized term first and retain the original in parentheses on first use (for example, "reducer (`Reducer`)"). Do not treat an English template label such as `State set`, `Owner`, `Guard`, or `Risk` as a protected token.
- Before a design/spec/plan/task gate or CP-DESIGN approval, perform a language review: scan headings, table headers, diagram labels, captions, prose, and review notes; translate unexplained English; confirm that retained English is a protected token or an explicitly introduced technical term. Unexplained English prose or headings are a localization defect and must be fixed before the gate.
- For Markdown templates, localize all human-readable content and remove the `ai-delivery-template-language` instruction comment before writing the artifact. For JSON templates, preserve the structure and localize only human-readable descriptive values.

## Framework adaptation (run once per session)

Before executing any stage action:

1. Self-check the environment per [references/framework-adaptation.md](references/framework-adaptation.md) (installed frameworks: spec-kit / OpenSpec / superpowers / ECC; none installed → native tier).
2. Select the tier for the current action (spec-type vs execution-type actions).
3. Record the selection once in the subreq `decisions.md`.

Action → guide dispatch table and loop model: [references/framework-adaptation.md](references/framework-adaptation.md). Per-framework usage guides: `references/frameworks/{spec-kit,openspec,superpowers,ecc,native}.md`.

## Pipeline

| Stage | Abstract action | Gate |
|-------|-----------------|------|
| 1 | `requirement-breakdown` + light audit | `split_ready` |
| 2 | Capability-gated `ui-truth-mapping` (only when `ui_truth_mode` requires it) | `acceptance_frozen` when enabled |
| 3a | `solution-design` (canonical artifact remains `design.md`) | `design_approved` when `design_mode=full` |
| 3b | `spec` → `plan` → `tasks` | `spec/plan/tasks_ready` |
| 4 | `implement` | `visual_acceptance_passed` → `merged` |
| 5 | `finish` | `merged` |
| 6 | `archive` | `archived` (all subreqs) |

Stage details: [references/stage-breakdown.md](references/stage-breakdown.md), [stage-ui-truth.md](references/stage-ui-truth.md), [stage-design-and-spec.md](references/stage-design-and-spec.md), [stage-4-sdd-bridge.md](references/stage-4-sdd-bridge.md), [stage-implementation.md](references/stage-implementation.md).

## State model

```
draft → split_ready → [acceptance_frozen] → [design_approved] → spec_ready → plan_ready → tasks_ready → in_dev → [visual_acceptance_passed] → merged → archived
```

The bracketed states are capability-gated. `ui_truth_mode=none` and `existing` skip UI truth freeze and visual acceptance; `design_mode=none` and `light` do not require a full approval checkpoint.

Truth lives in `.ai-delivery/requirements/<req-id>/status.json`. Copy the structure of [templates/status-template.json](templates/status-template.json) verbatim and localize its human-readable descriptive values; never regenerate the structure from memory. Instantiate [templates/todo-template.md](templates/todo-template.md) in the user's current conversation language (not source of truth).

The current status template is schema `1.1`. On resume, an active unversioned or schema `1.0` entry missing the state-flow and review fields must be re-audited and migrated before routing; `merged`/`archived` legacy records remain read-only compatible.

| Field | Purpose |
|-------|---------|
| `status` | Current state or `blocked_*` |
| `ui_bearing` | `true` / `false` — whether the slice owns a UI surface; validators require consistency with `ui_truth_mode` |
| `ui_truth_mode` | `none` / `existing` / `runtime-baseline` / `figma` — the UI truth capability required by the slice |
| `design_mode` | `none` / `light` / `full` — the solution-design depth and approval policy |
| `state_flow_required` | Capability-audit result; `true` for MVI/UDF, shared mutable state, complex async/concurrency/recovery, or business-constrained effects, and it forces `design_mode=full` |
| `design_approved` | Compatibility mirror for the solution-design gate; `light` follows AI self-review, `full` follows explicit user approval, and `none` remains `false` |
| `design_review` | Structured review metadata (`review_mode`, `reviewed_design_sha256`, `reviewed_at`, `reviewed_by`) bound to the exact current `design.md` bytes |
| `blocker_scope` | `slice_local` / `action_level_integration` / `requirement_global` |
| `resume_target_status` | Resume target after blocker cleared |

## Reconcile first

On every resume or continue, run reconcile before trusting `todo.md`:

```bash
python3 .agents/skills/ai-delivery-orchestrator/scripts/reconcile-delivery.py \
  .ai-delivery/requirements/<req-id>/status.json \
  --req-root .ai-delivery/requirements/<req-id>
```

reconcile emits abstract actions (`solution-design` / `spec` / `plan` / `tasks` / `implement` / `finish` / `archive`, plus kit-owned skills) — never third-party skill names. Rules: [references/reconcile-rules.md](references/reconcile-rules.md).

## Handoff table

Each stage has one legal next action. Full table: [references/handoff-table.md](references/handoff-table.md).

| Done | Next |
|------|------|
| `split_ready` + audit (`ui_truth_mode=figma` or `runtime-baseline`) | CP-UI → `ui-truth-mapping` |
| `split_ready` + audit (`ui_truth_mode=none` or `existing`) | `solution-design` when `design_mode` is `light` or `full`; otherwise `spec` |
| `acceptance_frozen` | `solution-design` according to `design_mode` |
| `design_approved=true` or `design_mode=none` | `spec` |
| All `tasks_ready` + CP-001 | Stage 4 `implement` |
| Slice done | `finish` |

## Pause points (6)

1. After split/skip decision — confirm with user
2. Before enabled UI truth production-code work — CP-UI, authorize the controlled visual implementation (workspace choice is a separate user decision)
3. After a `design_mode=full` solution-design session — CP-DESIGN, explicit approval before `spec`
4. After `tasks_ready` — CP-001, confirm before the remaining development work
5. Review-loop budget exhausted — the task-level review loop (implement → review → fix → re-review) stopped without a clean round; report outstanding findings and wait for the user
6. After all subreqs `merged` — CP-ARCHIVE, confirm converging each subreq status in place to `archived`

## Hard boundary

- Do not move workflow truth out of `.ai-delivery`.
- Workspace selection follows [references/workspace-policy.md](references/workspace-policy.md). The current checkout is the default; creating or reusing a worktree requires separate explicit confirmation for the current sub-requirement, and an approved worktree must be at `<project-root>/.worktrees/<req-id>-<sr-id>`. CP-UI, CP-001, framework defaults, and legacy `require_isolated_worktree` values are not consent. When already in an external worktree, stop production edits and ask the user to switch to the project checkout or the exact project-local worktree. Leave the external worktree unchanged; switching does not authorize migration or deletion.
- External skill defaults never authorize framework-owned artifact paths. External skills provide methods and execution discipline only: pass canonical `.ai-delivery` output paths before invocation; if a persistence step cannot honor them, skip that step and write the equivalent canonical artifact directly. Never create process/governance artifacts under `docs/superpowers/**`, `.superpowers/**`, `.specify/**`, `openspec/**`, or another host-tree framework directory and move them afterward.
- Outside `.ai-delivery/`, writes are limited to production source, project-native tests, goldens/official previews, and runtime assets. Before advancing any gate, compare the entry/exit Git status/content fingerprint and independent filesystem fingerprints for every declared external default output root, including ignored files and at least the four forbidden roots above. Path, status, type, symlink-target, or SHA-256 drift catches writes even when a path was already dirty or ignored. A new or modified process/governance artifact outside `.ai-delivery/` sets `blocked_verification_failure`.
- Do not require the user to install or pick frameworks/skills on the normal path; adapt to what is already installed.
- Do not let `ui_truth_mode=figma` or `runtime-baseline` subreqs enter `spec` before `acceptance_frozen`; `none` and `existing` bypass that gate. `acceptance_frozen` requires both static visual confirmation and a resolved motion confirmation/waiver for every applicable unit; “static / no motion” is still an explicit confirmed decision. Data-bound visuals with no real value stay empty/omitted; test fixtures never become production UI.
- Do not dispatch `ui-truth-mapping` unless the mode enables the capability and CP-UI is explicitly confirmed and recorded. Stage 2 writes production code in the user-approved workspace, uses TDD/golden tests, and closes a fresh-context review loop.
- Do not let UI truth slices claim `merged` before `visual_acceptance_passed`; `none` and `existing` use ordinary behavior/semantic verification.
- Do not promote slice-local blockers to requirement-global while any runnable item exists.
- Gate / blocker / status / merge decisions never go to subagents. Leaf skills may use subagents per their own rules (`ui-truth-mapping` per-unit, Stage 4 per the chosen execution tier).
- Do not write solution-design docs into framework-owned directories during orchestrator solution-design mode; write the canonical artifact to subreq `design.md` and keep only a short pointer in `notes`.
- For `state_flow_required=true`, Stage 3a is always `design_mode=full` and CP-DESIGN-gated. The canonical `design.md` must contain the state taxonomy, MVI loop, lifecycle chart, UI projection, authoritative transition matrix, applicable async sequences, invariants, and traceability. Use Mermaid Markdown only; do not create a second state index or HTML artifact.
- A design approval is valid only when `design_review.reviewed_design_sha256` matches the exact UTF-8 bytes of the current `design.md`, the review mode matches `design_mode`, and the review timestamp/actor are present. A changed design file invalidates the gate and must reopen `solution-design` (CP-DESIGN for `full`).
- For `ui_truth_mode=figma` or `runtime-baseline`, do not set `acceptance_frozen` until each UI unit has a real host-stack component, complete applicability-gated runtime coverage, an official-stack preview for every visual scenario whose **absolute path** was shown to the user, a valid v2 `contracts/ui-truth-index.json` with matching SHA-256 hashes and confirmation bound to current preview hashes, separate static visual confirmation and motion confirmation/waiver (including an explicit confirmed static/no-motion decision), and a clean Stage 2 review. When the host can deterministically record the real motion, include the GIF preview path and hash; when it cannot, record the reason and defer that runtime acceptance to Stage 4. Stage 4 must record independent motion acceptance for every unit before `visual_acceptance_passed`. Stage 2 authors via `ui-truth-mapping` only — never via `figma-design-to-code`, and never by generating `ui-contract.html`. Do not use an unapproved placeholder, generic icon, dummy/fixture visual, painted input shell, or silent asset fallback; missing resources require an explicit user choice to render empty, defer, or block. A missing data-bound value must render the real empty/omitted state, never fabricated content.
- Stage 4: for `ui_truth_mode=figma` or `runtime-baseline`, reuse the Stage 2 user-approved workspace; do not create a second workspace or re-draw the component. `existing` uses the existing component and ordinary behavior/semantic checks; `none` has no UI truth artifact. Do not re-query TemPad / run `figma-design-to-code` by default; the frozen component plus confirmed preview is the visual source of truth. Follow fill / hug / fixed (fill = parent minus insets, not snapshot px). Do not re-draw Flutter from HTML.
- Do not set `merged` for `ui_truth_mode=figma` or `runtime-baseline` without prior `acceptance_frozen` + `visual_acceptance_passed` + a valid v2 `ui-truth-index.json` + structured `visual-acceptance.json` covering every indexed scenario. `none` and `existing` close through ordinary verification.
- Set `archived` only through `scripts/archive-subrequirement.py` after CP-ARCHIVE confirmation. The action updates `status.json` in place and must not create an `archive/<ISO-ts>/` directory, copy canonical artifacts, or write `MANIFEST.json`. The completed requirement directory remains the historical source of truth; subsequent changes use a new `<req-id>` directory.
- Do not claim a task done or merge work whose latest review round is not clean; the review loop escalates to the user when its budget is exhausted.
- Edit one file at a time during implementation; rebase branches (no merge commits).

## Status transition gates

| Target | Requirement |
|--------|-------------|
| `acceptance_frozen` | Required only for `ui_truth_mode=figma` or `runtime-baseline`: CP-UI recorded; user-approved workspace evidence recorded; real component compiles; Stage 2 TDD/review clean; all ten runtime dimensions are `covered` or reasoned `not_applicable`; preview paths, v2 index hashes/provenance/profile/scenario coverage, preview-bound static confirmations, and motion confirmations/waivers (with unavailable-preview reasons when needed) validate |
| `spec/plan/tasks_ready` (UI truth) | Valid prior `acceptance_frozen`; v2 index paths, hashes, coverage, and confirmation bindings still validate |
| `merged` (UI truth) | UI truth mode has prior `acceptance_frozen` + `visual_acceptance_passed` + valid v2 index + structured `visual-acceptance.json`; `existing` uses ordinary behavior/semantic evidence, and `none` skips visual acceptance |
| `archived` | Status converged in place; canonical artifacts remain at their original paths and later changes use a new requirement directory |

## Split decision

**Skip** when ALL: single screen, no shared state, one developer, no cross-cutting rules, doc under ~300 words.

**Split** when ANY: 2+ screens, shared state, multi-developer coordination, cross-feature infrastructure.

State decision with reasoning, then proceed. Details: [references/stage-breakdown.md](references/stage-breakdown.md).

## Light audit (not solution-design exploration)

After `split_ready`, main session runs inline 4-check audit per subreq (gaps, conflicts, states, permissions), then resolves `ui_truth_mode` and `design_mode`. Critical issues → blockers; otherwise append to `notes`. Do not run the `solution-design` action during the light audit.

## Stage 4 (summary)

The `implement` action executes per the selected tier (see `references/frameworks/`): subagent-driven when superpowers is present, agent-driven with ECC, inline disciplined on the native tier. Default discipline regardless of tier: sequential tasks, TDD inside, code review before completion claims. Never parallel implementers on the same slice files.

Chain: resolve the user-approved workspace under `references/workspace-policy.md` and reuse the Stage 2 choice for enabled UI truth modes → task execution (TDD) → code review → scenario-complete visual/runtime acceptance recorded in `visual-acceptance.json` when required → verification before completion → full test → merge.

UI truth slices: wire the already-written component (API / route / state / mount); do not re-query TemPad / run `figma-design-to-code` by default. `existing` UI slices do not enter Stage 2; they use normal project behavior and semantic checks.

Full runbook: [references/stage-implementation.md](references/stage-implementation.md).

## Blockers

Narrowest blocker wins; continue safest runnable work first. On validator failure use `blocked_verification_failure`. Catalog: [references/blocker-catalog.md](references/blocker-catalog.md).

## API policy

API docs pass directly to the spec pipeline and implementation. Gaps → `integration_deferred` in notes; they do not block UI mapping or shell work.

## User entry

1. Inspect `.ai-delivery/requirements/*`, `status.json`, run reconcile.
2. Read `.ai-delivery/retrospectives/index.md` if it exists; select matching
   problem rows and load only their linked sections. If the current requirement
   has `retrospective.md`, read its problem map for unfinished investigation.
3. Recommend `continue req-xxx` or `create req-yyy`.
4. Pause for human confirmation before routing.

| Intent | Mode |
|--------|------|
| New requirement + sources | `bootstrap` or `resume` |
| Continue orchestrating | `resume` |
| UI truth capability pending authorization | `confirm_ui` (CP-UI) |
| tasks_ready, proceed to dev | `confirm_to_dev` (CP-001) |
| Full solution-design pending approval | `confirm_solution_design` (CP-DESIGN) |
| Blocker resolved | `blocker_recovery` (CP-002) |

## Runtime modes

`bootstrap` | `resume` | `confirm_ui` | `confirm_solution_design` | `confirm_to_dev` | `blocker_recovery` | `closing` | `completed`

Checkpoints: CP-UI (pre-enabled UI truth production code), CP-DESIGN (full solution-design approval), CP-001 (remaining development), CP-002 (hard blocker, only when no runnable items remain), CP-ARCHIVE (pre-freeze, all subreqs merged).

## Completion

All executable subreqs `merged` → runtime_mode `closing` (CP-ARCHIVE). Before
the final archive command, instantiate `templates/delivery-report-template.md`
as a temporary template in the user's current conversation language, remove its
`ai-delivery-template-language` comment, and preserve its placeholders. Run
`scripts/archive-subrequirement.py` per subreq to advance status to `archived` in
place without copying canonical artifacts; pass the prepared template to
the final command with `--delivery-report-template <path>`. The requirement
must have `retrospective.md`; instantiate
`templates/retrospective-index-template.md` in the user's current conversation
language, remove its `ai-delivery-template-language` instruction, preserve its
markers and placeholder, and pass it to the final command with
`--retrospective-index-template <path>`. The archive command requires exactly
one parseable `<!-- ai-delivery-retrospective:reviewed-at:<ISO-8601> -->` marker
whose calendar date matches the archive date, then reads the marked problem map
and idempotently updates `.ai-delivery/retrospectives/index.md`; it does not
create, rewrite, summarize, or audit the ledger. A ledger with no problem rows
is valid and creates no index rows. A missing or stale ledger blocks archive.
Tell the user which problem rows were registered.
Do not claim `completed` until the localized `delivery-report.md` exists. When
every subreq is `archived`, the requirement is `completed`; canonical artifacts
remain in place and any later change requires a new `<req-id>` directory.

## Orchestration shape (invariants)

These rules prevent orchestration regressions. They apply to the main session and reconcile dispatch:

1. **Main session is the orchestrator** — one human-facing session drives the sequential pipeline (Pattern 4). No router persona sits between stages.
2. **Dispatch table is data, not a router** — `ACTION_BY_STATUS` / reconcile output names abstract actions; do not introduce a persona that re-derives or re-explains the table.
3. **Subagents are leaf-only, depth ≤ 1** — implementation and review may delegate to subagents per tier rules; the orchestrator never nests orchestrator personas.
4. **Forbidden patterns** — persona-calls-persona chains, “sequential orchestrator” layers that only paraphrase the previous stage, and deep persona trees.
5. **Review never auto-merges** — `merged` / `archived` require clean review evidence (`verification.md`) and human gates; budget exhaustion always pauses for the user.

This kit owns single-repo governed delivery (`.ai-delivery/`, `status.json`, gates). Multi-party coordination is out of scope here — install [ai-delivery-coordination](https://github.com/s-charvin/ai-delivery-coordination) separately if needed.
