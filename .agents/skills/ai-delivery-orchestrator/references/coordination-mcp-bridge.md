# Coordination MCP bridge

`ai-delivery-coordination/` is a **separate deployable engine** companion to ai-delivery-kit. The skill layer must never `import` its Python modules. All autonomous execution goes through **MCP tools** on a running coordination server.

## Lightweight principles (AI-first)

Coordination is a **status + protocol** layer, not an artifact-format police:

| Principle | Meaning |
|-----------|---------|
| Storage autonomy | Business parties and hub operators choose their own storage (Git paths, S3, Figma, OpenSpec dirs, `.ai-delivery/`, …). Coordination does **not** validate schemas or directory trees. |
| Status + hints | When updating task status, optionally attach `context` / `artifact_hints` (free text or JSON — prompt-like enrichment). Coordination stores and forwards; it does **not** interpret semantics. |
| AI self-fetch | Consumers use `hub://` pointers + hints + their own context to fetch content. No forced content download; no automatic sha256 gates on register. |
| Hard protocol only | State-machine edges, claim leases, `hub://` parse, cross-pipeline acyclic checks, audit. |

Kit `.ai-delivery/` layout rules still apply to repos bootstrapped by `ai-delivery init`. Coordination does **not** export that layout to third-party hubs.

## When to use

- Long-running ECC-style implement loops with checkpoint recovery, stall monitoring, and cost budgets
- Cross-party task claim / status / dependency scheduling without sharing a filesystem
- Human-in-the-loop intervention (`intervene_loop`) without rewriting `status.json` by hand

Normal governed delivery still flows through reconcile + abstract actions (`design` / `spec` / `implement` / `finish` / `archive`). Loop mode is optional and **never** bypasses gates, `verification.md`, or CP-ARCHIVE.

## MCP tools — loops

| Tool | Purpose |
|------|---------|
| `start_loop` | `req_root` → load `status.json` via `skill_bridge`, start `LoopRunner` |
| `stop_loop` | Cancel runner |
| `loop_status` | Inspect runner + node states |
| `stall_report` | ALR-1/2/4/15 stall visibility |
| `intervene_loop` | Human-only: `pause`, `resume`, `cancel`, `retry_node`, `skip_node`, `approve_overbudget` |

`resume` and `approve_overbudget` **require** a non-empty `reason` (audit trail).

## MCP tools — hub pointers + claims

| Tool | Purpose |
|------|---------|
| `register_pipeline` | Register pipeline metadata (wraps `create_pipeline`) |
| `register_artifact_ref` | Register `hub://pipeline/node@version` + optional `uri` / `hints` (**pointer only**) |
| `resolve_hub_ref` | Resolve pointer → `{uri, version, hints, status}` — **no content fetch** |
| `list_artifact_refs` | List registered pointers |
| `claim_node` / `release_claim` | Lease-based claim (`E_ALREADY_CLAIMED` on conflict) |
| `report_node_status` | Legal status transition + optional `context` / `artifact_hints` |
| `list_claimable_nodes` | READY + unclaimed; upstream satisfaction (status / ref presence only) |
| `schedule_dependents` | After `done`, unlock BLOCKED→READY dependents; emit cross-pipeline notices |

### Task claim workflow

1. `register_pipeline` (once) → parties `register_artifact_ref` when they publish something others may need.
2. `list_claimable_nodes` → `claim_node`.
3. Do the work using whatever storage you already use; optionally `report_node_status` with `context` / `artifact_hints`.
4. When done (legal edge to `done`), `schedule_dependents` so others can claim.

### AI consumption guide

1. Call `resolve_hub_ref("hub://…")` or `list_claimable_nodes`.
2. Read `uri` + `hints` + `context`.
3. Clone / open / download yourself. If access fails, retry or ask a human — coordination does not guarantee reachability.

## Truth boundaries

| Layer | Owns |
|-------|------|
| Parties / hub | Artifact bytes and storage shape |
| Skill (`status.json`) | Spec segment: `draft` … `tasks_ready`, `archived`, CP checkpoints |
| Coordination STORE | Node state machine, claims/leases, dependency readiness |
| Coordination REFREG | `hub://` pointers + optional uri/hints (not content) |
| `skill_bridge.flush_back` | Writes **only** execution-segment statuses to kit `status.json`, then reconcile |

Cross-repo execution **must** go through coordination MCP — do not invent a local fake hub status.

## Operator checklist (loops)

1. Confirm reconcile queue is sane (`tasks_ready` + CP-001 cleared before heavy autonomy).
2. `start_loop` with absolute `req_root`.
3. Monitor `loop_status` / `stall_report`; use `intervene_loop` on stalls or budget (ALR-15).
4. When slices reach `merged`, return to skill-layer `finish` / `archive` — loop runner does **not** auto-archive.

Implementation reference ([ai-delivery-coordination](https://github.com/s-charvin/ai-delivery-coordination)): `orchestration/skill_bridge.py`, `mcp/loop_registry.py`, `mcp/ref_claim_tools.py`, `repo/hub_ref.py`.
