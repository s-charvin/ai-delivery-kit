# UI Truth Mapping HTML Contract v2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace YAML/section-map UI contracts with a single-versioned `ui-contract.html` that is reviewable, implementable, and incrementally patchable.

**Architecture:** Add an HTML v2 validator and fixtures first, then rewrite the `ui-truth-mapping` skill and its Chinese mirror, then migrate orchestrator consumption, gates, hooks, and bootstrap assets. Every task includes a failing test or structural validation before implementation.

**Tech Stack:** Python 3 + PyYAML + BeautifulSoup-compatible standard parsing, Markdown skill definitions, shell test scripts, Go managed-asset tests.

## Global Constraints

- Do not create or update `ui-acceptance-contract.yaml` or `section-map.json` for v2.
- Do not maintain parallel YAML/JSON/HTML UI truth sources.
- `get_code` remains the primary TemPad evidence; `get_structure` is only for hierarchy/geometry/overlap ambiguity.
- Screenshots only support post-implementation visual regression; never infer contract CSS/token/layout values from screenshots.
- Each `ui-contract.html` contains exactly one unit: `page`, `modal`, or `shared-component`.
- Completion metadata must be present for delivered units.
- Use Conventional Commits for every completed task.
- Keep `.superpowers/` out of commits.

---

### Task 1: Add failing HTML v2 validator tests and fixtures

**Files:**
- Create: `tests/ai-delivery-skills/fixtures/ui-contract-good.html`
- Create: `tests/ai-delivery-skills/fixtures/ui-contract-bad.html`
- Create: `tests/ai-delivery-skills/ui-contract-html-validator.test.sh`
- Modify: `tests/ai-delivery-skills/run.sh` or the existing test runner that includes shell suites (locate with `rg "ui-contract-validator"` before editing)

**Interfaces:**
- Consumes: none.
- Produces: command `python3 scripts/validate-ui-contract-html.py <contract.html>` expected to exit 0 on good fixture and non-zero on bad fixture; `validate_delivery_contracts(root)` shell helper path used by the test suite if the repo already has a similar helper.

- [ ] **Step 1: Write the good fixture**

Create `tests/ai-delivery-skills/fixtures/ui-contract-good.html`:

```html
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>UI Contract: fixture-profile-page</title>
  <script type="application/json" id="ui-contract-meta">
  {
    "schema_version": 2,
    "contract_id": "fixture-profile-page",
    "source": {
      "requirement": "requirement-slice.md",
      "design_file": "fixture-file-key",
      "root_node": "1:100",
      "cache": ".ai-delivery/figma-cache/fixture-file-key"
    },
    "unit": {
      "id": "profile-page",
      "type": "page",
      "title": "Profile Page",
      "route_or_trigger": "/profile",
      "requirements": ["fixture-subreq-1"],
      "source_node": "1:200",
      "dependencies": []
    },
    "states": [
      { "id": "idle", "source_node": "1:200", "default": true }
    ],
    "revision": 1,
    "delivery": {
      "status": "frozen",
      "implemented": null
    }
  }
  </script>
  <style>
    :root {
      --color-surface: #F2F7FA;
      --color-text: #111111;
      --space-page-x: 16px;
    }
    [data-ui-contract] { background: var(--color-surface); color: var(--color-text); min-height: 100vh; }
    [data-ui-id="profile-header"] { padding: 24px var(--space-page-x); }
    [data-ui-id="profile-title"] { font-size: 24px; line-height: 32px; font-weight: 600; text-align: center; }
  </style>
</head>
<body>
  <main data-ui-contract data-ui-unit-id="profile-page" data-ui-unit-type="page" data-ui-state-default="idle">
    <section data-ui-id="profile-header" data-ui-kind="container" data-figma-node="1:201" data-evidence="structure+code">
      <h1 data-ui-id="profile-title" data-ui-kind="text" data-figma-node="1:202" data-evidence="code">Profile</h1>
    </section>
    <template data-ui-state="idle">
      <div data-ui-id="profile-idle-note" data-ui-kind="text" data-figma-node="1:203" data-evidence="code">No notifications.</div>
    </template>
    <details data-ui-review-panel>
      <summary>Contract evidence</summary>
      <dl>
        <dt data-ui-evidence-for="profile-header">Inference</dt>
        <dd>Grouped repeated Figma rows into a semantic header container from nodes 1:201-1:202.</dd>
      </dl>
    </details>
  </main>
</body>
</html>
```

