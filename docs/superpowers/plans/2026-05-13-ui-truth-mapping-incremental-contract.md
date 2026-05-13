# UI Truth Mapping: Incremental Contract Construction — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace single-pass contract construction with three incremental passes (skeleton → layout → style/content), each processing frames one at a time to reduce hallucination and missed details.

**Architecture:** Modify the ui-truth-mapping SKILL.md to merge old Stages 3+4 into a single "Three-Pass Incremental Contract Construction" stage, renumber Stage 5→4, and reorganize the review checklist. The YAML template and section-map template are unchanged. The Chinese SKILL-zh.md receives identical mirrored changes.

**Tech Stack:** Markdown skill definitions, YAML contract templates, JSON section maps

---

### Task 1: Add per-frame iteration and field-ownership boundaries to Hard Boundary section

**Files:**
- Modify: `.agents/skills/ui-truth-mapping/SKILL.md` (after line 63 — last Hard Boundary rule)
- Modify: `.agents-zh/skills/ui-truth-mapping/SKILL-zh.md` (after line 59 — last Hard Boundary rule)

- [ ] **Step 1: Add two new Hard Boundary rules to SKILL.md**

Insert after the existing rule ending with `explicit anchor entry's note field when auto` (line 63):

```
- Within a per-unit subagent, process frames ONE AT A TIME — never batch all frames into a single Figma query. Each pass iterates frame by frame: query one frame, fill its fields, move to the next. This keeps context focused and prevents missed details.
- Each of the three passes fills ONLY its assigned fields. Never touch fields owned by a different pass. Pass 1 owns id/type/name/source_node/visible_when/states. Pass 2 owns anchor/layout/box. Pass 3 owns background/content/interaction/description.
```

Edit command:
```
old: offset: auto when the parent layout (e.g. a list with multiple items) controls positioning — when auto, document how the offset is calculated in the anchor entry's note field.

new: offset: auto when the parent layout (e.g. a list with multiple items) controls positioning — when auto, document how the offset is calculated in the anchor entry's note field.
- Within a per-unit subagent, process frames ONE AT A TIME — never batch all frames into a single Figma query. Each pass iterates frame by frame: query one frame, fill its fields, move to the next. This keeps context focused and prevents missed details.
- Each of the three passes fills ONLY its assigned fields. Never touch fields owned by a different pass. Pass 1 owns id/type/name/source_node/visible_when/states. Pass 2 owns anchor/layout/box. Pass 3 owns background/content/interaction/description.
```

- [ ] **Step 2: Verify with grep**

Run: `grep -n "process frames ONE AT A TIME" .agents/skills/ui-truth-mapping/SKILL.md`
Expected: One matching line.

Run: `grep -n "three passes fills ONLY" .agents/skills/ui-truth-mapping/SKILL.md`
Expected: One matching line.

- [ ] **Step 3: Add the same rules to SKILL-zh.md**

Insert after the last Hard Boundary rule (line 59):

```
- 在逐单元子代理内部，一次只处理一个帧 — 永远不要将所有帧批量塞入单个 Figma 查询。每一层逐帧迭代：查询一个帧，填充该帧的字段，然后处理下一个。保持上下文聚焦，防止细节遗漏。
- 三层各自只填充其分配的字段。绝不触碰其他层拥有的字段。Pass 1 拥有 id/type/name/source_node/visible_when/states。Pass 2 拥有 anchor/layout/box。Pass 3 拥有 background/content/interaction/description。
```

Edit command: Similar to Step 1 but against SKILL-zh.md with Chinese text.

- [ ] **Step 4: Verify SKILL-zh.md changes**

Run: `grep -n "一次只处理一个帧" .agents-zh/skills/ui-truth-mapping/SKILL-zh.md`
Expected: One matching line.

- [ ] **Step 5: Commit**

```bash
git add .agents/skills/ui-truth-mapping/SKILL.md .agents-zh/skills/ui-truth-mapping/SKILL-zh.md
git commit -m "feat: add per-frame iteration and field-ownership rules to Hard Boundary"
```

---

### Task 2: Update Stage 2 subagent dispatch with frame iteration guidance

**Files:**
- Modify: `.agents/skills/ui-truth-mapping/SKILL.md` (the subagent dispatch paragraph, line ~96)
- Modify: `.agents-zh/skills/ui-truth-mapping/SKILL-zh.md` (the subagent dispatch paragraph, line ~92)

- [ ] **Step 1: Update the dispatch paragraph in SKILL.md**

Change from:
```
**After section-map is written — dispatch per-unit subagents.** For each independent unit (page, modal, shared-shell) in the section-map, spawn a subagent. Each subagent receives only its unit's frames (with source_node ids), the requirement-slice, the design source locator, and the template path. It independently executes Steps 3+4 for its assigned unit — gathering evidence only for its frames, then freezing one YAML contract. Dispatch all units in parallel. The main session does not gather evidence or freeze YAML; it only dispatches, collects results, then runs Step 5 review.
```

