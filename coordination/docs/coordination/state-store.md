# PipelineStateStore (STORE)

`coordination/mcp/state_store.py` holds the in-process pipeline registry used by
the MCP tools (`STORE`).

## Volatile cache, SQLite-backed

STORE is a **volatile in-memory cache** whose durable backing is a local SQLite
database (`data/pipeline_state.db` by default, overridable via the `db_path`
constructor argument):

- `register(def, state)` and `set_state(pid, state)` are **write-through**: the
  pipeline definition and state are written to SQLite on every call, not just
  held in RAM.
- On construction the store calls `load_latest()`, which warms the in-memory
  `pipelines` / `states` maps from SQLite so a restarted process recovers the
  last persisted definitions and states instead of starting empty.

## What is and isn't durable

| Data | Durable (SQLite) | Notes |
| --- | --- | --- |
| `pipelines` (PipelineDefinition) | yes | written on `register` |
| `states` (PipelineState) | yes | written on `register` / `set_state` |
| `pending_prs` | no | short-lived operational queue, in-memory only |
| `pending_sync` | no | short-lived operational queue, in-memory only |

Because the operational queues are intentionally not persisted, STORE should be
treated as **best-effort state recovery**, not a system of record. SQLite is the
authoritative snapshot for definitions and states; the RAM maps are a cache for
fast access within a process lifetime.
