from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture
def env(tmp_path, monkeypatch):
    from mcp.state_store import STORE
    STORE.clear_all()

    monkeypatch.setenv("LANGFUSE_BASE_URL", "http://localhost:1")
    monkeypatch.setenv("COORDINATION_DEV_SECRET", "dev-secret-mvp-e2e")
    monkeypatch.setenv("COORDINATION_JWT_SECRET", "dev-secret-mvp-e2e")

    from repo.providers.local_provider import LocalHubRepo
    hub = LocalHubRepo(repo_root=tmp_path / "hub", init_bare_if_missing=True)

    from audit.worm_storage import WormStorage
    worm = WormStorage(tmp_path / "audit.sqlite3")

    from orchestration.locks import ThreadingLockImpl, Allocator
    locks = ThreadingLockImpl()
    allocator = Allocator(tmp_path / "seq.sqlite3", locks)

    from mcp.server import set_hub_repo
    set_hub_repo(hub)

    # Wire global stores (used by mcp.tools_phase2) to tmp_path so that
    # audit entries / aux db / pending sync / gate policies are isolated per test.
    import mcp.tools_phase2 as _tp2
    _tp2._WORM_STORE_VAR["instance"] = worm
    _tp2._AUX_DB_PATH_VAR["path"] = tmp_path / "aux_tools.db"
    _tp2._AUX_CONN_VAR["conn"] = None  # force re-create on next get_aux_conn()
    _tp2._PENDING_SYNC_DIR_VAR["path"] = tmp_path / "pending_sync"

    from orchestration.gate_policy import _GATE_STORE_VAR, GatePolicyStore
    _GATE_STORE_VAR["instance"] = GatePolicyStore()

    # Clear SSE queue for observability tests
    import monitoring.observability_server as _obs
    while not _obs._SSE_QUEUE.empty():
        try:
            _obs._SSE_QUEUE.get_nowait()
        except Exception:
            break

    return SimpleNamespace(
        tmp=tmp_path,
        hub=hub,
        worm=worm,
        locks=locks,
        alloc=allocator,
    )
