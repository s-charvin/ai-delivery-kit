# AI Delivery Admin Requirement Grouping Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Refactor the `ai-delivery-admin` web console so requirement packages become the primary management scope across the explorer, traceability view, artifact editor, and execution board without changing the `.ai-delivery/requirements/<requirement-id>/...` truth contract.

**Architecture:** Keep the server and adapter contracts unchanged and derive a shared requirement-grouped view model entirely in the web layer. `App.tsx` becomes the orchestration point for requirement-scoped state, while the explorer, traceability page, artifact editor, and execution board consume filtered requirement-aware collections instead of flat global sub-requirement lists.

**Tech Stack:** `TypeScript`, `React`, `Vite`, `vitest`, `@testing-library/react`, existing `ai-delivery-admin` web pages and shared client-side API/types.

---

## Preconditions

- Work in `/Users/charvin/Projects/Codex/.worktrees/ai-delivery-admin-requirement-grouping-ui`
- Reuse the existing dependency tree through the linked `node_modules/`
- Treat `tests/server/read-api.test.ts` as a pre-existing baseline drift until separately repaired

### Task 1: Add Requirement Grouping View Models

**Files:**
- Modify: `/Users/charvin/Projects/ai-delivery-admin/web/src/lib/types.ts`
- Create: `/Users/charvin/Projects/ai-delivery-admin/web/src/lib/requirement-groups.ts`
- Test: `/Users/charvin/Projects/ai-delivery-admin/tests/web/requirement-explorer.test.tsx`

**Step 1: Write the failing test**

Add a new explorer-focused test that renders two requirements and verifies grouped counts are shown per requirement rather than as a flat sub-requirement list.

```tsx
test('shows grouped requirement counts and nested sub-requirements', () => {
  render(<RequirementExplorerPage requirements={requirements} blockers={blockers} />)

  expect(screen.getByText(/Requirement One/i)).toBeInTheDocument()
  expect(screen.getByText(/2 sub-requirements/i)).toBeInTheDocument()
  expect(screen.getByText(/1 blocked/i)).toBeInTheDocument()
})
```

**Step 2: Run test to verify it fails**

Run:

```bash
npm test -- tests/web/requirement-explorer.test.tsx
```

Expected: FAIL because the page does not yet support grouped metrics or the new props.

**Step 3: Write minimal implementation**

Add requirement-grouped client-side types and a helper that computes:

```ts
export type RequirementGroup = {
  requirement_id: string
  title: string
  summary: string
  sub_requirements: SubRequirementSummary[]
  sub_requirement_count: number
  blocked_count: number
  in_progress_count: number
  status_counts: Record<string, number>
}
```

and

```ts
export function buildRequirementGroups(
  requirements: RequirementSummary[],
  blockers: BlockerRecord[]
): RequirementGroup[] {
  // derive grouped counts from existing payloads
}
```

**Step 4: Run test to verify it passes**

Run:

```bash
npm test -- tests/web/requirement-explorer.test.tsx
```

Expected: PASS

**Step 5: Commit**

```bash
git -C /Users/charvin/Projects/Codex/.worktrees/ai-delivery-admin-requirement-grouping-ui add web/src/lib/types.ts web/src/lib/requirement-groups.ts tests/web/requirement-explorer.test.tsx
git -C /Users/charvin/Projects/Codex/.worktrees/ai-delivery-admin-requirement-grouping-ui commit -m "feat: add requirement grouping view model"
```

### Task 2: Rebuild Requirement Explorer As A Tree Browser

**Files:**
- Modify: `/Users/charvin/Projects/ai-delivery-admin/web/src/pages/RequirementExplorerPage.tsx`
- Modify: `/Users/charvin/Projects/ai-delivery-admin/web/src/styles.css`
- Test: `/Users/charvin/Projects/ai-delivery-admin/tests/web/requirement-explorer.test.tsx`

**Step 1: Write the failing test**

Extend the explorer test to cover:

- requirement collapse and expand
- blocked-only filtering
- search scoped to requirement or nested sub-requirements