- [ ] **Step 2: Write the bad fixture**

Create `tests/ai-delivery-skills/fixtures/ui-contract-bad.html` with:
- missing `ui-contract-meta`;
- duplicate `data-ui-id="duplicate-id"`;
- `data-ui-unit-type="screen"`;
- no `data-figma-node` on a component;
- a `<div data-ui-kind="status-bar">` system UI component.

Keep it compact but invalid.

- [ ] **Step 3: Write the failing shell test**

Create `tests/ai-delivery-skills/ui-contract-html-validator.test.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
GOOD="$ROOT/tests/ai-delivery-skills/fixtures/ui-contract-good.html"
BAD="$ROOT/tests/ai-delivery-skills/fixtures/ui-contract-bad.html"
VALIDATOR="$ROOT/scripts/validate-ui-contract-html.py"

fail() { echo "FAIL: $*" >&2; exit 1; }

python3 "$VALIDATOR" "$GOOD" >"$TMPDIR/ui-contract-good.out" 2>&1 || {
  cat "$TMPDIR/ui-contract-good.out" >&2
  fail "good fixture should validate"
}
grep -q '^OK:' "$TMPDIR/ui-contract-good.out" || fail "good fixture must print OK"

if python3 "$VALIDATOR" "$BAD" >"$TMPDIR/ui-contract-bad.out" 2>&1; then
  cat "$TMPDIR/ui-contract-bad.out" >&2
  fail "bad fixture unexpectedly validated"
fi
grep -q 'INVALID:' "$TMPDIR/ui-contract-bad.out" || fail "bad fixture must print INVALID"
grep -q 'META' "$TMPDIR/ui-contract-bad.out" || fail "bad fixture should report metadata errors"
grep -q 'DUPLICATE_ID' "$TMPDIR/ui-contract-bad.out" || fail "bad fixture should report duplicate IDs"
grep -q 'SOURCE_NODE' "$TMPDIR/ui-contract-bad.out" || fail "bad fixture should report missing source nodes"
grep -q 'SYSTEM_UI' "$TMPDIR/ui-contract-bad.out" || fail "bad fixture should reject system UI"

echo "PASS: ui-contract-html-validator"
```

- [ ] **Step 4: Run test to verify it fails**

Run: `bash tests/ai-delivery-skills/ui-contract-html-validator.test.sh`
Expected: FAIL with `No such file or directory` for `scripts/validate-ui-contract-html.py`.

- [ ] **Step 5: Commit the failing test and fixtures**

```bash
git add tests/ai-delivery-skills/fixtures/ui-contract-good.html tests/ai-delivery-skills/fixtures/ui-contract-bad.html tests/ai-delivery-skills/ui-contract-html-validator.test.sh
git commit -m "test: add failing HTML UI contract validator fixtures"
```

---

### Task 2: Implement the HTML v2 validator

**Files:**
- Create: `scripts/validate-ui-contract-html.py`
- Modify: `tests/ai-delivery-skills/ui-contract-html-validator.test.sh` only if command output needs refinement

**Interfaces:**
- Consumes: fixtures and test from Task 1.
- Produces:
  - CLI: `python3 scripts/validate-ui-contract-html.py <contract.html>`
  - success output: `OK: <path>`
  - failure output: one `FAIL <RULE>: <message>` per issue, then `INVALID: <path> (<n> issue(s))`
  - rules: `HTML`, `META`, `UNIT`, `DUPLICATE_ID`, `SOURCE_NODE`, `STATE`, `SYSTEM_UI`, `DELIVERY`, `ASSET`

- [ ] **Step 1: Implement parser and metadata validation**

Create `scripts/validate-ui-contract-html.py` with:
- standard-library `html.parser` plus `json` parsing;
- no new third-party dependency;
- require exactly one `<script id="ui-contract-meta" type="application/json">`;
- require `schema_version == 2`, `contract_id`, `source.requirement`, `source.design_file`, `source.root_node`;
- require `unit.id`, `unit.type in {"page", "modal", "shared-component"}`, `unit.source_node`, `unit.requirements`;
- reject multiple root units.

- [ ] **Step 2: Implement DOM validation**

