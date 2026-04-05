# AI Delivery Admin Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build the separate local `ai-delivery-admin` project at `/Users/charvin/Projects/ai-delivery-admin` so it can bind to business projects, consume `.specify/` and `.ai-delivery/`, expose governed local APIs, provide a React admin console for overview, blockers, execution state, logs, and artifact editing, and ship the admin-owned support skill plus governed MCP server.

**Architecture:** Keep business truth inside the host project and implement `ai-delivery-admin` as a separate local application with six owned layers: `shared` for zod schemas and common domain types, `adapters` for filesystem reads over `.specify/` and `.ai-delivery/`, `server` for validated local APIs and write governance, `web` for visualization and editing, `skills` for the single admin support skill, and `mcp-server` for the governed tool surface that wraps the admin system's shared schemas and server-owned workflow controls. This plan owns admin-side agent support end to end, but it still does not implement the three project-local workflow skills that live in the business project.

**Tech Stack:** `TypeScript`, `Node.js`, `npm`, `React`, `Vite`, `Hono`, `zod`, `better-sqlite3`, `vitest`, `@testing-library/react`, `jsdom`, `@modelcontextprotocol/sdk`, filesystem adapters, and shell-based smoke verification against `/Users/charvin/Projects/Codex`.

---

> Git note: `/Users/charvin/Projects/ai-delivery-admin` does not exist yet. Task 1 initializes the new repository so later commits in this plan are valid.

## Ownership Boundary

This execution plan owns only the separate admin project.

It may:

- create `/Users/charvin/Projects/ai-delivery-admin`
- implement `shared/`, `adapters/`, `server/`, `web/`, and `tests/`
- implement `skills/ai-delivery-admin-support/`
- implement `mcp-server/`
- bind to `/Users/charvin/Projects/Codex`
- read and write governed artifacts through validated server APIs
- provide human-facing local visualization and editing workflows
- provide admin-owned agent support surfaces for governed logging, state mutation, blocker handling, and artifact operations

It must not:

- redefine the `.ai-delivery/` source-of-truth contracts
- move business data out of `/Users/charvin/Projects/Codex`
- implement the three project-local workflow skill packages
- change Requirement/Figma governance rules defined in the master plan

## Governing References

This plan is derived from the following approved documents:

- `/Users/charvin/Projects/Codex/docs/plans/2026-04-04-ai-delivery-implementation-plan.md`
- `/Users/charvin/Projects/Codex/docs/plans/2026-04-04-ai-delivery-admin-system-design.md`
- `/Users/charvin/Projects/Codex/docs/plans/2026-04-04-ai-delivery-overall-chain-design.md`
- `/Users/charvin/Projects/Codex/docs/plans/2026-04-04-ai-delivery-master-plan-refactor-design.md`
- `/Users/charvin/Projects/Codex/docs/plans/2026-04-04-requirement-breakdown-skill-design.md`
- `/Users/charvin/Projects/Codex/docs/plans/2026-04-04-ui-requirement-mapping-skill-design.md`
- `/Users/charvin/Projects/Codex/docs/plans/2026-04-04-ui-interaction-design-skill-design.md`

## Preconditions

Before implementation starts:

- `/Users/charvin/Projects/Codex/.ai-delivery/` must already exist
- the project-local data layer must be considered the upstream truth contract
- the admin track may read `.specify/` and `.ai-delivery/`, but may not redesign them
- if `/Users/charvin/Projects/Codex/scripts/validate-ai-delivery-contracts.sh` exists, run it before starting work; otherwise manually validate the required `.ai-delivery/meta/*.json` and `.ai-delivery/runtime/*.json` files with `jq`

### Task 1: Verify The Upstream Data Contract And Scaffold The Admin Workspace

**Files:**
- Verify: `/Users/charvin/Projects/Codex/.ai-delivery/**`
- Create: `/Users/charvin/Projects/ai-delivery-admin/.gitignore`
- Create: `/Users/charvin/Projects/ai-delivery-admin/README.md`
- Create: `/Users/charvin/Projects/ai-delivery-admin/mcp-server/README.md`
- Create: `/Users/charvin/Projects/ai-delivery-admin/skills/README.md`
- Create: `/Users/charvin/Projects/ai-delivery-admin/skills/ai-delivery-admin-support/.gitkeep`
- Create: `/Users/charvin/Projects/ai-delivery-admin/mcp-server/src/tools/.gitkeep`
- Create: `/Users/charvin/Projects/ai-delivery-admin/adapters/src/.gitkeep`
- Create: `/Users/charvin/Projects/ai-delivery-admin/scripts/.gitkeep`
- Create: `/Users/charvin/Projects/ai-delivery-admin/server/src/.gitkeep`
- Create: `/Users/charvin/Projects/ai-delivery-admin/shared/src/.gitkeep`
- Create: `/Users/charvin/Projects/ai-delivery-admin/web/src/.gitkeep`
- Create: `/Users/charvin/Projects/ai-delivery-admin/tests/.gitkeep`
- Create: `/Users/charvin/Projects/ai-delivery-admin/tests/mcp/.gitkeep`
- Create: `/Users/charvin/Projects/ai-delivery-admin/tests/shared/.gitkeep`
- Create: `/Users/charvin/Projects/ai-delivery-admin/tests/skills/.gitkeep`
- Create: `/Users/charvin/Projects/ai-delivery-admin/data/.gitkeep`

