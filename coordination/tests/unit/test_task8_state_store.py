from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

from orchestration.models import (
    NodeDef,
    NodeState,
    NodeStatus,
    ParticipationProfile,
    PipelineDefinition,
    PipelineState,
    PipelineStatus,
)


def _load_store_module():
    # coordination/mcp/ is a local package literally named `mcp`, which collides
    # with the installed mcp SDK on sys.path, so `import mcp.state_store` fails
    # in this sandbox (it triggers mcp/__init__.py -> tools_phase2 -> mcp.server).
    # Load state_store.py in isolation (bypassing the package __init__) to test
    # the write-through logic directly.
    here = Path(__file__).resolve().parents[2]
    spec = importlib.util.spec_from_file_location(
        "mcp_state_store_iso", here / "mcp" / "state_store.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _make_pipeline():
    node = NodeDef(node_id="n1", node_type="client_ui_impl")
    profile = ParticipationProfile(id="p", name="p", roles_present=["product"])
    defn = PipelineDefinition(
        id="pipe-1",
        name="t",
        nodes=[node],
        profile=profile,
        root_product_node_id="n1",
    )
    ns = NodeState(node_id="n1", status=NodeStatus.READY, artifact_refs=[])
    state = PipelineState(
        pipeline_id="pipe-1",
        version=1,
        status=PipelineStatus.ACTIVE,
        created_at="2025-01-01T00:00:00Z",
        updated_at="2025-01-01T00:00:00Z",
        node_states={"n1": ns},
    )
    return defn, state


@pytest.fixture
def store_module(tmp_path, monkeypatch):
    # chdir so the module-level `STORE = PipelineStateStore()` (default db path
    # data/pipeline_state.db) lands in tmp_path instead of the repo data/ dir.
    monkeypatch.chdir(tmp_path)
    return _load_store_module()


def test_store_register_is_write_through_and_reloadable(store_module, tmp_path):
    """register() persists def+state to SQLite; a brand-new store reloads it."""
    store = store_module.PipelineStateStore(db_path=tmp_path / "state.db")
    defn, state = _make_pipeline()
    store.register(defn, state)

    reloaded = store_module.PipelineStateStore(db_path=tmp_path / "state.db")
    assert "pipe-1" in reloaded.pipelines
    assert "pipe-1" in reloaded.states
    assert (
        reloaded.get_state("pipe-1").node_states["n1"].status == NodeStatus.READY
    )
    assert reloaded.get_def("pipe-1").id == "pipe-1"


def test_store_set_state_writes_through(store_module, tmp_path):
    """set_state() updates both the cache and SQLite; a fresh store sees it."""
    store = store_module.PipelineStateStore(db_path=tmp_path / "state.db")
    _, state = _make_pipeline()
    store.register(_make_pipeline()[0], state)

    mutated = state.model_copy(deep=True)
    mutated.node_states["n1"].status = NodeStatus.DONE
    mutated.updated_at = "2025-01-02T00:00:00Z"
    store.set_state("pipe-1", mutated)

    reloaded = store_module.PipelineStateStore(db_path=tmp_path / "state.db")
    assert reloaded.get_state("pipe-1").node_states["n1"].status == NodeStatus.DONE
    assert reloaded.get_state("pipe-1").updated_at == "2025-01-02T00:00:00Z"


def test_store_get_missing_raises_keyerror(store_module, tmp_path):
    store = store_module.PipelineStateStore(db_path=tmp_path / "state.db")
    with pytest.raises(KeyError):
        store.get_state("does-not-exist")
    with pytest.raises(KeyError):
        store.get_def("does-not-exist")
