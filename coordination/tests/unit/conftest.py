from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from mcp.state_store import STORE
from mcp.tools_phase2 import reset_test_singletons


@pytest.fixture(autouse=True)
def _reset_sqlite_singletons():
    """Prevent stale SQLite connections across unit tests (readonly database errors)."""
    data_dir = Path("data")
    reset_test_singletons()
    STORE.clear_all()
    if data_dir.exists():
        for name in (
            "aux_tools.db",
            "worm.db",
            "gate_policies.db",
        ):
            p = data_dir / name
            if p.exists():
                try:
                    p.unlink()
                except Exception:
                    pass
        pending = data_dir / "pending_sync"
        if pending.exists():
            try:
                shutil.rmtree(pending)
            except Exception:
                pass
    yield
    reset_test_singletons()
    STORE.clear_all()