**Step 1: Verify the host-project contract surface is present**

Run:

```bash
if [[ -x /Users/charvin/Projects/Codex/scripts/validate-ai-delivery-contracts.sh ]]; then
  zsh /Users/charvin/Projects/Codex/scripts/validate-ai-delivery-contracts.sh /Users/charvin/Projects/Codex
else
  jq empty /Users/charvin/Projects/Codex/.ai-delivery/meta/*.json /Users/charvin/Projects/Codex/.ai-delivery/runtime/*.json
fi
```

Expected: zero exit status

**Step 2: Confirm the target admin path is absent or safe to create**

Run:

```bash
find /Users/charvin/Projects/ai-delivery-admin -maxdepth 3 -print 2>/dev/null || true
```

Expected: no output if the project does not exist yet, or only output you explicitly intend to keep

**Step 3: Create the initial directory skeleton**

Run:

```bash
mkdir -p \
  /Users/charvin/Projects/ai-delivery-admin/adapters/src \
  /Users/charvin/Projects/ai-delivery-admin/server/src/routes \
  /Users/charvin/Projects/ai-delivery-admin/server/src/services \
  /Users/charvin/Projects/ai-delivery-admin/server/src/persistence \
  /Users/charvin/Projects/ai-delivery-admin/shared/src/schemas \
  /Users/charvin/Projects/ai-delivery-admin/skills/ai-delivery-admin-support/references \
  /Users/charvin/Projects/ai-delivery-admin/mcp-server/src/tools \
  /Users/charvin/Projects/ai-delivery-admin/scripts \
  /Users/charvin/Projects/ai-delivery-admin/web/src/components \
  /Users/charvin/Projects/ai-delivery-admin/web/src/pages \
  /Users/charvin/Projects/ai-delivery-admin/web/src/lib \
  /Users/charvin/Projects/ai-delivery-admin/tests/adapters \
  /Users/charvin/Projects/ai-delivery-admin/tests/mcp \
  /Users/charvin/Projects/ai-delivery-admin/tests/server \
  /Users/charvin/Projects/ai-delivery-admin/tests/shared \
  /Users/charvin/Projects/ai-delivery-admin/tests/skills \
  /Users/charvin/Projects/ai-delivery-admin/tests/web \
  /Users/charvin/Projects/ai-delivery-admin/tests/fixtures \
  /Users/charvin/Projects/ai-delivery-admin/mcp-server \
  /Users/charvin/Projects/ai-delivery-admin/skills \
  /Users/charvin/Projects/ai-delivery-admin/data
```

Expected: all directories exist with no errors

**Step 4: Initialize the admin repository**

Run:

```bash
git init -b main /Users/charvin/Projects/ai-delivery-admin
```

Expected: the new project becomes a git repository with `main` as the default branch

**Step 5: Write the boundary docs and root ignore files**

The root files should establish:

- `node_modules/`, `dist/`, `.vite/`, `.DS_Store`, and `data/*.sqlite*` are ignored
- `README.md` explains this project binds to business repositories and does not own `.ai-delivery/` truth
- `mcp-server/README.md` explicitly says this directory is owned by this admin plan and contains the governed MCP tool surface
- `skills/README.md` explicitly says this directory owns only the admin support skill and never the three project-local workflow skills

**Step 6: Review the skeleton**

Run:

```bash
find /Users/charvin/Projects/ai-delivery-admin -maxdepth 3 -print | sort
```

Expected: only the planned directories and root files appear

**Step 7: Commit**

```bash
git -C /Users/charvin/Projects/ai-delivery-admin add .
git -C /Users/charvin/Projects/ai-delivery-admin commit -m "chore: scaffold ai-delivery-admin workspace"
```

### Task 2: Bootstrap The Root Toolchain And Smoke-Test The Workspace

**Files:**
- Create: `/Users/charvin/Projects/ai-delivery-admin/package.json`
- Create: `/Users/charvin/Projects/ai-delivery-admin/tsconfig.base.json`
- Create: `/Users/charvin/Projects/ai-delivery-admin/vitest.config.ts`
- Create: `/Users/charvin/Projects/ai-delivery-admin/web/index.html`
- Create: `/Users/charvin/Projects/ai-delivery-admin/web/vite.config.ts`
- Create: `/Users/charvin/Projects/ai-delivery-admin/web/tsconfig.json`
- Create: `/Users/charvin/Projects/ai-delivery-admin/server/tsconfig.json`
- Create: `/Users/charvin/Projects/ai-delivery-admin/shared/tsconfig.json`
- Create: `/Users/charvin/Projects/ai-delivery-admin/adapters/tsconfig.json`
- Create: `/Users/charvin/Projects/ai-delivery-admin/web/src/main.tsx`
- Create: `/Users/charvin/Projects/ai-delivery-admin/web/src/App.tsx`
- Create: `/Users/charvin/Projects/ai-delivery-admin/web/src/styles.css`
- Create: `/Users/charvin/Projects/ai-delivery-admin/tests/web/smoke.test.tsx`

**Step 1: Write the root `package.json`**

Include at least these scripts:

- `dev:web`
- `dev:server`
- `test`
- `typecheck`
- `build:web`

Include these dependencies:

- `react`
- `react-dom`
- `hono`
- `zod`
- `better-sqlite3`

Include these dev dependencies:

- `typescript`
- `vite`
- `vitest`
- `jsdom`
- `@testing-library/react`
- `@testing-library/jest-dom`
- `@vitejs/plugin-react`
- `tsx`
- `@types/node`
- `@types/react`
- `@types/react-dom`

**Step 2: Install the dependencies**

Run:

```bash
cd /Users/charvin/Projects/ai-delivery-admin && npm install
```

Expected: install completes successfully and creates `package-lock.json`

**Step 3: Write the TypeScript and Vite config files**

The config should support:

- a single root TypeScript baseline
- source folders under `shared/`, `adapters/`, `server/`, and `web/`
- Vitest in `jsdom` mode for web tests
- React rendering from `web/src/main.tsx`

**Step 4: Write a minimal app shell and failing smoke test**

Use this test shape:

```tsx
import { render, screen } from '@testing-library/react'
import App from '../../web/src/App'

test('renders the admin shell heading', () => {
  render(<App />)
  expect(screen.getByRole('heading', { name: /ai delivery admin/i })).toBeInTheDocument()
})
```

**Step 5: Run the smoke test and make it pass**

Run:

```bash
cd /Users/charvin/Projects/ai-delivery-admin && npm run test -- tests/web/smoke.test.tsx
```

Expected: PASS

**Step 6: Run the root typecheck**

Run:

```bash
cd /Users/charvin/Projects/ai-delivery-admin && npm run typecheck
```

Expected: PASS

**Step 7: Commit**

```bash
git -C /Users/charvin/Projects/ai-delivery-admin add .
git -C /Users/charvin/Projects/ai-delivery-admin commit -m "chore: bootstrap admin toolchain"
```

### Task 3: Define Shared Domain Schemas And Contract Parsers

**Files:**
- Create: `/Users/charvin/Projects/ai-delivery-admin/shared/src/schemas/project.ts`
- Create: `/Users/charvin/Projects/ai-delivery-admin/shared/src/schemas/runtime.ts`
- Create: `/Users/charvin/Projects/ai-delivery-admin/shared/src/schemas/requirement.ts`
- Create: `/Users/charvin/Projects/ai-delivery-admin/shared/src/schemas/event.ts`
- Create: `/Users/charvin/Projects/ai-delivery-admin/shared/src/schemas/blocker.ts`
- Create: `/Users/charvin/Projects/ai-delivery-admin/shared/src/schemas/artifact.ts`
- Create: `/Users/charvin/Projects/ai-delivery-admin/shared/src/index.ts`
- Create: `/Users/charvin/Projects/ai-delivery-admin/tests/fixtures/project-valid/.ai-delivery/meta/project-binding.json`
- Create: `/Users/charvin/Projects/ai-delivery-admin/tests/fixtures/project-valid/.ai-delivery/meta/naming-rules.json`
- Create: `/Users/charvin/Projects/ai-delivery-admin/tests/fixtures/project-valid/.ai-delivery/meta/workflow-policy.json`
- Create: `/Users/charvin/Projects/ai-delivery-admin/tests/fixtures/project-valid/.ai-delivery/runtime/main-branch.json`
- Create: `/Users/charvin/Projects/ai-delivery-admin/tests/fixtures/project-valid/.ai-delivery/runtime/dependency-graph.json`
- Create: `/Users/charvin/Projects/ai-delivery-admin/tests/fixtures/project-valid/.ai-delivery/runtime/worktrees.json`
- Create: `/Users/charvin/Projects/ai-delivery-admin/tests/fixtures/project-valid/.ai-delivery/runtime/task-board.json`
- Create: `/Users/charvin/Projects/ai-delivery-admin/tests/fixtures/project-valid/.ai-delivery/runtime/blockers.json`
- Create: `/Users/charvin/Projects/ai-delivery-admin/tests/fixtures/project-valid/.ai-delivery/runtime/merge-queue.json`
- Create: `/Users/charvin/Projects/ai-delivery-admin/tests/fixtures/project-valid/.specify/README.md`
- Create: `/Users/charvin/Projects/ai-delivery-admin/tests/shared/contracts.test.ts`

**Step 1: Create fixture files that mirror the current `.ai-delivery/` contract**

The fixture should include:

- valid `meta` files
- valid `runtime` files
- a minimal `.specify/` placeholder
- deterministic IDs and version fields

**Step 2: Write failing schema tests**

The tests should verify that:

- valid fixture JSON parses successfully
- missing required keys are rejected
- illegal state strings are rejected
- event objects require `event_id`, `timestamp`, `session_type`, and `event_type`
- artifact update payloads require explicit `version`, `updated_at`, and `updated_by`

**Step 3: Implement the zod schema modules**

The schemas must cover at least:

- project binding
- naming rules
- workflow policy
- runtime collections
- requirement summary shapes used by adapters
- execution event shape
- blocker shape
- artifact update payload shape

**Step 4: Re-export the shared contracts through `shared/src/index.ts`**

Expected: server, adapters, and web can all import the same schema definitions from one place

**Step 5: Run the shared-contract tests**