Change to:
```
**After section-map is written — dispatch per-unit subagents.** For each independent unit (page, modal, shared-shell) in the section-map, spawn a subagent. Each subagent receives only its unit's frames (each with a `source_node` for Figma queries and a `state_type` for the YAML state id), the requirement-slice, the design source locator, and the template path. It independently executes Stage 3 for its assigned unit — running three incremental passes (skeleton → layout → style/content), each pass processing frames ONE AT A TIME, and editing a single YAML file. Dispatch all units in parallel. The main session does not gather evidence or freeze YAML; it only dispatches, collects results, then runs Stage 4 review.
```

- [ ] **Step 2: Verify the paragraph**

Run: `grep -n "three incremental passes" .agents/skills/ui-truth-mapping/SKILL.md`
Expected: One matching line.

Run: `grep -n "ONE AT A TIME" .agents/skills/ui-truth-mapping/SKILL.md`
Expected: Two matching lines (Hard Boundary + Stage 2 dispatch).

- [ ] **Step 3: Update SKILL-zh.md dispatch paragraph**

Change from:
```
**section-map 写入后 — 派发逐单元子代理。** 对于 section-map 中的每个独立单元（page、modal、shared-shell），派发一个子代理。每个子代理仅接收其所属单元的帧（含 source_node ID）、需求切片、设计源定位符和模板路径。子代理为其分配的单元独立执行步骤 3+4 — 仅为其帧收集证据，然后冻结一份 YAML 契约。所有单元并行派发。主会话不收集证据也不冻结 YAML；仅负责派发、收集结果，然后运行步骤 5 的审校。
```

Change to:
```
**section-map 写入后 — 派发逐单元子代理。** 对于 section-map 中的每个独立单元（page、modal、shared-shell），派发一个子代理。每个子代理仅接收其所属单元的帧（每个帧含用于 Figma 查询的 `source_node` 和用于 YAML state id 的 `state_type`）、需求切片、设计源定位符和模板路径。子代理为其分配的单元独立执行阶段 3 — 运行三层增量编辑（骨架 → 布局 → 样式内容），每层一次只处理一个帧，编辑同一个 YAML 文件。所有单元并行派发。主会话不收集证据也不冻结 YAML；仅负责派发、收集结果，然后运行阶段 4 审校。
```

- [ ] **Step 4: Verify SKILL-zh.md**

Run: `grep -n "三层增量编辑" .agents-zh/skills/ui-truth-mapping/SKILL-zh.md`
Expected: One matching line.

- [ ] **Step 5: Commit**

```bash
git add .agents/skills/ui-truth-mapping/SKILL.md .agents-zh/skills/ui-truth-mapping/SKILL-zh.md
git commit -m "feat: update Stage 2 dispatch with three-pass iteration guidance"
```

---

### Task 3: Replace old Stages 3+4 with new Stage 3 (Three-Pass Incremental Contract Construction)

**Files:**
- Modify: `.agents/skills/ui-truth-mapping/SKILL.md` (replace lines 100-168)

This is the largest change. The old Stage 3 (Gather design evidence) and Stage 4 (Freeze YAML contract) are replaced with a single Stage 3 that defines the three-pass execution model.

- [ ] **Step 1: Replace old Stages 3+4 with new Stage 3**

Old text starts at `### 3. Gather design evidence *(runs inside per-unit subagent)*` (line 100) and continues through the end of old Stage 4 at line 168 (`- **有 font.size...**` rule). Replace with:

```
### 3. Three-Pass Incremental Contract Construction *(runs inside per-unit subagent)*

This step runs inside each per-unit subagent. The subagent has access only to its assigned unit's frames and evidence — no cross-contamination from other units.

**Execution model:** Three sequential passes over the same YAML file. Each pass processes frames ONE AT A TIME — never batch all frames into a single Figma query. Each pass fills ONLY its assigned fields and does not touch fields owned by other passes.

**First, copy the template.** Locate `templates/ui-acceptance-contract-template.yaml` and copy it verbatim to the output path for this unit. All three passes edit this single file.

#### Pass 1 — Skeleton Layer

**Purpose:** Build the component tree structure and state declarations.

**Figma queries:** `get_structure(frame_source_node)` — once per frame, structure-level only. Do NOT use `get_code` in this pass.

**FIELDS YOU FILL:**
- `version`, `contract_id`
- `source` — requirement filename, figma file key, root node id, cache path
- `states` — one entry per frame: `id` (from frame's `state_type` classification) and `source_node`
- `background` — page-level color only, from the default/idle frame
- `regions[].children[]` — component tree skeleton: `id`, `type`, `name`, `source_node`, `visible_when`, recursive `children`

**DO NOT TOUCH:** `anchor`, `layout`, `box` (width/height/padding), `background` (component-level), `content` (text/icon/image/font), `interaction`, `description`. Leave these as template defaults (`null`, `{}`, `[]`, `0`).

**Per-frame iteration:**

For EACH frame in the unit's frame list, one at a time:

1. Call `get_structure(<frame-source-node>)`.
2. Extract the component hierarchy — component types, nesting relationships, visible elements.
3. **First frame processed:** Create all component nodes in `regions[].children[]`. Fill `id`, `type`, `name`, `source_node`. Set `visible_when: null` (default state components are always visible). Recursively populate `children` using the Figma parent-child structure.
4. **Subsequent frames:** For each component found in this frame:
   - If a component with the same `source_node` already exists in the tree → it is the same component in a different state. Do NOT create a duplicate. Set or refine the `visible_when` condition if it is state-specific.
   - If a component has a new `source_node` not yet in the tree → it is state-specific content. Append it to the appropriate parent's `children` with `visible_when` set to the semantic condition that makes it appear.
5. Add the frame's state entry to the `states` list at the top of the YAML — one `id` + `source_node` per frame.

**Merging rules across states:**
- Components present in all states: use the default/idle frame's `source_node`, `visible_when: null`.
- Components present only in some states: use a frame where they ARE visible as `source_node`, set `visible_when` to the semantic condition.
- Components that differ only in style between states: one component entry, style diffs go into `states` — filled in Pass 3.
- Never create two component entries with the same `id`.

**After Pass 1:** The YAML has a complete `states` list and a complete component tree with `id`, `type`, `name`, `source_node`, `visible_when`. All other fields are template defaults.

#### Pass 2 — Layout Layer

**Purpose:** Fill positioning, sizing, and layout for every component.

**Figma queries:** `get_code(frame_source_node)` — once per frame, code-level. Read the YAML from Pass 1 to find components by `source_node`.

**FIELDS YOU FILL:**
- `anchor` — exactly 4 entries per component: `start`, `end`, `top`, `bottom`. Each has:
  - `to`: reference component id, `screen_start`, `screen_end`, `screen_top`, `screen_bottom`
  - `direction`: which edge of the reference to attach to
  - `offset`: `<Npx>` gap from the reference edge, or `auto` when parent layout controls position
  - `note`: required when `offset` is `auto` — explain how the offset is calculated
- `layout` — `direction` (vertical/horizontal/none), `align`, `gap`
- `box` — `width` (auto/fill/<Npx>), `height` (auto/<Npx>), `padding` (all 4 required: top/right/bottom/left; use `0` when flush)

**DO NOT TOUCH:** All Pass 1 fields (`id`, `type`, `name`, `source_node`, `visible_when`, `states`). Also: `background` (component-level), `content` (text/icon/image/font), `interaction`, `description`. Do NOT write `description` here — Pass 3 handles it even for fixed px.

**Per-frame iteration:**

For EACH frame in the unit's frame list, one at a time:

1. Read the current YAML file. Find all components whose `source_node` belongs to this frame.
2. Call `get_code(<frame-source-node>)` for precise positioning data.
3. For each component found in this frame, extract and fill:
   - **anchor**: Compute all 4 anchor entries. Offset from reference bottom edge formula: `offset = child.topY − (ref.topY + ref.height)`. Use `0px` for flush attachment. Use `auto` when the parent layout (e.g. a list) controls positioning — add a `note` explaining the calculation.
   - **layout**: Extract direction, alignment, and gap from Figma auto-layout or manual positioning data.
   - **box**: `width` prefer `auto` > `fill` > `<Npx>`. `height` prefer `auto` > `<Npx>`. `padding` all 4 directions from measured insets; use `0` where the design shows flush edges.
4. Move to the next frame. Repeat until all frames processed.

**After Pass 2:** Every component has complete anchor, layout, and box. `background` (component-level), `content`, `interaction`, and `description` remain as template defaults.

#### Pass 3 — Style/Content Layer

**Purpose:** Fill visual styling, content, and interactions for every component.

**Figma queries:** `get_code(frame_source_node)` — once per frame, code-level. May reuse cached data from Pass 2 (same `get_code` query). Read the YAML from Pass 2 to find components.

**FIELDS YOU FILL:**
- `background` — component-level: `color`, `border` (radius/width/color), `shadow`, `opacity`
- `content` — exactly ONE slot populated per component:
  - Text components: `text` (visible text content) + `font` (family, size, weight, color, height, align)
  - Icon components: `icon` (src — asset filename, size — display size)
  - Image components: `image` (src, width, height, fit)
- `interaction` — `on` (click/long-press/none), `action`, `note`
- `states` — per-state diffs from default. Component-state keys (e.g. `selected`, `active`, `disabled`), each a partial component diff. Example: `{ selected: { background: { border: { color: "#41B8F4" } } } }`.
- `description` — required when `box.width` or `box.height` uses fixed `<Npx>`; explain why `auto` was not applicable (e.g. "icon baseline size", "touch target minimum").

**DO NOT TOUCH:** All Pass 1 fields, all Pass 2 fields (`anchor`, `layout`, `box`). DO NOT modify component tree structure, add/remove nodes, or change `source_node` values. DO NOT change `visible_when` conditions.

**Per-frame iteration:**

For EACH frame in the unit's frame list, one at a time:

1. Read the current YAML file. Find all components whose `source_node` belongs to this frame.
2. Call `get_code(<frame-source-node>)` — reuse cached results from Pass 2 if available in `.ai-delivery/figma-cache/<file-key>/code/<node-id>.json`; fetch if not cached.
3. For each component in this frame, extract and fill:
   - **background**: Color fill, border styling, shadow, opacity.
   - **content**: Determine content type from the Figma node — text node → `text`+`font`; vector/icon node → `icon`; image fill node → `image`. Populate exactly one slot.
   - **interaction**: If the component is interactive (has click/long-press behavior in the design), fill `on`, `action`, and `note`.
   - **states**: If this component has style variations across states identified in Pass 1, write the per-state diffs. Each diff contains only the changed properties from the component's default (Pass 3) values.
   - **description**: If `box.width` or `box.height` uses fixed `<Npx>`, write a brief justification.
4. Move to the next frame. Repeat until all frames processed.

**After Pass 3:** The YAML contract is COMPLETE. All fields are populated with source-backed values.

**After all three passes:** The subagent returns the completed `ui-acceptance-contract.yaml` to the main session. The main session collects all unit contracts and proceeds to Stage 4.
```