```tsx
fireEvent.click(screen.getByRole('button', { name: /hide requirement one/i }))
expect(screen.queryByText(/Sub Requirement A/i)).not.toBeInTheDocument()

fireEvent.click(screen.getByLabelText(/only blocked/i))
expect(screen.queryByText(/Healthy Sub Requirement/i)).not.toBeInTheDocument()
```

**Step 2: Run test to verify it fails**

Run:

```bash
npm test -- tests/web/requirement-explorer.test.tsx
```

Expected: FAIL because explorer filtering and tree controls do not exist yet.

**Step 3: Write minimal implementation**

Refactor the page to render:

- search input
- status filter
- blocked-only toggle
- sort select
- requirement cards with metrics and collapse buttons
- nested sub-requirement rows inside each requirement card

Use one requirement card per grouped requirement and keep all sub-requirements visually nested beneath it.

**Step 4: Run test to verify it passes**

Run:

```bash
npm test -- tests/web/requirement-explorer.test.tsx
```

Expected: PASS

**Step 5: Commit**

```bash
git -C /Users/charvin/Projects/Codex/.worktrees/ai-delivery-admin-requirement-grouping-ui add web/src/pages/RequirementExplorerPage.tsx web/src/styles.css tests/web/requirement-explorer.test.tsx
git -C /Users/charvin/Projects/Codex/.worktrees/ai-delivery-admin-requirement-grouping-ui commit -m "feat: rebuild requirement explorer as grouped tree"
```

### Task 3: Add Requirement-Scoped Selection To Traceability And Artifact Editing

**Files:**
- Modify: `/Users/charvin/Projects/ai-delivery-admin/web/src/App.tsx`
- Modify: `/Users/charvin/Projects/ai-delivery-admin/web/src/pages/TraceabilityPage.tsx`
- Modify: `/Users/charvin/Projects/ai-delivery-admin/web/src/components/ArtifactEditor.tsx`
- Modify: `/Users/charvin/Projects/ai-delivery-admin/web/src/pages/ArtifactEditorPage.tsx`
- Modify: `/Users/charvin/Projects/ai-delivery-admin/web/src/styles.css`
- Test: `/Users/charvin/Projects/ai-delivery-admin/tests/web/traceability.test.tsx`
- Test: `/Users/charvin/Projects/ai-delivery-admin/tests/web/artifact-editor.test.tsx`
- Test: `/Users/charvin/Projects/ai-delivery-admin/tests/web/navigation.test.tsx`

**Step 1: Write the failing test**

Add tests that require:

- choosing a requirement before selecting a sub-requirement
- resetting the selected sub-requirement when the requirement changes
- limiting dropdown options to the active requirement scope

```tsx
fireEvent.change(screen.getByLabelText(/requirement/i), { target: { value: 'RQ-002' } })
expect(screen.getByRole('option', { name: /RQ-002 Sub Requirement/i })).toBeInTheDocument()
expect(screen.queryByRole('option', { name: /RQ-001 Sub Requirement/i })).not.toBeInTheDocument()
```

**Step 2: Run test to verify it fails**

Run:

```bash
npm test -- tests/web/traceability.test.tsx tests/web/artifact-editor.test.tsx tests/web/navigation.test.tsx
```

Expected: FAIL because App and child pages do not yet manage `selectedRequirementId`.

**Step 3: Write minimal implementation**

Add requirement-scoped state in `App.tsx`:

```ts
const [selectedRequirementId, setSelectedRequirementId] = useState('')
const visibleSubRequirements = subRequirements.filter(
  (item) => item.requirement_id === selectedRequirementId
)
```

Then update Traceability and Artifact Editor so they:

- render a requirement selector
- populate the sub-requirement selector from the active requirement only
- auto-reset invalid stale selections

**Step 4: Run test to verify it passes**

Run:

```bash
npm test -- tests/web/traceability.test.tsx tests/web/artifact-editor.test.tsx tests/web/navigation.test.tsx
```

Expected: PASS

