# UI Truth Mapping: Incremental Contract Construction

## Problem

The current ui-truth-mapping skill gathers ALL Figma evidence for a unit (all state frames + full component tree) in one batch, then freezes the complete YAML contract in a single pass. When context is large, the LLM hallucinates, misses details, and produces incomplete contracts.

## Solution

Replace single-pass contract construction with **three incremental passes**, each processing frames **one at a time** within the same subagent. Different units still build their contracts in parallel via separate subagents.

## Architecture

```
ai-delivery-orchestrator (Stage 2)
  │
  ├─ Analyze Figma → section-map.json (identify units: pages, modals, shared-shells)
  │
  ├─ Dispatch per-unit subagents in PARALLEL
  │   │
  │   └─ [Unit Subagent] — same process, three sequential passes
  │        │
  │        ├─ Pass 1 (Skeleton):  For each frame → get_structure() → append component nodes
  │        ├─ Pass 2 (Layout):   For each frame → get_code()     → fill box/anchor/padding/layout
  │        └─ Pass 3 (Style):    For each frame → get_code()     → fill background/content/interaction
  │
  └─ All units complete → Stage 4 subagent (Final Contract Review)
```

## Three Passes

### Pass 1 — Skeleton Layer

| Aspect | Detail |
|--------|--------|
| Figma queries | `get_structure(node_id)` — once per frame, structure only |
| Fields filled | `version`, `contract_id`, `source` (partial), `states`, `background` (page-level), `regions[].children[]` (id/type/name/source_node/visible_when) |
| Fields skipped | anchor, layout, box, background (component-level), content, interaction, description — keep template placeholders |
| Output | Complete component tree skeleton with id/type/name/source_node/visible_when links |

Rules:
- First frame creates component nodes in regions.children
- Subsequent same-page state frames merge into existing tree via visible_when + states
- Component hierarchy derived from Figma parent-child structure
- Do NOT use get_code — structure-level queries only

### Pass 2 — Layout Layer

| Aspect | Detail |
|--------|--------|
| Figma queries | `get_code(frame_node_id)` — once per frame, code-level |
| Fields filled | `anchor` (4-direction), `layout` (direction/align/gap), `box` (width/height/padding 4-direction) |
| Fields skipped | background (component-level), content, interaction, description |
| Input | YAML from Pass 1, read-only for source_node lookup |

Rules:
- Read current YAML, find components by source_node in this frame
- Call get_code for the frame, extract layout data per component
- anchor: exactly 4 entries (start/end/top/bottom), each with to/direction/offset/note
- Width/height: prefer auto > fill > "<Npx>"
- Padding: explicit 4 values, use 0 when flush
- Do NOT write description even for fixed px — Pass 3 handles it
- Do not modify any Pass 1 fields

### Pass 3 — Style/Content Layer

| Aspect | Detail |
|--------|--------|
| Figma queries | `get_code(frame_node_id)` — once per frame, code-level (may reuse Pass 2 cache) |
| Fields filled | `background` (component-level: color/border/shadow/opacity), `content` (exactly one of text+font/icon/image), `interaction` (on/action/note), `description` (when fixed px used) |
| Fields skipped | anchor, layout, box — Pass 2 fields are read-only |
| Output | Complete YAML, all fields populated |

Rules:
- content: exactly one slot per component (text+font, icon, or image)
- description: required when box.width or box.height uses "<Npx>"
- Do not modify any Pass 1 or Pass 2 fields

## Per-Frame Iteration

Within each pass, frames are processed one at a time, not batched:

```
Pass N (unit with 3 frames: default, loading, empty):

  Step 1: Read current YAML state
  
  Step 2: Process Frame "default"
    → get_structure/get_code(frame_default_id)
    → Write/update fields for this layer
  
  Step 3: Process Frame "loading"
    → get_structure/get_code(frame_loading_id)
    → Merge into YAML (new components appended, existing get states)
  
  Step 4: Process Frame "empty"
    → Same merge logic
```

This keeps context minimal per Figma query, reducing hallucination risk.

## Stage 4: Final Contract Review

Runs after all three passes complete, still as a separate subagent. Review checklist reorganized to match the three-layer structure:

**Skeleton quality (Pass 1):**
- S1: Component tree completeness — every frame's source_node has a tree node
- S2: visible_when coverage — all non-default-state components have conditions
- S3: states list matches declared frames in section-map
- S4: source metadata complete

**Layout quality (Pass 2):**
- L1: anchor 4-direction completeness on every component
- L2: padding 4-direction completeness on every component
- L3: width/height prefer auto/fill; fixed px must have description
- L4: gap/align consistent with Figma auto-layout

**Style/Content quality (Pass 3):**
- C1: every component has exactly one content slot
- C2: background values source-traceable
- C3: interaction has complete on/action when non-null
- C4: fixed px description filled and justified

**Global checks:**
- G1: Safe areas and system UI excluded
- G2: Keyboard adaptation considered

## Skill File Changes

Stages reorganized from 5 to 4:

| Old | New |
|-----|-----|
| Stage 1: Confirm upstream | Stage 1: Confirm upstream (unchanged) |
| Stage 2: Analyze sections and split | Stage 2: Analyze sections and split (unchanged) |
| Stage 3: Gather design evidence | Stage 3: Three-Pass Incremental Contract Construction (merged) |
| Stage 4: Freeze YAML contract | *(merged into Stage 3)* |
| Stage 5: Final Contract Review | Stage 4: Final Contract Review (checklist reorganized) |

section-map.json extended to carry per-frame node IDs for iteration:

```json
{
  "units": [
    {
      "id": "contacts-directory",
      "type": "page",
      "frames": [
        {"node_id": "1:100", "state_id": "default"},
        {"node_id": "1:101", "state_id": "loading"},
        {"node_id": "1:102", "state_id": "empty"}
      ]
    }
  ]
}
```

## Subagent Prompt Structure

Each unit subagent receives one prompt containing all three pass instructions. The prompt defines field ownership explicitly per pass — no template annotations needed.

Key rules repeated in each pass:
- "FIELDS YOU FILL" — explicit field list
- "DO NOT TOUCH" — explicit exclusion list
- "For EACH frame, one at a time" — per-frame iteration enforcement
- Pass 1: structure-only queries
- Pass 2/3: code-level queries, read previous pass fields only

## Cache Strategy

Cache granularity refined to support per-frame reuse across passes:

```
.ai-delivery/figma-cache/<file-key>/
  ├── structure/<node-id>.json    # Pass 1 cache
  └── code/<node-id>.json         # Pass 2+3 shared cache
```

Pass 2 and Pass 3 share the same get_code cache — Pass 2 fetches and caches, Pass 3 reads from cache.

## Template

The YAML contract template is unchanged. Field ownership is defined in subagent prompts, not in template annotations, keeping a single source of truth for the contract schema.

## Parallel Execution

Unit isolation is preserved. Different units' subagents run in parallel as before. The three-pass serialization only applies within a single unit's subagent, keeping the cross-unit parallelism benefit.

## Acceptance Criteria

1. A unit subagent completes all three passes without touching fields outside the current pass
2. Every component has complete anchor (4-direction) and padding (4-direction)
3. Every component has exactly one content slot
4. Stage 4 review passes all 14 checks (S1-4, L1-4, C1-4, G1-2)
5. Contract is identical in structure to the current single-pass output — same schema, same fields, different construction process