- [ ] **Step 2: Verify the new Stage 3 structure**

Run: `grep -n "Pass 1 — Skeleton Layer" .agents/skills/ui-truth-mapping/SKILL.md`
Expected: One match.

Run: `grep -n "Pass 2 — Layout Layer" .agents/skills/ui-truth-mapping/SKILL.md`
Expected: One match.

Run: `grep -n "Pass 3 — Style/Content Layer" .agents/skills/ui-truth-mapping/SKILL.md`
Expected: One match.

Run: `grep -n "DO NOT TOUCH" .agents/skills/ui-truth-mapping/SKILL.md`
Expected: 3 matches (one per pass).

- [ ] **Step 3: Check that old Stage references are gone**

Run: `grep -n "Gather design evidence" .agents/skills/ui-truth-mapping/SKILL.md && echo "FAIL: old text still present" || echo "PASS"`
Expected: PASS (no matches).

Run: `grep -n "Freeze YAML contract" .agents/skills/ui-truth-mapping/SKILL.md && echo "FAIL: old text still present" || echo "PASS"`
Expected: PASS (no matches).

- [ ] **Step 4: Commit**

```bash
git add .agents/skills/ui-truth-mapping/SKILL.md
git commit -m "feat: replace old Stages 3+4 with three-pass incremental contract construction"
```

---

### Task 4: Reorganize Stage 5 → Stage 4 with layered review checklist

