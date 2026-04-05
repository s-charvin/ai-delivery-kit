# AI Delivery Admin UI Refresh Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Refresh `ai-delivery-admin` with a Mantine-based control console, Markdown-first artifact preview, stronger interaction feedback, and a strengthened project-local `ui-interaction-design` skill.

**Architecture:** Keep the existing server API and page data flow intact while replacing the web shell and primary surfaces with Mantine components. Add Markdown/JSON preview behavior inside the artifact editor, then harden the project-local interaction skill and validation contract so the interaction-design guidance is local, governed, and testable.

**Tech Stack:** React 19, Vite, Vitest, Mantine, react-markdown, remark-gfm, project-local skill sources under `Codex/.codex/skills/ai-delivery`

---

### Task 1: Add frontend dependencies

**Files:**
- Modify: `/Users/charvin/Projects/spec-dev/ai-delivery-admin/package.json`
- Modify: `/Users/charvin/Projects/spec-dev/ai-delivery-admin/package-lock.json`

**Step 1: Install the approved UI dependencies**

Run:

```bash
npm install @mantine/core @mantine/hooks @mantine/notifications @tabler/icons-react react-markdown remark-gfm
```

Expected: dependencies are added to `package.json` and lockfile updates cleanly.

### Task 2: Add failing web tests for the new artifact editing experience

**Files:**
- Modify: `/Users/charvin/Projects/spec-dev/ai-delivery-admin/tests/web/artifact-editor.test.tsx`

**Step 1: Write failing tests**

Add tests that expect:

- Markdown preview mode can render heading content from the draft
- Dirty state is exposed when draft content changes
- Invalid JSON shows a preview-side warning instead of silent failure

**Step 2: Run test to verify it fails**

Run:

```bash
npm test -- artifact-editor.test.tsx
```

Expected: FAIL because the current editor only renders a textarea and save button.

### Task 3: Add failing skill validation for interaction-quality coverage

**Files:**
- Modify: `/Users/charvin/Projects/spec-dev/Codex/scripts/validate-project-ai-delivery-skills.sh`

**Step 1: Write failing validation assertions**

Require `ui-interaction-design/SKILL.md` to mention:

- `micro-interaction`
- `loading`
- `feedback`
- `timing`
- either `a11y` or `accessibility`
- project-local or local built-in guidance without external skill dependency

**Step 2: Run validation to verify it fails**

Run:

```bash
zsh /Users/charvin/Projects/spec-dev/Codex/scripts/validate-project-ai-delivery-skills.sh
```

Expected: FAIL because the current skill does not yet encode the stronger local-contract language.

### Task 4: Implement the Mantine shell and shared interaction primitives

**Files:**
- Modify: `/Users/charvin/Projects/spec-dev/ai-delivery-admin/web/src/main.tsx`
- Modify: `/Users/charvin/Projects/spec-dev/ai-delivery-admin/web/src/App.tsx`
- Modify: `/Users/charvin/Projects/spec-dev/ai-delivery-admin/web/src/components/Layout.tsx`
- Modify: `/Users/charvin/Projects/spec-dev/ai-delivery-admin/web/src/components/Sidebar.tsx`
- Modify: `/Users/charvin/Projects/spec-dev/ai-delivery-admin/web/src/components/ProjectSelector.tsx`
- Modify: `/Users/charvin/Projects/spec-dev/ai-delivery-admin/web/src/components/StatusBadge.tsx`
- Modify: `/Users/charvin/Projects/spec-dev/ai-delivery-admin/web/src/styles.css`

**Step 1: Add Mantine providers and notifications**

Wrap the app in `MantineProvider` and `Notifications`.

**Step 2: Replace the raw layout shell**

Move the app shell to Mantine `AppShell` with a responsive navbar and a stronger header.

**Step 3: Replace shared primitives**

Refactor sidebar, project selector, and status badges to Mantine components while preserving accessible labels and page names expected by tests.

