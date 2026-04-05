# AI Delivery Admin Runtime And MCP Daemon Design

## Goal

Simplify `ai-delivery-admin` local usage so one command can bring up the human-facing system end to end, while preserving a separate on-demand MCP entry for agent integration.

The approved direction is:

- no Docker
- one command starts `Web + API`
- MCP keeps its existing `stdio` entry for direct tool/agent use
- MCP also gains a locally managed daemon mode
- the Web console can start, stop, inspect, and read logs for that daemon mode through governed admin APIs

## Why This Design

The current admin project exposes multiple commands:

- `npm install`
- `npm run dev:server`
- `npm run dev:web`
- `npm run dev:mcp`
- `npm run test`
- `npm run typecheck`
- `npm run build:web`

That is workable for development, but not a good operator experience. The human-facing system should feel like a single local app, not a collection of separate terminal rituals.

At the same time, MCP is not identical to a normal Web/API service:

- the existing MCP entry is `stdio` oriented
- the admin console needs a controllable local runtime
- the Codex/agent side still benefits from a direct MCP entry

So the right split is:

- one-command startup for the human-facing surfaces
- two MCP runtime modes:
  - `stdio` mode for direct agent use
  - daemon mode for local runtime management and Web control

## Approach Options

### Option 1: Recommended

Add a local runtime supervisor plus a managed MCP daemon.

Characteristics:

- one new root command starts `Web + API`
- a small supervisor script auto-installs dependencies when needed, spawns both services, and waits for readiness
- API gains an MCP runtime manager that controls a daemonized MCP process
- Web adds runtime controls and log/status visibility
- existing `stdio` MCP entry remains available as a separate command

Why it fits:

- best operator experience
- keeps human runtime concerns and agent transport concerns both valid
- avoids Docker complexity around local project paths, Codex home, and transport semantics

Trade-offs:

- requires one new runtime-management layer
- requires child-process lifecycle handling and log persistence

### Option 2: Single Process Admin Server

Serve built Web assets directly from the API process and embed MCP management in that same process.

Why it is weaker:

- makes local development less ergonomic
- pushes frontend iteration into build/serve coupling too early
- increases restart cost for every frontend/backend tweak

### Option 3: External Process Manager

Use a third-party process manager or OS service wrapper to orchestrate `Web + API + MCP`.

Why it is weaker:

- adds more moving parts than the product needs
- pushes core operator behavior outside the repo
- makes onboarding and local troubleshooting harder

## Final Architecture

### Runtime Surfaces

`ai-delivery-admin` will expose three runtime surfaces:

1. `API Server`
   - existing Hono app
   - continues to own governed reads/writes
   - gains runtime-control routes for MCP daemon status and lifecycle

2. `Web Console`
   - continues to be the human-facing control plane
   - gains a runtime management card/page for MCP daemon lifecycle

3. `MCP`
   - `stdio` mode remains for direct Codex/agent integration
   - daemon mode runs as a local managed process and exposes a local transport suitable for long-lived control

### One-Command Local Startup

Add a single root command for operators:

- `npm run admin:start`

Backed by a Node-based supervisor script, not a shell-only script, so it is easier to keep cross-platform and testable.

Responsibilities:

- detect whether `node_modules` is present
- run `npm install` automatically if dependencies are missing
- spawn API and Web child processes
- wait for readiness checks
- print the final local URLs and runtime summary

Optional follow-up commands:

- `npm run admin:stop`
- `npm run admin:status`

But the key requirement is that `npm run admin:start` is the primary operator entry.

### MCP Runtime Model

The MCP subsystem will have two entrypoints:

1. `stdio entry`
   - current direct MCP entry
   - kept for Codex/agent configurations that expect a process command

2. `daemon entry`
   - new long-lived local MCP process
   - started and stopped by admin APIs
   - writes runtime metadata and rolling logs into admin-local data storage

The daemon mode exists so Web control is meaningful. A Web page cannot reliably manage a pure ad hoc `stdio` session and claim that the MCP service is truly usable. Daemon mode solves that by making the managed MCP runtime an actual local long-lived service.

### MCP Runtime Manager

Add a server-owned `mcp-runtime-service` layer.

Responsibilities:

- spawn the daemon process
- stop the daemon process gracefully
- detect whether the daemon is running
- collect:
  - pid
  - started_at
  - stopped_at
  - last_exit_code
  - current status
  - recent logs
- persist runtime metadata in admin-local `data/`

Suggested files:

- `data/mcp-runtime.json`
- `data/logs/mcp-daemon.log`

### Web Controls

The Web console will gain a dedicated runtime management surface.

Minimum capabilities:

- show daemon status: `running / stopped / starting / stopping / failed`
- show transport information for daemon mode
- show recent daemon logs
- start daemon
- stop daemon
- refresh status

The UI should make the two MCP modes explicit:

- `Daemon Mode`
  - controllable from Web
  - intended for local operator-managed runtime

- `Stdio Mode`
  - not Web-managed
  - intended for direct Codex/agent launcher integration

This prevents users from confusing “MCP exists” with “this exact transport is the one my client needs”.

## API Additions

Add governed runtime endpoints, for example:

- `GET /api/runtime/mcp`
- `POST /api/runtime/mcp/start`
- `POST /api/runtime/mcp/stop`
- `GET /api/runtime/mcp/logs`

These routes must remain admin-owned orchestration APIs, not direct raw process wrappers with no validation.

Rules:

- refuse duplicate starts if already running
- refuse stop if not running
- report actionable errors
- never silently discard logs or exit state

## Data Flow

### Human Path

1. Operator runs `npm run admin:start`
2. Supervisor ensures dependencies and starts `Web + API`
3. Operator opens Web console
4. Operator uses MCP runtime controls in Web
5. Web calls governed API routes
6. API runtime manager starts/stops daemon and returns state
7. Web renders current status and logs

### Agent Path

1. Agent or Codex can still use `stdio` MCP entry directly
2. Admin support skill continues to point governed write operations through admin-owned surfaces
3. When daemon mode is useful, humans can manage it through Web without replacing direct `stdio` usage

## Error Handling

### Startup

- if dependency install fails, supervisor exits with a clear summary
- if API or Web fails to become ready, supervisor stops the other child process and reports failure
- if one child exits after startup, supervisor reports degraded state

### MCP Daemon

- if daemon start fails, API records the failure and exposes the last error
- if daemon crashes, status becomes `failed` and the last exit code is preserved
- log tail remains visible for diagnosis

### Web

- runtime controls must show busy state and last known outcome
- runtime log view must tolerate empty logs

## Git Hygiene

`.idea/` should be ignored at the repo level before feature implementation continues, so local IDE metadata stops polluting git status and branch work.

## Testing Strategy

### Unit / Service Tests

- MCP runtime manager:
  - start success
  - duplicate start refusal
  - stop success
  - stop when not running
  - log/status persistence

### API Tests

- runtime status endpoint returns structured state
- start/stop endpoints enforce governance rules

### Web Tests

- runtime section renders status
- start/stop buttons trigger the expected API calls
- log panel renders recent output

### Smoke Tests

- one-command startup script reports both API and Web ready
- daemon mode can start and stop through governed APIs
- existing `stdio` MCP entry still boots independently

## Non-Goals

- Docker deployment
- replacing direct `stdio` MCP usage
- moving host-project `.ai-delivery/` truth into admin-local storage
- redesigning existing requirement/Figma governance