In the same file, collect elements:
- require exactly one `<main data-ui-contract>`;
- require main `data-ui-unit-id` equals `meta.unit.id` and `data-ui-unit-type` equals `meta.unit.type`;
- reject duplicate `data-ui-id`;
- require every element with `data-ui-id` to have `data-figma-node` and `data-ui-kind`;
- reject kinds `status-bar`, `system-navigation`, `soft-keyboard`, `device-chrome`;
- require every `<template data-ui-state>` state to appear in `meta.states`;
- require at least one default state.

- [ ] **Step 3: Implement delivery and evidence validation**

- If `meta.delivery.status in {"implemented", "merged"}`, require `delivery.implemented` with `type`, `target`, `requirement`, `version`, and `status`.
- If `delivery.status` is `frozen`, `implemented` may be null.
- Require evidence notes for elements with `data-evidence="inferred"` inside `[data-ui-review-panel]`.
- Reject `data-src` assets without `data-ui-asset` metadata when present in fixture design.

- [ ] **Step 4: Run test to verify it passes**

Run: `bash tests/ai-delivery-skills/ui-contract-html-validator.test.sh`
Expected: `PASS: ui-contract-html-validator`

- [ ] **Step 5: Commit**

```bash
git add scripts/validate-ui-contract-html.py tests/ai-delivery-skills/fixtures/ui-contract-good.html tests/ai-delivery-skills/fixtures/ui-contract-bad.html tests/ai-delivery-skills/ui-contract-html-validator.test.sh
git commit -m "feat: add HTML UI contract v2 validator"
```

---

### Task 3: Replace ui-truth-mapping skill artifacts with HTML v2 templates and workflow

**Files:**
- Modify: `.agents/skills/ui-truth-mapping/SKILL.md`
- Modify: `.agents-zh/skills/ui-truth-mapping/SKILL-zh.md`
- Create: `.agents/skills/ui-truth-mapping/templates/ui-contract-template.html`
- Create: `.agents-zh/skills/ui-truth-mapping/templates/ui-contract-template.html`
- Delete: `.agents/skills/ui-truth-mapping/templates/ui-acceptance-contract-template.yaml`
- Delete: `.agents/skills/ui-truth-mapping/templates/section-map-template.json`
- Delete: `.agents/skills/ui-truth-mapping/fixtures/ui-acceptance-contract-good.yaml`
- Delete: `.agents/skills/ui-truth-mapping/fixtures/ui-acceptance-contract-bad.yaml`
- Delete: `.agents/skills/ui-truth-mapping/fixtures/section-map-good.json`
- Modify: `tests/ai-delivery-skills/ui-composition-guardrails.test.sh`

**Interfaces:**
- Consumes: validator command from Task 2.
- Produces: template path `.agents/skills/ui-truth-mapping/templates/ui-contract-template.html`; validator command referenced by the skill.

- [ ] **Step 1: Write failing structural tests**

Update `tests/ai-delivery-skills/ui-composition-guardrails.test.sh` to assert:
- `SKILL.md` contains `ui-contract.html`, `ui-contract-template.html`, incremental patch, and implementation lookup;
- `SKILL.md` does not instruct creating YAML or section-map;
- template exists and contains `id="ui-contract-meta"`, `<main data-ui-contract`, `data-ui-unit-id`, and `data-ui-review-panel`.

Run the targeted test and expect failures.

- [ ] **Step 2: Create the HTML contract template**

Create `.agents/skills/ui-truth-mapping/templates/ui-contract-template.html` with a full constrained skeleton:
- `ui-contract-meta` JSON with schema v2, source, unit, states, revision, delivery;
- CSS custom properties section;
- `<main data-ui-contract>`;
- unit root;
- state template;
- review details panel;
- comments explaining allowed fields and forbidden system UI/free-form structure.

Mirror it byte-for-byte into `.agents-zh/skills/ui-truth-mapping/templates/ui-contract-template.html`.

- [ ] **Step 3: Rewrite English skill workflow**

Rewrite `.agents/skills/ui-truth-mapping/SKILL.md` around:
1. locate requirement and candidate existing contract;
2. decide create vs incremental patch;
3. enumerate TemPad frames at parent/selection level;
4. get minimal evidence with `get_code` first and `get_structure` only for ambiguity;
5. copy HTML template verbatim;
6. generate or patch one-unit HTML;
7. browser-review layout and collapsible evidence;
8. run `python3 scripts/validate-ui-contract-html.py`;
9. after implementation, fill `delivery.implemented` and revalidate.

Keep old process principles that remain valid: one frame at a time, no cross-unit contamination, no invented visual truth, no system UI.

