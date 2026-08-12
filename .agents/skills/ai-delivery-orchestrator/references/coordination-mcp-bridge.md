# Coordination MCP bridge

`ai-delivery-coordination/` is a **separate deployable engine** companion to ai-delivery-kit. The skill layer must never `import` its Python modules. All autonomous execution goes through **MCP tools** on a running coordination server.

## When to use

- Long-running ECC-style implement loops with checkpoint recovery, stall monitoring, and cost budgets
- Human-in-the-loop intervention (`intervene_loop`) without rewriting `status.json` by hand

Normal governed delivery still flows through reconcile + abstract actions (`design` / `spec` / `implement` / `finish` / `archive`). Loop mode is optional and **never** bypasses gates, `verification.md`, or CP-ARCHIVE.

## MCP tools

| Tool | Purpose |
|------|---------|
| `start_loop` | `req_root` → load `status.json` via `skill_bridge`, start `LoopRunner` |
| `stop_loop` | Cancel runner |
| `loop_status` | Inspect runner + node states |
| `stall_report` | ALR-1/2/4/15 stall visibility |
| `intervene_loop` | Human-only: `pause`, `resume`, `cancel`, `retry_node`, `skip_node`, `approve_overbudget` |

`resume` and `approve_overbudget` **require** a non-empty `reason` (audit trail).

## Truth boundaries

| Layer | Owns |
|-------|------|
| Skill (`status.json`) | Spec segment: `draft` … `tasks_ready`, `archived`, CP checkpoints |
| Coordination engine | Execution view: `in_dev`, `merged`, `blocked_*` |
| `skill_bridge.flush_back` | Writes **only** execution-segment statuses, then runs `reconcile-delivery.py` |

The engine does not cache reconcile conclusions; after every flush, reconcile re-derives `next_action`.

## Operator checklist

1. Confirm reconcile queue is sane (`tasks_ready` + CP-001 cleared before heavy autonomy).
2. `start_loop` with absolute `req_root`.
3. Monitor `loop_status` / `stall_report`; use `intervene_loop` on stalls or budget (ALR-15).
4. When slices reach `merged`, return to skill-layer `finish` / `archive` — loop runner does **not** auto-archive.

Implementation reference ([ai-delivery-coordination](https://github.com/s-charvin/ai-delivery-coordination) repo): `orchestration/skill_bridge.py`, `mcp/loop_registry.py`.
