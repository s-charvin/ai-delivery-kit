# AI Delivery Admin Runtime And MCP Daemon Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add one-command local startup for `Web + API`, add a governed MCP daemon runtime that can be started and stopped from the admin console, and keep the existing `stdio` MCP entry available for direct agent use.

**Architecture:** Keep the current Hono server, Vite web app, and MCP `stdio` entry intact. Add a new server-owned runtime-management layer, a daemon MCP entry, Web runtime controls, and a Node-based startup supervisor that can install dependencies and orchestrate `Web + API` readiness.

**Tech Stack:** `TypeScript`, `Node.js`, `React`, `Vite`, `Hono`, `vitest`, `@modelcontextprotocol/sdk`, `child_process`, local filesystem metadata under `data/`, and existing admin app tests.

---

### Task 1: Create An Isolated Feature Workspace And Ignore IDE Noise

**Files:**
- Modify: `/Users/charvin/Projects/ai-delivery-admin/.gitignore`

**Step 1: Create a feature worktree or isolated branch**

Use `superpowers:using-git-worktrees` against `/Users/charvin/Projects/ai-delivery-admin`.

Expected: feature work continues outside the current dirty main workspace.

**Step 2: Add IDE ignores**

Add at least:

```gitignore
.idea/
```

**Step 3: Verify git status is no longer polluted by `.idea/`**

Run:

```bash
git status --short
```

Expected: `.idea/` no longer appears as trackable feature noise.

**Step 4: Commit**

```bash
git add .gitignore
git commit -m "chore: ignore local ide metadata"
```

### Task 2: Add Tests For The MCP Runtime Manager Service

**Files:**
- Create: `/Users/charvin/Projects/ai-delivery-admin/server/src/services/mcp-runtime-service.ts`
- Create: `/Users/charvin/Projects/ai-delivery-admin/tests/server/mcp-runtime-service.test.ts`

**Step 1: Write failing tests**

Cover at least:

- reading default stopped state
- starting daemon writes runtime metadata
- starting twice returns a governed conflict
- stopping daemon updates runtime state
- recent log reads return appended output

**Step 2: Run the test and watch it fail**

Run:

```bash
cd /Users/charvin/Projects/ai-delivery-admin && npm run test -- tests/server/mcp-runtime-service.test.ts
```

Expected: FAIL because runtime manager does not exist yet.

**Step 3: Implement minimal runtime manager**

Use admin-local files under `data/` for runtime state and logs.

**Step 4: Re-run the test**

Expected: PASS

**Step 5: Commit**

```bash
git add server/src/services/mcp-runtime-service.ts tests/server/mcp-runtime-service.test.ts
git commit -m "feat: add mcp runtime manager service"
```

### Task 3: Add A Managed MCP Daemon Entry Without Replacing Stdio Mode

**Files:**
- Create: `/Users/charvin/Projects/ai-delivery-admin/mcp-server/src/daemon.ts`
- Modify: `/Users/charvin/Projects/ai-delivery-admin/package.json`
- Create: `/Users/charvin/Projects/ai-delivery-admin/tests/mcp/daemon-entry.test.ts`

**Step 1: Write failing tests for the daemon entry contract**

Verify:

- daemon entry boots without using `stdio`
- daemon entry exposes a health/readiness surface suitable for the runtime manager
- existing `stdio` entry is untouched

**Step 2: Run the test and watch it fail**

Run:

```bash
cd /Users/charvin/Projects/ai-delivery-admin && npm run test -- tests/mcp/daemon-entry.test.ts
```

Expected: FAIL

**Step 3: Implement daemon entry and add a new script**

Add a script such as:

- `dev:mcp-daemon`

Keep:

- `dev:mcp`

**Step 4: Re-run the test**

Expected: PASS

**Step 5: Commit**

```bash
git add mcp-server package.json tests/mcp/daemon-entry.test.ts
git commit -m "feat: add managed mcp daemon entry"
```

### Task 4: Expose Governed Runtime Control APIs

**Files:**
- Create: `/Users/charvin/Projects/ai-delivery-admin/server/src/routes/runtime.ts`
- Modify: `/Users/charvin/Projects/ai-delivery-admin/server/src/app.ts`
- Create: `/Users/charvin/Projects/ai-delivery-admin/tests/server/runtime-routes.test.ts`

**Step 1: Write failing API tests**

Cover:

- `GET /api/runtime/mcp`
- `POST /api/runtime/mcp/start`
- `POST /api/runtime/mcp/stop`
- `GET /api/runtime/mcp/logs`

Verify duplicate start and invalid stop produce governed failures.

**Step 2: Run the tests and watch them fail**

Run:

```bash
cd /Users/charvin/Projects/ai-delivery-admin && npm run test -- tests/server/runtime-routes.test.ts
```

Expected: FAIL

**Step 3: Implement runtime routes using the runtime manager**

**Step 4: Re-run the tests**

Expected: PASS

**Step 5: Commit**