### Task 5: Implement the Markdown-first artifact editor

**Files:**
- Modify: `/Users/charvin/Projects/spec-dev/ai-delivery-admin/web/src/components/ArtifactEditor.tsx`
- Modify: `/Users/charvin/Projects/spec-dev/ai-delivery-admin/web/src/pages/ArtifactEditorPage.tsx`
- Modify: `/Users/charvin/Projects/spec-dev/ai-delivery-admin/web/src/App.tsx`
- Optionally Create: `/Users/charvin/Projects/spec-dev/ai-delivery-admin/web/src/components/ArtifactPreview.tsx`

**Step 1: Add edit / split / preview modes**

Support Markdown and JSON artifacts with mode switching.

**Step 2: Add preview rendering**

Use `react-markdown` + `remark-gfm` for Markdown and formatted JSON for JSON artifacts.

**Step 3: Add local feedback**

Expose:

- dirty state
- inline JSON parse errors
- local save status
- notification feedback on save success/failure

### Task 6: Refresh the remaining page surfaces

**Files:**
- Modify: `/Users/charvin/Projects/spec-dev/ai-delivery-admin/web/src/pages/DashboardPage.tsx`
- Modify: `/Users/charvin/Projects/spec-dev/ai-delivery-admin/web/src/pages/RequirementExplorerPage.tsx`
- Modify: `/Users/charvin/Projects/spec-dev/ai-delivery-admin/web/src/pages/LogsTimelinePage.tsx`
- Modify: `/Users/charvin/Projects/spec-dev/ai-delivery-admin/web/src/pages/BlockerCenterPage.tsx`
- Modify: `/Users/charvin/Projects/spec-dev/ai-delivery-admin/web/src/pages/ExecutionBoardPage.tsx`
- Modify: `/Users/charvin/Projects/spec-dev/ai-delivery-admin/web/src/pages/RuntimePage.tsx`
- Modify: `/Users/charvin/Projects/spec-dev/ai-delivery-admin/web/src/pages/TraceabilityPage.tsx`
- Modify: `/Users/charvin/Projects/spec-dev/ai-delivery-admin/web/src/components/TraceabilityChain.tsx`

**Step 1: Migrate page sections to Mantine**

Use Mantine cards, groups, stacks, badges, controls, and skeleton-friendly layouts.

**Step 2: Preserve semantics**

Keep existing headings and control labels stable so regressions are minimized.

### Task 7: Update the project-local interaction skill and references

**Files:**
- Modify: `/Users/charvin/Projects/spec-dev/Codex/.codex/skills/ai-delivery/ui-interaction-design/SKILL.md`
- Modify: `/Users/charvin/Projects/spec-dev/Codex/.codex/skills/ai-delivery/ui-interaction-design/references/interaction-quality-guidelines.md`
- Modify: `/Users/charvin/Projects/spec-dev/Codex/.codex/skills/ai-delivery/ui-interaction-design/references/allowed-assumptions.md`

**Step 1: Add the local-contract language**

State clearly that this project-local skill absorbs the needed interaction-quality guidance and does not depend on external skill installation.

**Step 2: Strengthen bounded guidance**

Make micro-interactions, loading, feedback, timing, motion restraint, and a11y expectations explicit within the allowed assumption boundary.

### Task 8: Verify green across tests, typecheck, build, and skill validation

**Files:**
- Modify as needed based on failures from previous tasks

**Step 1: Run targeted web tests**

```bash
npm test -- artifact-editor.test.tsx navigation.test.tsx requirement-explorer.test.tsx traceability.test.tsx execution-board.test.tsx blocker-center.test.tsx runtime-page.test.tsx
```

**Step 2: Run full app verification**

```bash
npm test
npm run typecheck
npm run build:web
```

**Step 3: Run skill validation**

```bash
zsh /Users/charvin/Projects/spec-dev/Codex/scripts/validate-project-ai-delivery-skills.sh
```

Expected: all commands pass with fresh output.
