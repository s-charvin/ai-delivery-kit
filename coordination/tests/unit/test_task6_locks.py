from __future__ import annotations

import asyncio
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from orchestration.cascade_integration import CascadeIntegrator
from orchestration.conflict_resolver import (
    ConflictResolver,
    DistributedLock,
    PRConflictError,
)
from orchestration.locks import (
    Allocator,
    FileFcntlLockImpl,
    SQLiteAdvisoryLockImpl,
    ThreadingLockImpl,
)


@pytest.fixture
def tmp_sqlite(tmp_path):
    return tmp_path / "test_task6.sqlite3"


@pytest.fixture
def tmp_lock_dir(tmp_path):
    d = tmp_path / "locks"
    d.mkdir(parents=True, exist_ok=True)
    return d


def test_protocol_isinstance_checks(tmp_sqlite, tmp_lock_dir):
    tlock = ThreadingLockImpl()
    flock = FileFcntlLockImpl(tmp_lock_dir)
    slock = SQLiteAdvisoryLockImpl(tmp_sqlite)

    assert isinstance(tlock, DistributedLock)
    assert isinstance(flock, DistributedLock)
    assert isinstance(slock, DistributedLock)


@pytest.mark.asyncio
async def test_TR61_allocate_seq_100_concurrent_no_duplicate(tmp_sqlite):
    lock = ThreadingLockImpl()
    allocator = Allocator(tmp_sqlite, lock)

    pid = "p61"
    inst = "inst-a"
    node_type = "server_impl"

    loop = asyncio.get_event_loop()
    executor = ThreadPoolExecutor(max_workers=16)

    async def _alloc(idx: int) -> int:
        return await loop.run_in_executor(
            executor, allocator.allocate, pid, inst, node_type
        )

    results = await asyncio.gather(*[_alloc(i) for i in range(100)])

    assert len(set(results)) == 100, f"Expected 100 unique values, got duplicates: {len(set(results))}"
    assert min(results) == 1, f"Expected min value 1, got {min(results)}"
    assert max(results) == 100, f"Expected max value 100, got {max(results)}"

    executor.shutdown(wait=True)


def test_TR62_submit_artifact_same_node_5_threads_conflict(tmp_sqlite):
    lock = ThreadingLockImpl()
    allocator = Allocator(tmp_sqlite, lock)
    state_store = type("MockStore", (), {"pending_prs": {}})()
    resolver = ConflictResolver(locks=lock, allocator=allocator, state_store=state_store)

    node_id = "node-conflict-62"
    pr_id = "pr-fixed-62"
    success_count = [0]
    conflict_count = [0]
    conflict_codes = []
    list_lock = threading.Lock()

    def worker():
        try:
            resolver.check_open_pr_conflict(node_id, state_store.pending_prs)
            with list_lock:
                state_store.pending_prs[node_id] = pr_id
                success_count[0] += 1
        except PRConflictError as e:
            with list_lock:
                conflict_count[0] += 1
                conflict_codes.append(e.error_code)
        except Exception:
            with list_lock:
                conflict_count[0] += 1

    threads = [threading.Thread(target=worker) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert success_count[0] == 1, f"Expected exactly 1 success, got {success_count[0]}"
    assert conflict_count[0] == 4, f"Expected exactly 4 conflicts, got {conflict_count[0]}"
    for code in conflict_codes:
        assert code == "E_NODE_PENDING_PR_EXISTS", f"Expected E_NODE_PENDING_PR_EXISTS, got {code}"


def test_TR63_cascade_done_3_downstream_idempotent_no_duplicate_events(tmp_sqlite):
    lock = ThreadingLockImpl()
    allocator = Allocator(tmp_sqlite, lock)
    resolver = ConflictResolver(locks=lock, allocator=allocator)
    integrator = CascadeIntegrator(resolver=resolver)

    pipeline_id = "pipe-63"
    events_template = [
        {"event_id": "evt-1", "type": "NODE_READY", "payload": {"node_id": "down-a"}},
        {"event_id": "evt-2", "type": "NODE_READY", "payload": {"node_id": "down-b"}},
        {"event_id": "evt-3", "type": "NODE_DONE", "payload": {"node_id": "down-c"}},
    ]

    all_event_ids: set[str] = set()
    results_per_call = []

    for _ in range(3):
        def fake_fn(evts=events_template):
            return list(evts)

        deduped = resolver.cascade_serialize(pipeline_id, fake_fn)
        results_per_call.append(deduped)
        for ev in deduped:
            all_event_ids.add(ev["event_id"])

    assert len(all_event_ids) == 3, (
        f"Expected exactly 3 unique event_ids across all calls, got {len(all_event_ids)}: {all_event_ids}"
    )
    for result in results_per_call:
        assert len(result) == 3, f"Each call should dedupe to 3 events, got {len(result)}"
