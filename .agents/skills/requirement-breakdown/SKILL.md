---
name: requirement-breakdown
description: Use when a requirement document needs to be split into independently trackable sub-requirements with source-preserving artifacts.
---

# Requirement Breakdown

Split a top-level requirement and every explicitly supplied supporting artifact into sub-requirements. Each sub-requirement references source sections by a stable locator (line range, table row/cell range, sheet range, or equivalent; not verbatim copy) and adds normalized statements.

This skill does one thing: reads requirements → produces sub-requirements. It does not manage state, decide what runs next, or handle blockers.

## Input

A requirement document (path or pasted text) plus every explicitly supplied supporting artifact, such as tables, spreadsheets, API descriptions, analytics maps, copy decks, diagrams, or design notes.

## Output

```
<output-dir>/
├── breakdown-summary.md     # input sources, sub-requirement index, open questions
├── global-rules.md          # cross-cutting rules only
├── dependency-graph.json    # acyclic DAG (depends_on only — no blocks, managed by orchestrator)
└── <subreq-dir>/
    └── requirement-slice.md # source_ref line ranges + normalized statements
```

## Workflow

### 1. Inventory sources
- Read every supplied source. Do not classify or down-rank a source from its filename, extension, folder, or labels such as `draft`, `pending`, or `to confirm`; inspect its actual columns, notes, annotations, and structure first.
- Identify every semantic role carried by each source. A copy/localization table may also define state order, transitions, triggers, branches, convergence, side effects, or acceptance behavior; an API file may also constrain domain state or error behavior.
- Capture stable source locators for every meaningful section or row group. Treat uncertain content as evidence with unresolved authority, not as omitted input: normalize the established facts, mark the uncertain decision `unknown`, and surface the material question.
- Identify which sections belong to which sub-requirement boundary.

### 2. Decide boundaries
Split by delivery meaning. A sub-requirement should satisfy at least one of:
- it can be independently developed, integrated, tested, or accepted
- it owns one coherent dependency or capability surface

Valid types: `Global Rule`, `Shared Foundation`, `Shared Component`, `Feature Module`, `Cross-Feature Infrastructure`.

Rules:
- Extract shared foundations and cross-feature infrastructure before feature modules.
- Cross-cutting rules affecting 2+ sub-requirements go into `global-rules.md`, not duplicated.
- Do not over-split for implementation convenience.

### 3. Write artifacts
- **Copy template first.** For each `requirement-slice.md`, copy `templates/requirement-slice-template.md` to the output path, then fill in values. Do not regenerate the structure from memory — the template's section keys, field names, and ordering are the source of truth. Localize all human-readable headings, labels, prose, and necessary comments into the user's current conversation language, then remove the `ai-delivery-template-language` instruction comment. Preserve machine-readable keys, enum values, IDs, paths, commands, and code symbols exactly; never add, remove, or rename sections or fields.
- `requirement-slice.md` references source document line ranges (sections). Do NOT copy the original text verbatim — that wastes tokens.
- `dependency-graph.json` must be acyclic. Only lists `depends_on` — `blocks` is managed by the orchestrator, not this skill.

### 4. Re-audit
- Re-read every primary and supporting source. Verify no section, table row group, note, state transition, branch, side effect, or acceptance signal was silently dropped.
- In `breakdown-summary.md`, account for every meaningful source unit as assigned to a slice, promoted to a global rule, recorded as an open question, or explicitly excluded with a reason. A source title suggesting copy, localization, draft status, or another narrow purpose is never an exclusion reason.
- Verify every acceptance signal traces back to a source reference.
- Verify the dependency graph is acyclic and global rules are not duplicated.

## Source-Reference Pattern

```
source_ref: "original-requirement.md#L14-L22, L30-L35"
  — line ranges in the original document that this slice covers.
  — multiple non-contiguous ranges are listed, joined by commas.
  — each range represents a logical section/paragraph, not random lines.

Normalized Statement:
  - statement: This slice covers project-name editing in Settings.
  - source_basis: original-requirement.md#L14-L22
  - normalization_type: wording cleanup
```

Do NOT copy the original text into the slice. The `source_ref` is sufficient — downstream tools and humans can open the original document.

For tabular sources, use the most stable available locator, for example `source.csv#rows=12-18` or `source.xlsx#sheet=Flow&range=A12:H18`. Preserve row-level semantics when different rows encode different states or transitions; do not collapse them into a generic “copy resource” statement.

## Hard Boundary

- Do not split requirements without source line-range coverage for every slice.
- Do not infer a source's semantic scope from its filename or document category. Draft or pending status requires an explicit uncertainty record; it never authorizes silent omission.
- Do not defer non-visual state machines, transitions, branching, persistence, side effects, or protocol behavior merely because visual design evidence is unavailable. Allocate them to the owning non-visual slice or record the unresolved dependency explicitly.
- Do not duplicate cross-cutting rules across slices — they belong in `global-rules.md`.
- Do not generate `requirement-slice.md` from memory. Locate `templates/requirement-slice-template.md`, copy its structure to the output path, then fill in values. Preserve all section keys, field names, and ordering. Localize human-readable content into the user's current conversation language and remove only the `ai-delivery-template-language` instruction comment; preserve the remaining semantic HTML comments. Only change values — never add, remove, or rename template sections or fields.
- Do not produce circular dependencies. The dependency graph must be a DAG.
- Do not manage `blocks` — that is the orchestrator's responsibility.