- [ ] **Step 4: Mirror Chinese skill**

Apply equivalent semantics to `.agents-zh/skills/ui-truth-mapping/SKILL-zh.md`.

- [ ] **Step 5: Remove obsolete YAML/section-map artifacts**

Delete the listed YAML/JSON templates and fixtures from `.agents/skills/ui-truth-mapping`; delete corresponding mirrored artifacts under `.agents-zh` if present.

- [ ] **Step 6: Run structural tests**

Run: `bash tests/ai-delivery-skills/ui-composition-guardrails.test.sh`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add .agents/skills/ui-truth-mapping .agents-zh/skills/ui-truth-mapping tests/ai-delivery-skills/ui-composition-guardrails.test.sh
git commit -m "feat: migrate ui truth mapping to HTML contract v2"
```

---

### Task 4: Migrate orchestrator, gates, hooks, and status validation to HTML v2

**Files:**
- Modify: `.agents/skills/ai-delivery-orchestrator/references/stage-ui-truth.md`
- Modify: `.agents/skills/ai-delivery-orchestrator/references/stage-design-and-speckit.md`
- Modify: `.agents/skills/ai-delivery-orchestrator/references/stage-implementation.md`
- Modify: `.agents-zh/skills/ai-delivery-orchestrator/references/stage-ui-truth.md`
- Modify: `.agents-zh/skills/ai-delivery-orchestrator/references/stage-design-and-speckit.md`
- Modify: `.agents-zh/skills/ai-delivery-orchestrator/references/stage-implementation.md`
- Modify: `scripts/validate-delivery-status.py`
- Modify: `scripts/reconcile-delivery.py`
- Modify: `scripts/hooks/validate-ui-contract.sh`
- Modify: `AGENTS.md`
- Modify: `.cursor/rules/ui-contract-gate.mdc`
- Modify: `.claude/rules/ui-contract-gate.md`
- Modify: `.ai-delivery/docs/guides/contract-gated-stage-checklists.md`
- Modify: `.ai-delivery/docs/guides/ai-delivery-any-repo-onboarding.md`
- Modify: `tests/ai-delivery-skills/ui-contract-validator.test.sh`

**Interfaces:**
- Consumes: `.agents/skills/ui-truth-mapping/templates/ui-contract-template.html`, `scripts/validate-ui-contract-html.py`.
- Produces: status validator recognizes `ui-contract.html`; hook command `bash scripts/hooks/validate-ui-contract.sh <path>` accepts HTML contracts; orchestrator implementation order derives from `meta.unit.type` and `meta.unit.dependencies`.

- [ ] **Step 1: Write failing gate tests**

Update `tests/ai-delivery-skills/ui-contract-validator.test.sh` so:
- v2 HTML contract passes through `scripts/validate-delivery-status.py` when status expects a frozen contract;
- missing `delivery.implemented` fails for delivered status;
- no test expects YAML or section-map.

Run and expect failure because status validator still targets YAML.

- [ ] **Step 2: Update status and reconcile scripts**

In `scripts/validate-delivery-status.py`:
- discover `ui-contract.html` per sub-requirement/unit directory;
- run `scripts/validate-ui-contract-html.py`;
- preserve existing status semantics and output format;
- pass unit metadata where dependency ordering is checked.

In `scripts/reconcile-delivery.py`:
- infer `ui_bearing` from `ui-contract.html`;
- stop inferring from `ui-acceptance-contract.yaml` / `section-map.json`.

- [ ] **Step 3: Update hook**

In `scripts/hooks/validate-ui-contract.sh`:
- trigger on `ui-contract.html`;
- call `python3 scripts/validate-ui-contract-html.py`;
- in bootstrapped repos call `python3 .ai-delivery/scripts/validate-ui-contract-html.py`;
- keep hook exit behavior unchanged.

- [ ] **Step 4: Update orchestrator references and gates**

Replace YAML/section-map wording with:
- output `ui-contract.html` per unit;
- implementation order from embedded `meta.unit.type` and dependencies: `shared-component → page → modal`;
- Spec Kit input is the HTML contract;
- visual acceptance compares implementation against the reviewed HTML and optional visual-regression report.

Update `AGENTS.md` and rule gates to reference the template and HTML validator only.

- [ ] **Step 5: Run targeted and full skill tests**

Run:
```bash
bash tests/ai-delivery-skills/ui-contract-validator.test.sh
bash tests/ai-delivery-skills/ui-contract-html-validator.test.sh
bash scripts/validate-project-ai-delivery-skills.sh
```
Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add .agents/skills/ai-delivery-orchestrator .agents-zh/skills/ai-delivery-orchestrator scripts/validate-delivery-status.py scripts/reconcile-delivery.py scripts/hooks/validate-ui-contract.sh AGENTS.md .cursor/rules/ui-contract-gate.mdc .claude/rules/ui-contract-gate.md .ai-delivery/docs/guides/contract-gated-stage-checklists.md .ai-delivery/docs/guides/ai-delivery-any-repo-onboarding.md tests/ai-delivery-skills/ui-contract-validator.test.sh
git commit -m "feat: enforce HTML UI contracts across delivery gates"
```