**Step 5: Commit**

```bash
git -C /Users/charvin/Projects/Codex/.worktrees/ai-delivery-admin-requirement-grouping-ui add web/src/App.tsx web/src/pages/TraceabilityPage.tsx web/src/components/ArtifactEditor.tsx web/src/pages/ArtifactEditorPage.tsx web/src/styles.css tests/web/traceability.test.tsx tests/web/artifact-editor.test.tsx tests/web/navigation.test.tsx
git -C /Users/charvin/Projects/Codex/.worktrees/ai-delivery-admin-requirement-grouping-ui commit -m "feat: add requirement-scoped editing and traceability"
```

### Task 4: Add Requirement Filtering To Execution Board

**Files:**
- Modify: `/Users/charvin/Projects/ai-delivery-admin/web/src/pages/ExecutionBoardPage.tsx`
- Modify: `/Users/charvin/Projects/ai-delivery-admin/web/src/App.tsx`
- Modify: `/Users/charvin/Projects/ai-delivery-admin/web/src/styles.css`
- Test: `/Users/charvin/Projects/ai-delivery-admin/tests/web/execution-board.test.tsx`

**Step 1: Write the failing test**

Require the board to render a requirement filter and hide items from other requirements.

```tsx
fireEvent.change(screen.getByLabelText(/requirement/i), { target: { value: 'RQ-001' } })
expect(screen.getByText(/Sub Requirement One/i)).toBeInTheDocument()
expect(screen.queryByText(/Sub Requirement Two/i)).not.toBeInTheDocument()
```

**Step 2: Run test to verify it fails**

Run:

```bash
npm test -- tests/web/execution-board.test.tsx
```

Expected: FAIL because the board only groups by status today.

**Step 3: Write minimal implementation**

Add a requirement filter control above the board and apply it before grouping/rendering items. Keep the existing status-lane structure intact.

**Step 4: Run test to verify it passes**

Run:

```bash
npm test -- tests/web/execution-board.test.tsx
```

Expected: PASS

**Step 5: Commit**

```bash
git -C /Users/charvin/Projects/Codex/.worktrees/ai-delivery-admin-requirement-grouping-ui add web/src/pages/ExecutionBoardPage.tsx web/src/App.tsx web/src/styles.css tests/web/execution-board.test.tsx
git -C /Users/charvin/Projects/Codex/.worktrees/ai-delivery-admin-requirement-grouping-ui commit -m "feat: filter execution board by requirement"
```

### Task 5: Full Verification

**Files:**
- Verify: `/Users/charvin/Projects/Codex/.worktrees/ai-delivery-admin-requirement-grouping-ui/tests/web/*.test.tsx`
- Verify: `/Users/charvin/Projects/Codex/.worktrees/ai-delivery-admin-requirement-grouping-ui`

**Step 1: Run focused web tests**

Run:

```bash
npm test -- tests/web/requirement-explorer.test.tsx tests/web/navigation.test.tsx tests/web/traceability.test.tsx tests/web/artifact-editor.test.tsx tests/web/execution-board.test.tsx
```

Expected: PASS

**Step 2: Run the full test suite**

Run:

```bash
npm test
```

Expected: all new requirement-grouping tests pass; if the known `tests/server/read-api.test.ts` environment drift still fails, report it separately as pre-existing.

**Step 3: Run typecheck**

Run:

```bash
npm run typecheck
```

Expected: PASS

**Step 4: Review the diff**

Run:

```bash
git -C /Users/charvin/Projects/Codex/.worktrees/ai-delivery-admin-requirement-grouping-ui diff -- web/src tests/web
```

Expected: only requirement-grouping web changes and related tests appear

**Step 5: Commit**

```bash
git -C /Users/charvin/Projects/Codex/.worktrees/ai-delivery-admin-requirement-grouping-ui add web/src tests/web
git -C /Users/charvin/Projects/Codex/.worktrees/ai-delivery-admin-requirement-grouping-ui commit -m "feat: add requirement-grouped admin browsing"
```