Run:

```bash
cd /Users/charvin/Projects/ai-delivery-admin && npm run test -- tests/shared/contracts.test.ts
```

Expected: PASS

**Step 6: Commit**

```bash
git -C /Users/charvin/Projects/ai-delivery-admin add .
git -C /Users/charvin/Projects/ai-delivery-admin commit -m "feat: add shared admin schemas"
```

### Task 4: Implement Local Binding Persistence And Filesystem Path Utilities

**Files:**
- Create: `/Users/charvin/Projects/ai-delivery-admin/server/src/persistence/db.ts`
- Create: `/Users/charvin/Projects/ai-delivery-admin/server/src/persistence/bindings-store.ts`
- Create: `/Users/charvin/Projects/ai-delivery-admin/adapters/src/filesystem.ts`
- Create: `/Users/charvin/Projects/ai-delivery-admin/tests/server/bindings-store.test.ts`
- Create: `/Users/charvin/Projects/ai-delivery-admin/tests/adapters/filesystem.test.ts`

**Step 1: Write failing tests for binding persistence**

The tests should verify that:

- a project binding can be inserted and read back
- re-binding the same `project_id` updates rather than duplicates
- default main branch is persisted
- the SQLite file is created under `/Users/charvin/Projects/ai-delivery-admin/data/admin.sqlite` in real runs and under a temp path in tests

**Step 2: Write failing tests for filesystem path helpers**

The tests should verify that:

- project root resolution is deterministic
- `.specify/` and `.ai-delivery/` paths are derived from the binding config
- missing directories are rejected with actionable errors

**Step 3: Implement the SQLite bootstrap and binding store**

The store should support at least:

- `upsertBinding`
- `listBindings`
- `getBindingByProjectId`
- `deleteBinding`

**Step 4: Implement the filesystem helpers**

The helpers should expose at least:

- `resolveProjectPaths(binding)`
- `requireReadableProject(binding)`
- `readJsonFile(path, schema)`
- `readOptionalMarkdown(path)`

**Step 5: Run the targeted tests**

Run:

```bash
cd /Users/charvin/Projects/ai-delivery-admin && npm run test -- tests/server/bindings-store.test.ts tests/adapters/filesystem.test.ts
```

Expected: PASS

**Step 6: Commit**

```bash
git -C /Users/charvin/Projects/ai-delivery-admin add .
git -C /Users/charvin/Projects/ai-delivery-admin commit -m "feat: add binding persistence and filesystem helpers"
```

### Task 5: Build Read-Only Adapters For Overview, Requirements, Traceability, Blockers, And Logs

**Files:**
- Create: `/Users/charvin/Projects/ai-delivery-admin/adapters/src/project-overview.ts`
- Create: `/Users/charvin/Projects/ai-delivery-admin/adapters/src/requirements.ts`
- Create: `/Users/charvin/Projects/ai-delivery-admin/adapters/src/traceability.ts`
- Create: `/Users/charvin/Projects/ai-delivery-admin/adapters/src/blockers.ts`
- Create: `/Users/charvin/Projects/ai-delivery-admin/adapters/src/events.ts`
- Create: `/Users/charvin/Projects/ai-delivery-admin/adapters/src/index.ts`
- Create: `/Users/charvin/Projects/ai-delivery-admin/tests/adapters/project-overview.test.ts`
- Create: `/Users/charvin/Projects/ai-delivery-admin/tests/adapters/requirements.test.ts`
- Create: `/Users/charvin/Projects/ai-delivery-admin/tests/adapters/traceability.test.ts`
- Create: `/Users/charvin/Projects/ai-delivery-admin/tests/adapters/events.test.ts`

**Step 1: Extend the fixture project with one requirement and one blocker**

Create enough fixture content to exercise:

- one requirement
- one sub-requirement
- one `traceability.json`
- one `interaction-design.md`
- one blocker item
- one NDJSON event line

**Step 2: Write failing adapter tests**

The tests should verify that adapters can:

- count requirements and sub-requirements for the dashboard
- enumerate requirements and sub-requirements with their current state
- return one traceability chain from Requirement to runtime state
- parse `events.ndjson` into ordered execution events
- surface blockers with type, state, and affected scope

**Step 3: Implement the read adapters**

Expected responsibilities:

- `project-overview.ts` computes dashboard counts and summary cards
- `requirements.ts` reads requirement trees and sub-requirement details
- `traceability.ts` assembles the Requirement -> SubRequirement -> Figma -> Interaction -> Runtime chain
- `blockers.ts` reads and normalizes blocker lists
- `events.ts` parses NDJSON and returns typed event collections

**Step 4: Run the adapter tests**

Run:

```bash
cd /Users/charvin/Projects/ai-delivery-admin && npm run test -- tests/adapters/project-overview.test.ts tests/adapters/requirements.test.ts tests/adapters/traceability.test.ts tests/adapters/events.test.ts
```

Expected: PASS

**Step 5: Commit**

```bash
git -C /Users/charvin/Projects/ai-delivery-admin add .
git -C /Users/charvin/Projects/ai-delivery-admin commit -m "feat: add read adapters for admin views"
```

### Task 6: Expose The Core Read APIs Through The Local Hono Server