---

### Task 5: Update bootstrap managed assets and Go tests

**Files:**
- Modify: `managedassets.go`
- Modify: `managedassets_test.go`
- Modify: any embedded manifest or generation source that lists `validate-ui-contract.py`, YAML templates, YAML fixtures, or the old hook path

**Interfaces:**
- Consumes: Task 2 validator, Task 3 template, Task 4 hook and scripts.
- Produces: bootstrapped repos receive `.ai-delivery/scripts/validate-ui-contract-html.py`, HTML hook, HTML template, and gate docs; they do not receive obsolete YAML assets.

- [ ] **Step 1: Write failing managed-asset tests**

Update `managedassets_test.go` to assert:
- embedded asset list contains `scripts/validate-ui-contract-html.py`;
- embedded asset list contains `.agents/skills/ui-truth-mapping/templates/ui-contract-template.html`;
- obsolete YAML template and section-map paths are absent;
- restored gate content references `ui-contract.html`.

Run `go test ./...` and expect failure.

- [ ] **Step 2: Update managed assets**

Update `managedassets.go` and the manifest source to embed the new HTML validator/template/hook/rule content and remove old YAML artifacts.

- [ ] **Step 3: Run Go tests**

Run: `go test ./...`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add managedassets.go managedassets_test.go managed_manifest.go
git commit -m "feat: bootstrap HTML UI contract assets"
```

---

### Task 6: End-to-end verification and cleanup

**Files:**
- Modify: `README.md`, `README.zh-CN.md` only if they mention YAML contract outputs
- Modify: any remaining docs found by search
- Do not modify: `docs/superpowers/specs/2026-08-03-ui-truth-mapping-html-contract-v2-design.md` unless a discovered implementation constraint changes the approved design

**Interfaces:**
- Consumes: all prior tasks.
- Produces: clean working tree except approved spec/plan docs and implementation commits; full test suite PASS.

- [ ] **Step 1: Search for obsolete references**

Run:
```bash
rg "ui-acceptance-contract|section-map\\.json|section-map-template|validate-ui-contract\\.py" .
```

Expected: only historical specs/plans, deleted-file references in git internals if any, or explicitly documented migration notes remain. Update active docs/scripts/skills found by the search.

- [ ] **Step 2: Run all tests**

Run:
```bash
go test ./...
bash scripts/validate-project-ai-delivery-skills.sh
bash tests/ai-delivery-skills/ui-contract-validator.test.sh
bash tests/ai-delivery-skills/ui-contract-html-validator.test.sh
bash tests/ai-delivery-skills/ui-composition-guardrails.test.sh
```
Expected: all PASS.

- [ ] **Step 3: Verify no accidental artifacts**

Run:
```bash
git status --short
```
Expected: no `.superpowers/` staged; no deleted YAML assets reintroduced; only intended docs/tests/code modified.

- [ ] **Step 4: Final commit**

```bash
git add README.md README.zh-CN.md .ai-delivery docs scripts tests .agents .agents-zh
git commit -m "chore: complete HTML UI contract v2 migration"
```
Only include files actually modified by this task.

---

## Self-Review

- Spec coverage: Task 1–2 cover validator and gates; Task 3 covers HTML structure and skill workflow; Task 4 covers orchestrator/status/hook; Task 5 covers bootstrap; Task 6 covers full verification.
- No placeholders: each task has exact files, commands, expected outcomes, and implementation boundaries.
- Interface consistency: validator path is consistently `scripts/validate-ui-contract-html.py`; template path is consistently `.agents/skills/ui-truth-mapping/templates/ui-contract-template.html`; contract filename is consistently `ui-contract.html`.