```bash
git add server/src/app.ts server/src/routes/runtime.ts tests/server/runtime-routes.test.ts
git commit -m "feat: add governed mcp runtime routes"
```

### Task 5: Add Web Runtime Controls And Log Visibility

**Files:**
- Modify: `/Users/charvin/Projects/ai-delivery-admin/web/src/App.tsx`
- Create: `/Users/charvin/Projects/ai-delivery-admin/web/src/pages/RuntimePage.tsx`
- Modify: `/Users/charvin/Projects/ai-delivery-admin/web/src/components/Sidebar.tsx`
- Modify: `/Users/charvin/Projects/ai-delivery-admin/web/src/lib/api.ts`
- Modify: `/Users/charvin/Projects/ai-delivery-admin/web/src/lib/types.ts`
- Create: `/Users/charvin/Projects/ai-delivery-admin/tests/web/runtime-page.test.tsx`

**Step 1: Write failing UI tests**

Verify:

- runtime page renders current MCP status
- start button calls the start endpoint
- stop button calls the stop endpoint
- recent logs are visible

**Step 2: Run the test and watch it fail**

Run:

```bash
cd /Users/charvin/Projects/ai-delivery-admin && npm run test -- tests/web/runtime-page.test.tsx
```

Expected: FAIL

**Step 3: Implement runtime API client and page**

Add a nav entry such as `Runtime`.

**Step 4: Re-run the test**

Expected: PASS

**Step 5: Commit**

```bash
git add web/src/App.tsx web/src/pages/RuntimePage.tsx web/src/components/Sidebar.tsx web/src/lib/api.ts web/src/lib/types.ts tests/web/runtime-page.test.tsx
git commit -m "feat: add mcp runtime controls to web console"
```

### Task 6: Add One-Command Local Startup For Web And API

**Files:**
- Create: `/Users/charvin/Projects/ai-delivery-admin/scripts/admin-start.ts`
- Create: `/Users/charvin/Projects/ai-delivery-admin/tests/scripts/admin-start.test.ts`
- Modify: `/Users/charvin/Projects/ai-delivery-admin/package.json`

**Step 1: Write failing tests for startup orchestration**

Verify:

- missing dependencies trigger install step
- API and Web child processes are spawned
- readiness is checked before success is reported
- failure in one child tears down the other child

**Step 2: Run the test and watch it fail**

Run:

```bash
cd /Users/charvin/Projects/ai-delivery-admin && npm run test -- tests/scripts/admin-start.test.ts
```

Expected: FAIL

**Step 3: Implement the Node-based supervisor**

Add a primary command such as:

- `npm run admin:start`

Optional:

- `npm run admin:status`

Do not remove:

- `dev:web`
- `dev:server`
- `dev:mcp`
- `dev:mcp-daemon`

**Step 4: Re-run the tests**

Expected: PASS

**Step 5: Commit**

```bash
git add scripts/admin-start.ts package.json tests/scripts/admin-start.test.ts
git commit -m "feat: add one-command local admin startup"
```

### Task 7: Update Docs And Add End-To-End Runtime Smoke Coverage

**Files:**
- Modify: `/Users/charvin/Projects/ai-delivery-admin/README.md`
- Modify: `/Users/charvin/Projects/ai-delivery-admin/mcp-server/README.md`
- Modify: `/Users/charvin/Projects/ai-delivery-admin/skills/README.md`
- Create: `/Users/charvin/Projects/ai-delivery-admin/tests/server/runtime-smoke.test.ts`

**Step 1: Write failing smoke coverage**

Verify:

- runtime status endpoint works against the real app wiring
- daemon can be started and stopped through governed APIs
- one-command startup documentation matches actual scripts

**Step 2: Run the test and watch it fail**

Run:

```bash
cd /Users/charvin/Projects/ai-delivery-admin && npm run test -- tests/server/runtime-smoke.test.ts
```

Expected: FAIL

**Step 3: Update docs**

Document:

- one-command startup
- how daemon mode differs from `stdio` mode
- how Web controls MCP runtime
- that Docker is intentionally not part of this feature

**Step 4: Re-run targeted smoke**

Expected: PASS

**Step 5: Commit**

```bash
git add README.md mcp-server/README.md skills/README.md tests/server/runtime-smoke.test.ts
git commit -m "docs: add runtime startup and mcp daemon guidance"
```

### Task 8: Run Full Verification

**Files:**
- No new files

**Step 1: Run the full test suite**

```bash
cd /Users/charvin/Projects/ai-delivery-admin && npm run test
```

Expected: PASS

**Step 2: Run typecheck**

```bash
cd /Users/charvin/Projects/ai-delivery-admin && npm run typecheck
```

Expected: PASS

**Step 3: Run the frontend build**

```bash
cd /Users/charvin/Projects/ai-delivery-admin && npm run build:web
```

Expected: PASS

**Step 4: Commit any final doc or verification fixes**

```bash
git add .
git commit -m "test: finalize runtime and daemon integration"
```