**Files:**
- Create: `/Users/charvin/Projects/ai-delivery-admin/server/src/app.ts`
- Create: `/Users/charvin/Projects/ai-delivery-admin/server/src/index.ts`
- Create: `/Users/charvin/Projects/ai-delivery-admin/server/src/services/project-service.ts`
- Create: `/Users/charvin/Projects/ai-delivery-admin/server/src/routes/health.ts`
- Create: `/Users/charvin/Projects/ai-delivery-admin/server/src/routes/projects.ts`
- Create: `/Users/charvin/Projects/ai-delivery-admin/server/src/routes/requirements.ts`
- Create: `/Users/charvin/Projects/ai-delivery-admin/server/src/routes/logs.ts`
- Create: `/Users/charvin/Projects/ai-delivery-admin/server/src/routes/blockers.ts`
- Create: `/Users/charvin/Projects/ai-delivery-admin/tests/server/read-api.test.ts`

**Step 1: Write failing server tests**

The tests should verify these endpoints:

- `GET /health`
- `GET /api/projects`
- `POST /api/projects/bind`
- `GET /api/projects/:projectId/overview`
- `GET /api/projects/:projectId/requirements`
- `GET /api/projects/:projectId/sub-requirements`
- `GET /api/projects/:projectId/sub-requirements/:subreqId`
- `GET /api/projects/:projectId/blockers`
- `GET /api/projects/:projectId/events`

Use `app.request()` so the tests stay local and do not require a running server process.

**Step 2: Implement the service layer and route handlers**

The service layer should:

- load the bound project
- call the adapters
- return normalized JSON payloads
- convert missing-project and invalid-binding situations into clear HTTP errors

**Step 3: Add one real-project smoke binding for `/Users/charvin/Projects/Codex`**

The tests or smoke script should verify that the real host project can be bound and read without copying its data.

**Step 4: Run the read API tests**

Run:

```bash
cd /Users/charvin/Projects/ai-delivery-admin && npm run test -- tests/server/read-api.test.ts
```

Expected: PASS

**Step 5: Commit**

```bash
git -C /Users/charvin/Projects/ai-delivery-admin add .
git -C /Users/charvin/Projects/ai-delivery-admin commit -m "feat: add admin read APIs"
```

### Task 7: Implement Governed Write APIs For Logs, Artifacts, Blockers, And Status Transitions

**Files:**
- Create: `/Users/charvin/Projects/ai-delivery-admin/server/src/services/event-service.ts`
- Create: `/Users/charvin/Projects/ai-delivery-admin/server/src/services/artifact-service.ts`
- Create: `/Users/charvin/Projects/ai-delivery-admin/server/src/services/transition-service.ts`
- Create: `/Users/charvin/Projects/ai-delivery-admin/server/src/services/blocker-service.ts`
- Create: `/Users/charvin/Projects/ai-delivery-admin/server/src/routes/events-write.ts`
- Create: `/Users/charvin/Projects/ai-delivery-admin/server/src/routes/artifacts.ts`
- Create: `/Users/charvin/Projects/ai-delivery-admin/server/src/routes/transitions.ts`
- Create: `/Users/charvin/Projects/ai-delivery-admin/server/src/routes/blocker-actions.ts`
- Create: `/Users/charvin/Projects/ai-delivery-admin/tests/server/write-api.test.ts`

**Step 1: Write failing tests for governed writes**

The tests should verify that the server:

- appends execution events to `events.ndjson`
- rejects an event write when required fields are missing
- updates an editable artifact only when the provided version matches the current file version
- rejects illegal state transitions
- creates or updates blockers when a transition is invalid
- resolves blockers through an explicit blocker action endpoint

**Step 2: Implement the write services**

The services should support at least:

- append execution log entries
- update editable markdown or JSON artifacts through a controlled file map
- validate sub-requirement status transitions against the approved state machine
- detect blockers already attached to a sub-requirement before allowing progress
- write optimistic-concurrency metadata back to edited artifacts

**Step 3: Implement the write routes**

Expose at least:

- `POST /api/projects/:projectId/events`
- `PUT /api/projects/:projectId/artifacts`
- `POST /api/projects/:projectId/sub-requirements/:subreqId/transitions`
- `PATCH /api/projects/:projectId/blockers/:blockerId`

**Step 4: Run the write API tests**

Run:

```bash
cd /Users/charvin/Projects/ai-delivery-admin && npm run test -- tests/server/write-api.test.ts
```

Expected: PASS

**Step 5: Commit**

```bash
git -C /Users/charvin/Projects/ai-delivery-admin add .
git -C /Users/charvin/Projects/ai-delivery-admin commit -m "feat: add governed admin write APIs"
```

### Task 8: Build The React Shell, API Client, And Project Navigation

