# AI Delivery Admin Folder Picker Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a native system folder picker flow to the `ai-delivery-admin` project binding UI so users can choose a project root instead of typing absolute paths manually.

**Architecture:** Keep the existing `bindProject` contract unchanged and add a new local server route that opens a native directory picker and returns the selected absolute path. Wire the web app to call that route from the `Bound Project` surface and fill the `Project Root` field with the chosen value.

**Tech Stack:** Hono, Node built-ins, React 19, Mantine, Vitest

---

### Task 1: Write failing server tests for the folder picker route

**Files:**
- Create: `/Users/charvin/Projects/spec-dev/ai-delivery-admin/tests/server/project-root-picker.test.ts`
- Modify: `/Users/charvin/Projects/spec-dev/ai-delivery-admin/server/src/app.ts`

**Step 1: Write the failing test**

Cover:

- route returns a selected path from an injected picker service
- route returns `cancelled: true` when user cancels

**Step 2: Run test to verify it fails**

Run:

```bash
npm test -- tests/server/project-root-picker.test.ts
```

Expected: FAIL because the route and injected picker service do not exist yet.

### Task 2: Write a failing web test for the choose-folder interaction

**Files:**
- Modify: `/Users/charvin/Projects/spec-dev/ai-delivery-admin/tests/web/navigation.test.tsx`

**Step 1: Write the failing test**

Cover:

- clicking `Choose Folder` calls the new API
- the returned path populates the `Project Root` input

**Step 2: Run test to verify it fails**

Run:

```bash
npm test -- navigation.test.tsx
```

Expected: FAIL because the button and API call do not exist yet.

### Task 3: Implement the native folder picker service and route

**Files:**
- Create: `/Users/charvin/Projects/spec-dev/ai-delivery-admin/server/src/services/project-root-picker-service.ts`
- Modify: `/Users/charvin/Projects/spec-dev/ai-delivery-admin/server/src/app.ts`
- Modify: `/Users/charvin/Projects/spec-dev/ai-delivery-admin/server/src/routes/projects.ts`

**Step 1: Add a picker service abstraction**

Define an interface that can be injected in tests and implemented with a macOS native folder picker.

**Step 2: Add the route**

Expose `POST /api/system/select-project-root`.

**Step 3: Handle success, cancel, and unsupported platform cases**

Return structured JSON for success/cancel and clear server errors for unsupported environments.

### Task 4: Implement the web API and project selector button

**Files:**
- Modify: `/Users/charvin/Projects/spec-dev/ai-delivery-admin/web/src/lib/api.ts`
- Modify: `/Users/charvin/Projects/spec-dev/ai-delivery-admin/web/src/App.tsx`
- Modify: `/Users/charvin/Projects/spec-dev/ai-delivery-admin/web/src/components/ProjectSelector.tsx`

**Step 1: Add a client helper**

Add `selectProjectRoot()`.

**Step 2: Add UI state and callback**

Track `choosingProjectRoot` separately from `busy`.

**Step 3: Add the button**

Render `Choose Folder` next to the bind action and update the input on success.

### Task 5: Verify green

**Files:**
- Modify as needed based on failures

**Step 1: Run targeted tests**

```bash
npm test -- tests/server/project-root-picker.test.ts navigation.test.tsx
```

**Step 2: Run full verification**

```bash
npm test
npm run typecheck
npm run build:web
```

Expected: all commands pass with fresh output.
