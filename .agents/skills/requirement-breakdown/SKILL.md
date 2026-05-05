---
name: requirement-breakdown
description: Use when a requirement document needs to be split into independently trackable sub-requirements with source-preserving artifacts.
---

# Requirement Breakdown

Split a top-level requirement document into sub-requirements. Each sub-requirement references source sections by line range (not verbatim copy) and adds normalized statements.

This skill does one thing: reads requirements → produces sub-requirements. It does not manage state, decide what runs next, or handle blockers.

## Input

A requirement document (path or pasted text).

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
- Read the requirement document. Capture line numbers for every section.
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
- `requirement-slice.md` references source document line ranges (sections). Do NOT copy the original text verbatim — that wastes tokens.
- `dependency-graph.json` must be acyclic. Only lists `depends_on` — `blocks` is managed by the orchestrator, not this skill.

### 4. Re-audit
- Re-read the original requirement. Verify no section was silently dropped.
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