**Files:**
- Modify: `/Users/charvin/Projects/ai-delivery-admin/web/src/App.tsx`
- Create: `/Users/charvin/Projects/ai-delivery-admin/web/src/lib/api.ts`
- Create: `/Users/charvin/Projects/ai-delivery-admin/web/src/lib/types.ts`
- Create: `/Users/charvin/Projects/ai-delivery-admin/web/src/components/Layout.tsx`
- Create: `/Users/charvin/Projects/ai-delivery-admin/web/src/components/Sidebar.tsx`
- Create: `/Users/charvin/Projects/ai-delivery-admin/web/src/components/ProjectSelector.tsx`
- Create: `/Users/charvin/Projects/ai-delivery-admin/web/src/pages/DashboardPage.tsx`
- Create: `/Users/charvin/Projects/ai-delivery-admin/web/src/pages/RequirementExplorerPage.tsx`
- Create: `/Users/charvin/Projects/ai-delivery-admin/web/src/pages/LogsTimelinePage.tsx`
- Create: `/Users/charvin/Projects/ai-delivery-admin/web/src/pages/BlockerCenterPage.tsx`
- Create: `/Users/charvin/Projects/ai-delivery-admin/tests/web/navigation.test.tsx`

**Step 1: Write failing UI tests for the admin shell**

The tests should verify that the shell:

- renders a project selector
- renders nav links for Dashboard, Requirements, Logs, and Blockers
- loads the dashboard by default once a project is selected

**Step 2: Implement the API client**

The client should expose typed functions for:

- listing bound projects
- binding a project
- loading overview data
- loading requirements
- loading blockers
- loading events

**Step 3: Implement the layout and initial pages**

The first-pass pages should show real data, even if minimally styled:

- dashboard cards from overview API
- requirement tree list from requirement API
- log rows from event API
- blocker list from blocker API

**Step 4: Run the web-shell tests**

Run:

```bash
cd /Users/charvin/Projects/ai-delivery-admin && npm run test -- tests/web/navigation.test.tsx
```

Expected: PASS

**Step 5: Commit**

```bash
git -C /Users/charvin/Projects/ai-delivery-admin add .
git -C /Users/charvin/Projects/ai-delivery-admin commit -m "feat: add admin shell and primary pages"
```

### Task 9: Add Execution Board, Traceability View, And Artifact Editor

**Files:**
- Create: `/Users/charvin/Projects/ai-delivery-admin/web/src/pages/ExecutionBoardPage.tsx`
- Create: `/Users/charvin/Projects/ai-delivery-admin/web/src/pages/TraceabilityPage.tsx`
- Create: `/Users/charvin/Projects/ai-delivery-admin/web/src/pages/ArtifactEditorPage.tsx`
- Create: `/Users/charvin/Projects/ai-delivery-admin/web/src/components/StatusBadge.tsx`
- Create: `/Users/charvin/Projects/ai-delivery-admin/web/src/components/ArtifactEditor.tsx`
- Create: `/Users/charvin/Projects/ai-delivery-admin/web/src/components/TraceabilityChain.tsx`
- Create: `/Users/charvin/Projects/ai-delivery-admin/tests/web/execution-board.test.tsx`
- Create: `/Users/charvin/Projects/ai-delivery-admin/tests/web/traceability.test.tsx`
- Create: `/Users/charvin/Projects/ai-delivery-admin/tests/web/artifact-editor.test.tsx`

**Step 1: Write failing tests for the advanced pages**

The tests should verify that:

- the execution board groups items by state and shows blockers or merge-queue signals
- the traceability view renders Requirement -> SubRequirement -> Figma -> Interaction -> Runtime links
- the artifact editor can load one editable artifact and submit a versioned update payload

**Step 2: Implement the missing server payload support if the web layer needs it**

If required, extend the existing read or write routes, but do not introduce MCP-specific semantics.

**Step 3: Implement the React pages and supporting components**

The artifact editor must support at least:

- `requirement-slice.md`
- `figma-mapping.md`
- `interaction-design.md`
- `status.json`
- `dependency.json`
- `decisions.md`

The execution board must visualize at least:

- sub-requirement state
- dependency wave information
- blocker presence
- worktree or merge-queue occupancy when present

**Step 4: Run the advanced-page tests**

Run:

```bash
cd /Users/charvin/Projects/ai-delivery-admin && npm run test -- tests/web/execution-board.test.tsx tests/web/traceability.test.tsx tests/web/artifact-editor.test.tsx
```

Expected: PASS

**Step 5: Commit**

```bash
git -C /Users/charvin/Projects/ai-delivery-admin add .
git -C /Users/charvin/Projects/ai-delivery-admin commit -m "feat: add execution board traceability and artifact editing"
```

### Task 10: Run End-To-End Verification Against The Real Codex Project And Document The Handoff

**Files:**
- Modify: `/Users/charvin/Projects/ai-delivery-admin/README.md`
- Create: `/Users/charvin/Projects/ai-delivery-admin/tests/server/codex-smoke.test.ts`
- Create: `/Users/charvin/Projects/ai-delivery-admin/tests/web/codex-smoke.test.tsx`

**Step 1: Add a real-project smoke test for `/Users/charvin/Projects/Codex`**

The smoke test should verify that the admin app can:

- bind `/Users/charvin/Projects/Codex`
- read its `.ai-delivery/meta/` and `.ai-delivery/runtime/` files
- return a non-error overview payload

**Step 2: Add a minimal web smoke test**

The web smoke test should verify that the dashboard can render a real bound project without crashing.

**Step 3: Run the full verification suite**

Run:

```bash
cd /Users/charvin/Projects/ai-delivery-admin && npm run test && npm run typecheck && npm run build:web
```

Expected: all commands pass