**Files:**
- Modify: `.agents/skills/ui-truth-mapping/SKILL.md` (old Stage 5, lines ~173-218 after Task 3's insertion)

- [ ] **Step 1: Replace old Stage 5 content with reorganized Stage 4**

Old text starts at `### 5. Final Contract Review` and continues through the end of the review content (the line before `## Component Type Vocabulary`).

Replace with:

```
### 4. Final Contract Review

**Mandatory — run after every YAML freeze.** Review EVERY contract produced (page, modal, shared-shell). Do not skip any unit. Use a subagent for clean isolation — the subagent receives all contracts plus `section-map.json` and returns optimized contracts.

This review normalizes layout semantics and sizing only. It does NOT add or remove source-backed components, states, `visible_when` conditions, or `source_node` values.

**Review order (follow strictly, organized by pass layer):**

**Skeleton quality (Pass 1 output):**

**S1. Component tree completeness**
- Every frame's `source_node` enumerated in `section-map.json` must have at least one corresponding component node in the tree.
- No frame left without representation.

**S2. visible_when coverage**
- All non-default state components must have a `visible_when` condition.
- Conditions use semantic language (e.g. "input is filled"), not mechanical state-ID checks.

**S3. states list consistency**
- The `states` list in the YAML must match the frames declared in `section-map.json` — same count, each state has `id` + `source_node`.

**S4. source metadata completeness**
- `source.requirement`, `source.design_file`, `source.root_node`, `source.cache` are all populated.

**Layout quality (Pass 2 output):**

**L1. anchor 4-direction completeness**
- Every component has all 4 anchor entries (`start`, `end`, `top`, `bottom`).
- Each entry has explicit `to`, `direction`, and `offset` — no nulls, no empty strings.
- `offset: "0px"` for flush attachment; `offset: "auto"` must have a `note` explaining the calculation.

**L2. padding 4-direction completeness**
- Every component's `padding` has explicit values for all 4 directions (`top`, `right`, `bottom`, `left`).
- Use `0` where design shows flush edges — never leave a padding field `null` or omitted.

**L3. width/height convergence**
- Text, labels, descriptions → `width: "auto"`, `height: "auto"`.
- Cards, rows spanning available width → `width: "fill"`.
- **fill detection rule**: if a component's px width equals (parent_width − symmetrical horizontal padding), use `fill`, not fixed px.
- Fixed px kept only for: icons, avatars, minimum touch targets (≥44px), modal widths with explicit intent.

**L4. gap/align consistency**
- `layout.gap` and `layout.align` values are consistent with the Figma auto-layout data.

**Style/content quality (Pass 3 output):**

**C1. content slot — exactly one**
- Every leaf component has exactly one content slot populated: `text`+`font`, `icon`, or `image`.
- Empty containers with no visible children, no text, no icons, no images → should not exist in the tree.

**C2. background source traceability**
- `background.color`, `border`, `shadow`, `opacity` values are traceable to Figma fill/stroke/effect data.
- No invented colors or effects.

**C3. interaction completeness**
- Components with `interaction.on` set must have a corresponding `action` and `note` when non-trivial.

**C4. fixed px justification**
- Every component that retains a fixed `width` or `height` px value must have a `description` explaining why `auto` was not applicable.

**Global checks:**

**G1. Safe areas & system UI**
- Regions with top edge under system status bar → `safe_area: "top"`.
- Regions above system navigation bar, home indicator, or soft keyboard → `safe_area: "bottom"`, anchor to `bottom` with `offset: "0px"`.
- No status bars, navigation bars, keyboards, or device chrome in the component tree.

**G2. Keyboard adaptation**
- Pages with text inputs → the region containing the input area must anchor to `bottom` with `safe_area: "bottom"`.
- No fixed pixel offsets to simulate keyboard-pushed positions.

**Output**: overwrite each `ui-acceptance-contract.yaml` with the optimized version. Update `section-map.json` only if unit classification changes. If a fixed value is source-justified, keep it. If `auto`/`fill` is semantically correct, apply it. Surface any ambiguous case in the subagent's response.
```

- [ ] **Step 2: Verify renumbered Stage and checklist items**

Run: `grep -n "### 4. Final Contract Review" .agents/skills/ui-truth-mapping/SKILL.md`
Expected: One match.

Run: `grep -n "### 5. Final Contract Review" .agents/skills/ui-truth-mapping/SKILL.md && echo "FAIL" || echo "PASS: old number removed"`
Expected: PASS.

Run: `grep -c "^\*\*S[0-9]" .agents/skills/ui-truth-mapping/SKILL.md`
Expected: 0 — "S1" etc. should appear as `**S1.**` not at start of line, but let me check: `grep -c "\*\*S[1-4]\.\*\*" .agents/skills/ui-truth-mapping/SKILL.md` should be 4.

Run: `grep -c "\*\*L[1-4]\.\*\*" .agents/skills/ui-truth-mapping/SKILL.md`
Expected: 4.

Run: `grep -c "\*\*C[1-4]\.\*\*" .agents/skills/ui-truth-mapping/SKILL.md`
Expected: 4.

Run: `grep -c "\*\*G[1-2]\.\*\*" .agents/skills/ui-truth-mapping/SKILL.md`
Expected: 2.

- [ ] **Step 3: Commit**

```bash
git add .agents/skills/ui-truth-mapping/SKILL.md
git commit -m "feat: reorganize Stage 4 review checklist by pass layer (S1-4/L1-4/C1-4/G1-2)"
```

---

### Task 5: Mirror all changes to SKILL-zh.md

**Files:**
- Modify: `.agents-zh/skills/ui-truth-mapping/SKILL-zh.md` (equivalent changes for Chinese version)

- [ ] **Step 1: Replace old Stages 3+4 in SKILL-zh.md with new Stage 3** (mirrors Task 3)

Find the range from `### 3. 收集设计证据` (line 96) through the end of `### 4. 冻结 YAML 契约` content (line 167 `- **跟随键盘的区域...**`). Replace with the new Stage 3 in Chinese:

```
### 3. 三层增量契约构建 *（在逐单元子代理内运行）*

此步骤在每个逐单元子代理内运行。子代理只能访问其分配单元的帧和证据 — 无其他单元的交叉污染。

**执行模型：** 在同一 YAML 文件上执行三层顺序编辑。每层一次只处理一个帧 — 永远不要将所有帧批量塞入单个 Figma 查询。每层只填充其分配的字段，不触碰其他层拥有的字段。

**首先，复制模板。** 找到 `templates/ui-acceptance-contract-template.yaml`，将其逐字复制到本单元的输出路径。三层全部编辑同一个文件。

#### Pass 1 — 骨架层

**用途：** 构建组件树结构和状态声明。

**Figma 查询：** `get_structure(frame_source_node)` — 每帧一次，仅结构级。此层不要使用 `get_code`。

**你填充的字段：**
- `version`、`contract_id`
- `source` — 需求文件名、Figma 文件 key、根节点 ID、缓存路径
- `states` — 每帧一个条目：`id`（来自帧的 `state_type` 分类）和 `source_node`
- `background` — 仅页面级颜色，来自默认/idle 帧
- `regions[].children[]` — 组件树骨架：`id`、`type`、`name`、`source_node`、`visible_when`、递归 `children`

**不要触碰：** `anchor`、`layout`、`box`（width/height/padding）、`background`（组件级）、`content`（text/icon/image/font）、`interaction`、`description`。保持这些为模板默认值（`null`、`{}`、`[]`、`0`）。

**逐帧迭代：**

对于该单元帧列表中的每一帧，一次处理一个：

1. 调用 `get_structure(<frame-source-node>)`。
2. 提取组件层级 — 组件类型、嵌套关系、可见元素。
3. **第一个处理的帧：** 在 `regions[].children[]` 中创建所有组件节点。填充 `id`、`type`、`name`、`source_node`。设置 `visible_when: null`（默认状态组件始终可见）。使用 Figma 父子结构递归填充 `children`。
4. **后续帧：** 对此帧中发现的每个组件：
   - 若组件具有相同的 `source_node` 且已存在于树中 → 同一组件在不同状态。不要创建重复项。若其仅特定状态可见则设置或细化 `visible_when` 条件。
   - 若组件具有新的 `source_node` 且树中不存在 → 特定于状态的内容。将其追加到适当父组件的 `children` 中，并设置导致其出现的语义条件的 `visible_when`。
5. 将帧的状态条目添加到 YAML 顶部的 `states` 列表 — 每帧一个 `id` + `source_node`。

**跨状态合并规则：**
- 所有状态中存在的组件：使用默认/idle 帧的 `source_node`，`visible_when: null`。
- 仅部分状态中存在的组件：使用其可见帧的 `source_node`，设置语义条件的 `visible_when`。
- 仅样式在不同状态间变化的组件：单个组件条目，样式差异写入 `states` — 在 Pass 3 中填充。
- 绝不为不同状态创建相同 `id` 的两个组件条目。

**Pass 1 完成后：** YAML 具有完整的 `states` 列表和完整的组件树，包含 `id`、`type`、`name`、`source_node`、`visible_when`。所有其他字段为模板默认值。

#### Pass 2 — 布局层

**用途：** 为每个组件填充定位、尺寸和布局。

**Figma 查询：** `get_code(frame_source_node)` — 每帧一次，代码级。读取 Pass 1 的 YAML，按 `source_node` 查找组件。

**你填充的字段：**
- `anchor` — 每个组件恰好 4 个条目：`start`、`end`、`top`、`bottom`。每个包含：
  - `to`：引用组件 ID、`screen_start`、`screen_end`、`screen_top`、`screen_bottom`
  - `direction`：附着到引用边缘的哪个方向
  - `offset`：与引用边缘的 `<Npx>` 间距，或 `auto` 当父布局控制定位时
  - `note`：当 `offset` 为 `auto` 时必须填写 — 解释偏移量如何计算
- `layout` — `direction`（vertical/horizontal/none）、`align`、`gap`
- `box` — `width`（auto/fill/<Npx>）、`height`（auto/<Npx>）、`padding`（全部 4 方向必需：top/right/bottom/left；无视觉间距时使用 `0`）

**不要触碰：** 所有 Pass 1 字段（`id`、`type`、`name`、`source_node`、`visible_when`、`states`）。同时：`background`（组件级）、`content`（text/icon/image/font）、`interaction`、`description`。即使存在固定 px 也不要在此处写 `description` — Pass 3 会处理。

**逐帧迭代：**

对于该单元帧列表中的每一帧，一次处理一个：

1. 读取当前 YAML 文件。找到所有 `source_node` 属于此帧的组件。
2. 调用 `get_code(<frame-source-node>)` 获取精确的定位数据。
3. 为此帧中找到的每个组件提取并填充：
   - **anchor**：计算全部 4 个锚点条目。从参考底部边缘的偏移公式：`offset = 子元素.y − (参考元素.y + 参考元素.height)`。与参考边缘齐平时使用 `0px`。使用 `auto` 当父布局（如列表）控制定位时 — 添加 `note` 解释计算方式。
   - **layout**：从 Figma 自动布局或手动定位数据中提取方向、对齐和间距。
   - **box**：`width` 优先 `auto` > `fill` > `<Npx>`。`height` 优先 `auto` > `<Npx>`。`padding` 全部 4 方向从测量内边距中获取；设计显示齐平时使用 `0`。
4. 移动到下一帧。重复直到所有帧处理完毕。

**Pass 2 完成后：** 每个组件具有完整的 anchor、layout 和 box。`background`（组件级）、`content`、`interaction` 和 `description` 保持为模板默认值。

#### Pass 3 — 样式内容层

**用途：** 为每个组件填充视觉样式、内容和交互。

**Figma 查询：** `get_code(frame_source_node)` — 每帧一次，代码级。可复用 Pass 2 的缓存数据（相同的 `get_code` 查询）。读取 Pass 2 的 YAML 查找组件。

**你填充的字段：**
- `background` — 组件级：`color`、`border`（radius/width/color）、`shadow`、`opacity`
- `content` — 每个组件恰好填充一个插槽：
  - 文本组件：`text`（可见文本内容）+ `font`（family、size、weight、color、height、align）
  - 图标组件：`icon`（src — 资源文件名，size — 显示尺寸）
  - 图片组件：`image`（src、width、height、fit）
- `interaction` — `on`（click/long-press/none）、`action`、`note`
- `states` — 与默认状态的差异。组件状态键名（如 `selected`、`active`、`disabled`），每个为部分组件差异。示例：`{ selected: { background: { border: { color: "#41B8F4" } } } }`。
- `description` — 当 `box.width` 或 `box.height` 使用固定 `<Npx>` 时必须填写；解释为何 `auto` 不适用（如"图标基准尺寸"、"触控目标最小值"）。

**不要触碰：** 所有 Pass 1 字段，所有 Pass 2 字段（`anchor`、`layout`、`box`）。不要修改组件树结构、增加/删除节点或更改 `source_node` 值。不要更改 `visible_when` 条件。

**逐帧迭代：**

对于该单元帧列表中的每一帧，一次处理一个：

1. 读取当前 YAML 文件。找到所有 `source_node` 属于此帧的组件。
2. 调用 `get_code(<frame-source-node>)` — 若 Pass 2 已有缓存在 `.ai-delivery/figma-cache/<file-key>/code/<node-id>.json` 中则复用；如未缓存则重新获取。
3. 为此帧中找到的每个组件提取并填充：
   - **background**：颜色填充、边框样式、阴影、透明度。
   - **content**：从 Figma 节点确定内容类型 — 文本节点 → `text`+`font`；矢量/图标节点 → `icon`；图片填充节点 → `image`。恰好填充一个插槽。
   - **interaction**：若组件是交互式的（设计中有 click/long-press 行为），填充 `on`、`action` 和 `note`。
   - **states**：若此组件在 Pass 1 确定的状态间有样式变化，写入各状态的差异。每个差异仅包含组件默认值（Pass 3）中变化的属性。
   - **description**：若 `box.width` 或 `box.height` 使用固定 `<Npx>`，写简要的理由说明。
4. 移动到下一帧。重复直到所有帧处理完毕。

**Pass 3 完成后：** YAML 契约完整。所有字段均使用 design-backed 值填充。

**全部三层完成后：** 子代理将完成的 `ui-acceptance-contract.yaml` 返回给主会话。主会话收集所有单元契约后进入阶段 4。
```

- [ ] **Step 2: Replace old Stage 5 with new Stage 4 in SKILL-zh.md** (mirrors Task 4)

Old text: `### 5. 最终契约审校` through the end of review content. Replace with reorganized Chinese Stage 4 with S1-4/L1-4/C1-4/G1-2 checklist.

```
### 4. 最终契约审校

**强制执行 — 每次 YAML 冻结后运行。** 审校生成的每一份契约（page、modal、shared-shell），不得跳过任何单元。使用子代理纯净执行 — 子代理接收所有契约和 `section-map.json`，返回优化后的契约。

此审校仅规范化布局语义和尺寸。不新增或删除 source-backed 组件、状态、`visible_when` 条件或 `source_node` 值。

**审校顺序（严格遵循，按 pass 层组织）：**

**骨架质量（Pass 1 产出）：**

**S1. 组件树完整性**
- `section-map.json` 中枚举的每个帧的 `source_node` 必须在树中至少有一个对应的组件节点。
- 没有帧被遗漏。

**S2. visible_when 覆盖率**
- 所有非默认状态组件必须有 `visible_when` 条件。
- 条件使用语义化语言（如"选项已被选中"），不使用机械的状态 ID 检查。

**S3. states 列表一致性**
- YAML 中的 `states` 列表必须与 `section-map.json` 中声明的帧一致 — 相同的数量，每个状态有 `id` + `source_node`。

**S4. source 元数据完整性**
- `source.requirement`、`source.design_file`、`source.root_node`、`source.cache` 全部已填充。

**布局质量（Pass 2 产出）：**

**L1. anchor 4 方向完整性**
- 每个组件有全部 4 个 anchor 条目（`start`、`end`、`top`、`bottom`）。
- 每个条目有明确的 `to`、`direction` 和 `offset` — 无 null、无空字符串。
- `offset: "0px"` 用于齐平附着；`offset: "auto"` 必须有 `note` 解释计算方式。

**L2. padding 4 方向完整性**
- 每个组件的 `padding` 在全部 4 方向（`top`、`right`、`bottom`、`left`）有明确值。
- 设计显示齐平时使用 `0` — 永远不要让 padding 字段为 `null` 或缺失。

**L3. width/height 收敛**
- 文字、标签、说明 → `width: "auto"`、`height: "auto"`。
- 横跨可用宽度的卡片、行 → `width: "fill"`。
- **fill 判定规则**：若组件的 px 宽度等于（父容器宽度 − 对称水平间距），使用 `fill` 而非固定 px。
- 仅保留固定 px：图标、头像、最小触控目标（≥44px）、明确设计要求固定宽度的弹窗。

**L4. gap/align 一致性**
- `layout.gap` 和 `layout.align` 值与 Figma 自动布局数据一致。

**样式内容质量（Pass 3 产出）：**

**C1. content slot — 恰好一个**
- 每个叶子节点组件恰好填充一个内容插槽：`text`+`font`、`icon` 或 `image`。
- 无可视子元素、无文字、无图标、无图片的空容器 → 不应存在于树中。

**C2. background 来源可追溯**
- `background.color`、`border`、`shadow`、`opacity` 值可追溯到 Figma fill/stroke/effect 数据。
- 无凭空编造的颜色或效果。

**C3. interaction 完整性**
- 设置了 `interaction.on` 的组件必须有对应的 `action` 和（非平凡时的）`note`。

**C4. fixed px 理由说明**
- 每个保留固定 `width` 或 `height` px 值的组件必须有 `description` 解释为何 `auto` 不适用。

**全局检查：**

**G1. 安全区与系统 UI**
- 顶部边缘在系统状态栏下的区域 → `safe_area: "top"`。
- 位于系统导航栏、主页指示条或软键盘上方的区域 → `safe_area: "bottom"`，锚定到 `bottom`，`offset: "0px"`。
- 组件树中无状态栏、导航栏、键盘或设备壳层。

**G2. 键盘适配**
- 含文本输入框的页面 → 包含输入区域的 region 必须锚定到 `bottom` 并设 `safe_area: "bottom"`。
- 没有用固定像素偏移模拟键盘位置的写法。

**输出**：用优化后的版本覆盖每个 `ui-acceptance-contract.yaml`。仅在单元分类变更时更新 `section-map.json`。若固定值有源依据则保留，若 `auto`/`fill` 语义正确则应用。在子代理响应中标注任何模棱两可的情况。
```

- [ ] **Step 3: Verify SKILL-zh.md completeness**

Run: `grep -c "你填充的字段" .agents-zh/skills/ui-truth-mapping/SKILL-zh.md`
Expected: 3.

Run: `grep -c "不要触碰" .agents-zh/skills/ui-truth-mapping/SKILL-zh.md`
Expected: At least 3.

Run: `grep -c "\*\*S[1-4]\.\*\*" .agents-zh/skills/ui-truth-mapping/SKILL-zh.md`
Expected: 4.

- [ ] **Step 4: Commit**

```bash
git add .agents-zh/skills/ui-truth-mapping/SKILL-zh.md
git commit -m "feat: mirror three-pass incremental contract to SKILL-zh.md"
```

---

### Task 6: Run validation and end-to-end check

**Files:**
- Run: `scripts/validate-project-ai-delivery-skills.sh`

- [ ] **Step 1: Update validation expectations if needed**

The validation script checks for specific string patterns. After the rewrite, check if any expected strings have changed.

Check the validation function `validate_ui_truth_mapping_skill` in `scripts/validate-project-ai-delivery-skills.sh` (lines 225-239). It checks for:
- `requirement-slice` — still present in Stage 1
- `Figma` — still present throughout
- `ui-acceptance-contract.yaml` — still present in templates section
- `section-map` — still present in Stage 2
- `Do not invent visual truth` — still present in Hard Boundary
- `screen state` — check if this exact phrase still exists

Run: `grep -n "screen state" .agents/skills/ui-truth-mapping/SKILL.md`
Expected: Need to verify. If absent, update the validation to check for a replacement string like "state frames" or "each frame" or "states".

The phrase "screen state" previously appeared in old Stage 4. In the new text, the concept is still present as "states" but "screen state" (with space) may not appear. Let's check and fix the validation if needed.

If the phrase doesn't exist, update the validation line:
```
require_contains "$skill_file" 'screen state'
```
to:
```
require_contains "$skill_file" 'component tree'
```
(which exists in the new Pass 1 section).

- [ ] **Step 2: Run the validation script**

```bash
bash scripts/validate-project-ai-delivery-skills.sh
```

Expected: `PASS: project-local ai-delivery skill sources are structurally valid.`

- [ ] **Step 3: Run validate-full-chain if available**

```bash
bash scripts/validate-full-chain-repair-contracts.sh 2>/dev/null || echo "No full-chain repair available"
```

- [ ] **Step 4: Commit any validation fixes**

```bash
git add -A
git commit -m "fix: update skill validation expectations for three-pass restructure"
```
(Only if changes were needed.)

---

### Task 7: Final diff review and commit

**Files:**
- Review all changes

- [ ] **Step 1: Show the complete diff**

```bash
git diff HEAD~6..HEAD --stat
```

- [ ] **Step 2: Verify no regressions**

- The YAML template file is unchanged (verify: `git diff main -- .agents/skills/ui-truth-mapping/templates/ui-acceptance-contract-template.yaml` should be empty)
- The section-map template is unchanged (verify: `git diff main -- .agents/skills/ui-truth-mapping/templates/section-map-template.json` should be empty)
- Hard Boundary rules have been added but existing ones are preserved
- All 18 component types from the vocabulary are still listed

Run:
```bash
git diff main -- .agents/skills/ui-truth-mapping/templates/
```
Expected: No output (templates unchanged).

- [ ] **Step 3: Commit if any final cleanup needed**

```bash
git status
```