**Step 4: Run one local server smoke command**

Run:

```bash
cd /Users/charvin/Projects/ai-delivery-admin && npm run dev:server
```

In a separate shell, verify:

```bash
curl http://127.0.0.1:3000/health
```

Expected: a healthy JSON response

**Step 5: Update `README.md`**

Document at least:

- project purpose and ownership boundary
- how to install dependencies
- how to bind `/Users/charvin/Projects/Codex`
- how to run the server and web app locally
- where the admin support skill and MCP server live

**Step 6: Commit**

```bash
git -C /Users/charvin/Projects/ai-delivery-admin add .
git -C /Users/charvin/Projects/ai-delivery-admin commit -m "docs: finalize admin implementation baseline"
```

### Task 11: Implement The Admin Support Skill And Local Install Script

**Files:**
- Create: `/Users/charvin/Projects/ai-delivery-admin/skills/ai-delivery-admin-support/SKILL.md`
- Create: `/Users/charvin/Projects/ai-delivery-admin/skills/ai-delivery-admin-support/references/tool-usage-order.md`
- Create: `/Users/charvin/Projects/ai-delivery-admin/skills/ai-delivery-admin-support/references/failure-policy.md`
- Create: `/Users/charvin/Projects/ai-delivery-admin/scripts/install-admin-support-skill.sh`
- Create: `/Users/charvin/Projects/ai-delivery-admin/tests/skills/admin-support-skill.test.ts`

**Step 1: Write the failing admin-support-skill test**

The test should verify that the support skill documentation references:

- project binding
- dependency check before action
- log append before and after significant execution steps
- blocker escalation instead of silent inference
- MCP usage instead of raw file mutation for governed writes

**Step 2: Write the admin support skill package**

The support skill must teach agents to:

- bind the target project first
- inspect blockers and dependency readiness before acting
- append execution logs consistently
- use governed MCP operations for state changes and artifact writes
- stop when the system enters a blocker state

**Step 3: Write the install script**

The install script should expose only the admin support skill from `/Users/charvin/Projects/ai-delivery-admin/skills/ai-delivery-admin-support/`.

**Step 4: Run the admin-support-skill test**

Run:

```bash
cd /Users/charvin/Projects/ai-delivery-admin && npm run test -- tests/skills/admin-support-skill.test.ts
```

Expected: PASS

**Step 5: Commit**

```bash
git -C /Users/charvin/Projects/ai-delivery-admin add skills scripts tests/skills
git -C /Users/charvin/Projects/ai-delivery-admin commit -m "feat: add admin support skill"
```

### Task 12: Extend The Admin Toolchain And Implement The MCP Server Core

**Files:**
- Modify: `/Users/charvin/Projects/ai-delivery-admin/package.json`
- Modify: `/Users/charvin/Projects/ai-delivery-admin/tsconfig.base.json`
- Create: `/Users/charvin/Projects/ai-delivery-admin/mcp-server/tsconfig.json`
- Create: `/Users/charvin/Projects/ai-delivery-admin/mcp-server/src/index.ts`
- Create: `/Users/charvin/Projects/ai-delivery-admin/mcp-server/src/server.ts`
- Create: `/Users/charvin/Projects/ai-delivery-admin/mcp-server/src/tool-registry.ts`
- Create: `/Users/charvin/Projects/ai-delivery-admin/mcp-server/src/context.ts`
- Create: `/Users/charvin/Projects/ai-delivery-admin/tests/mcp/server-core.test.ts`

**Step 1: Write the failing MCP server core test**

The test should verify that the server:

- boots without starting the transport in test mode
- registers the expected tool names
- can construct a project-bound context without bypassing the admin layer

**Step 2: Extend the admin root toolchain**

Add at least:

- the `@modelcontextprotocol/sdk` dependency
- `dev:mcp` and `test:mcp` scripts
- any required TypeScript path or include rules for `mcp-server/`

**Step 3: Implement the MCP server core modules**

The core must:

- bootstrap the SDK server
- register tool handlers through one registry
- reuse shared schemas where possible
- rely on admin services or governed APIs rather than re-parsing `.ai-delivery/` directly inside tool handlers

**Step 4: Run the MCP core test**

Run:

```bash
cd /Users/charvin/Projects/ai-delivery-admin && npm run test -- tests/mcp/server-core.test.ts
```

Expected: PASS

**Step 5: Commit**

```bash
git -C /Users/charvin/Projects/ai-delivery-admin add package.json tsconfig.base.json mcp-server tests/mcp
git -C /Users/charvin/Projects/ai-delivery-admin commit -m "feat: add mcp server core"
```

### Task 13: Implement The Read-Oriented MCP Tool Surface

**Files:**
- Create: `/Users/charvin/Projects/ai-delivery-admin/mcp-server/src/tools/bind-project.ts`
- Create: `/Users/charvin/Projects/ai-delivery-admin/mcp-server/src/tools/project-overview.ts`
- Create: `/Users/charvin/Projects/ai-delivery-admin/mcp-server/src/tools/requirements.ts`
- Create: `/Users/charvin/Projects/ai-delivery-admin/mcp-server/src/tools/sub-requirements.ts`
- Create: `/Users/charvin/Projects/ai-delivery-admin/mcp-server/src/tools/blockers.ts`
- Create: `/Users/charvin/Projects/ai-delivery-admin/mcp-server/src/tools/traceability.ts`
- Create: `/Users/charvin/Projects/ai-delivery-admin/tests/mcp/read-tools.test.ts`

**Step 1: Write failing read-tool tests**

The tests should verify these tool handlers:

- `bind_project`
- `get_project_overview`
- `list_requirements`
- `list_sub_requirements`
- `get_sub_requirement_detail`
- `list_blockers`
- `read_traceability`

**Step 2: Implement the read tools as thin adapters over governed admin services**

The handlers must:

- validate inputs with shared schemas
- operate on one bound project at a time
- return normalized results for agent consumption
- avoid direct raw file traversal in tool code when the admin service layer already owns that logic

**Step 3: Run the read-tool tests**

Run:

```bash
cd /Users/charvin/Projects/ai-delivery-admin && npm run test -- tests/mcp/read-tools.test.ts
```

Expected: PASS

**Step 4: Commit**

```bash
git -C /Users/charvin/Projects/ai-delivery-admin add mcp-server tests/mcp
git -C /Users/charvin/Projects/ai-delivery-admin commit -m "feat: add read-oriented mcp tools"
```

### Task 14: Implement The Governed Write And Workflow-Control MCP Tools

**Files:**
- Create: `/Users/charvin/Projects/ai-delivery-admin/mcp-server/src/tools/events.ts`
- Create: `/Users/charvin/Projects/ai-delivery-admin/mcp-server/src/tools/transitions.ts`
- Create: `/Users/charvin/Projects/ai-delivery-admin/mcp-server/src/tools/worktrees.ts`
- Create: `/Users/charvin/Projects/ai-delivery-admin/mcp-server/src/tools/artifacts.ts`
- Create: `/Users/charvin/Projects/ai-delivery-admin/tests/mcp/write-tools.test.ts`

**Step 1: Write failing write-tool tests**

The tests should verify these tool handlers:

- `append_execution_log`
- `transition_sub_requirement_status`
- `check_dependency_ready`
- `reserve_worktree_slot`
- `record_worktree_created`
- `record_commit`
- `record_merge_result`
- `upsert_artifact`

The tests must also verify that illegal transitions or stale writes return governed errors rather than silent success.

**Step 2: Implement the write/control tools**

The handlers must:

- call the existing governed admin services
- preserve version checks and blocker behavior
- surface actionable failure messages to agents
- refuse silent writes when logging or transition checks fail

**Step 3: Run the write-tool tests**

Run:

```bash
cd /Users/charvin/Projects/ai-delivery-admin && npm run test -- tests/mcp/write-tools.test.ts
```

Expected: PASS

**Step 4: Commit**

```bash
git -C /Users/charvin/Projects/ai-delivery-admin add mcp-server tests/mcp
git -C /Users/charvin/Projects/ai-delivery-admin commit -m "feat: add governed write mcp tools"
```

### Task 15: Add End-To-End MCP Verification, Usage Docs, And Handoff Guides

**Files:**
- Modify: `/Users/charvin/Projects/ai-delivery-admin/README.md`
- Modify: `/Users/charvin/Projects/ai-delivery-admin/mcp-server/README.md`
- Modify: `/Users/charvin/Projects/ai-delivery-admin/skills/README.md`
- Create: `/Users/charvin/Projects/ai-delivery-admin/tests/mcp/codex-smoke.test.ts`

**Step 1: Write the end-to-end smoke test**

The smoke test should verify that:

- the admin MCP server can bind `/Users/charvin/Projects/Codex`
- the read tool chain returns data from the real project without crashing
- one governed write path, such as `append_execution_log`, succeeds against the real project contract

**Step 2: Run the full verification suite**

Run:

```bash
cd /Users/charvin/Projects/ai-delivery-admin && npm run test && npm run typecheck
```

Expected: all commands pass

**Step 3: Update the usage docs**

Document at least:

- where the admin support skill lives
- where the MCP server lives
- how to install the admin support skill locally
- how to run the MCP server locally
- how project-local skills are expected to cooperate with the admin support surfaces during execution

**Step 4: Commit**

```bash
git -C /Users/charvin/Projects/ai-delivery-admin add README.md mcp-server skills scripts tests/mcp tests/skills
git -C /Users/charvin/Projects/ai-delivery-admin commit -m "docs: finalize admin support and mcp baseline"
```

## Handoff After Implementation

After this plan is implemented and verified, the next eligible execution plan is:

- `ai-delivery-skills implementation plan`
- later, an `integration repair / full-chain verification plan`

That downstream plan may consume the admin project's:

- shared schemas
- validated server APIs
- project-binding workflow
- governed artifact update endpoints
- blocker and event surfaces

It must not retroactively redefine the admin plan's ownership boundary. If the later project-local skills track needs the admin server to expose an additional capability, that addition should first be reconciled against the governing master plan at `/Users/charvin/Projects/Codex/docs/plans/2026-04-04-ai-delivery-implementation-plan.md`.

This admin plan alone does not guarantee full-chain closure. Requirement bootstrap coverage, blocked-state recovery, merge finalization, and Spec Kit bridge verification must still be reconciled by the later integration repair / full-chain verification track.
