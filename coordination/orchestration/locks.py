from __future__ import annotations

import fcntl
import hashlib
import sqlite3
import threading
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Protocol, runtime_checkable

LOCK_NODE = "lock:node:{node_id}"
LOCK_SEQ = "lock:seq:{pipeline_id}:{instance_id}:{node_type}"
LOCK_CASCADE = "lock:cascade:{pipeline_id}"
LOCK_PR = "lock:pr:{node_id}"


@runtime_checkable
class DistributedLock(Protocol):
    def acquire(self, key: str, timeout_sec: float = 5.0) -> bool: ...
    def release(self, key: str) -> None: ...
    def is_locked(self, key: str) -> bool: ...

    @contextmanager
    def guard(self, key: str, timeout_sec: float = 5.0) -> Iterator[bool]:
        acquired = self.acquire(key, timeout_sec)
        try:
            yield acquired
        finally:
            if acquired:
                self.release(key)


class ThreadingLockImpl:
    def __init__(self) -> None:
        self._locks: dict[str, threading.Lock] = {}
        self._global: threading.RLock = threading.RLock()
        self._owned: dict[str, bool] = {}

    def acquire(self, key: str, timeout_sec: float = 5.0) -> bool:
        with self._global:
            if key not in self._locks:
                self._locks[key] = threading.Lock()
            lock = self._locks[key]
        ok = lock.acquire(timeout=timeout_sec)
        if ok:
            self._owned[key] = True
        return ok

    def release(self, key: str) -> None:
        with self._global:
            lock = self._locks.get(key)
        if lock is not None and self._owned.pop(key, False):
            lock.release()

    def is_locked(self, key: str) -> bool:
        with self._global:
            lock = self._locks.get(key)
        if lock is None:
            return False
        acquired = lock.acquire(blocking=False)
        if acquired:
            lock.release()
            return False
        return True

    @contextmanager
    def guard(self, key: str, timeout_sec: float = 5.0) -> Iterator[bool]:
        acquired = self.acquire(key, timeout_sec)
        try:
            yield acquired
        finally:
            if acquired:
                self.release(key)


class FileFcntlLockImpl:
    def __init__(self, lock_dir: Path | str) -> None:
        self.lock_dir = Path(lock_dir)
        self.lock_dir.mkdir(parents=True, exist_ok=True)
        self._fds: dict[str, int] = {}

    def _key_to_path(self, key: str) -> Path:
        h = hashlib.sha256(key.encode("utf-8")).hexdigest()[:32]
        return self.lock_dir / f"{h}.lock"

    def acquire(self, key: str, timeout_sec: float = 5.0) -> bool:
        path = self._key_to_path(key)
        fd = open(path, "w")
        deadline = time.time() + timeout_sec
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                self._fds[key] = fd.fileno()
                self._fd_objs = getattr(self, "_fd_objs", {})
                self._fd_objs[key] = fd
                return True
            except BlockingIOError:
                if time.time() >= deadline:
                    fd.close()
                    return False
                time.sleep(0.05)

    def release(self, key: str) -> None:
        fd_obj = getattr(self, "_fd_objs", {}).pop(key, None)
        if fd_obj is not None:
            try:
                fcntl.flock(fd_obj, fcntl.LOCK_UN)
            except Exception:
                pass
            fd_obj.close()
        self._fds.pop(key, None)

    def is_locked(self, key: str) -> bool:
        path = self._key_to_path(key)
        if not path.exists():
            return False
        fd = open(path, "w")
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            fcntl.flock(fd, fcntl.LOCK_UN)
            return False
        except BlockingIOError:
            return True
        finally:
            fd.close()

    @contextmanager
    def guard(self, key: str, timeout_sec: float = 5.0) -> Iterator[bool]:
        acquired = self.acquire(key, timeout_sec)
        try:
            yield acquired
        finally:
            if acquired:
                self.release(key)


class SQLiteAdvisoryLockImpl:
    def __init__(self, sqlite_path: Path | str) -> None:
        self.sqlite_path = Path(sqlite_path)
        self.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        self._owner = uuid.uuid4().hex
        self._conn = sqlite3.connect(str(self.sqlite_path), check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS locks(
                key TEXT PRIMARY KEY,
                owner TEXT,
                expires_at INTEGER
            )
            """
        )
        self._conn.commit()
        self._thread_lock = threading.RLock()

    def acquire(self, key: str, timeout_sec: float = 5.0) -> bool:
        deadline = time.time() + timeout_sec
        while True:
            with self._thread_lock:
                try:
                    self._conn.execute("BEGIN IMMEDIATE")
                    now_ms = int(time.time() * 1000)
                    expires_at = now_ms + int(timeout_sec * 1000) + 5000
                    self._conn.execute(
                        "INSERT OR IGNORE INTO locks(key, owner, expires_at) VALUES(?, ?, ?)",
                        (key, self._owner, expires_at),
                    )
                    cur = self._conn.execute(
                        "SELECT owner, expires_at FROM locks WHERE key=?", (key,)
                    )
                    row = cur.fetchone()
                    if row is None:
                        self._conn.commit()
                        if time.time() >= deadline:
                            return False
                        time.sleep(0.05)
                        continue
                    owner, exp = row
                    if owner == self._owner:
                        self._conn.execute(
                            "UPDATE locks SET expires_at=? WHERE key=?",
                            (expires_at, key),
                        )
                        self._conn.commit()
                        return True
                    if now_ms > exp:
                        self._conn.execute(
                            "UPDATE locks SET owner=?, expires_at=? WHERE key=?",
                            (self._owner, expires_at, key),
                        )
                        self._conn.commit()
                        return True
                    self._conn.commit()
                except Exception:
                    try:
                        self._conn.rollback()
                    except Exception:
                        pass
            if time.time() >= deadline:
                return False
            time.sleep(0.05)

    def release(self, key: str) -> None:
        with self._thread_lock:
            try:
                self._conn.execute(
                    "DELETE FROM locks WHERE key=? AND owner=?", (key, self._owner)
                )
                self._conn.commit()
            except Exception:
                try:
                    self._conn.rollback()
                except Exception:
                    pass

    def is_locked(self, key: str) -> bool:
        with self._thread_lock:
            try:
                cur = self._conn.execute(
                    "SELECT owner, expires_at FROM locks WHERE key=?", (key,)
                )
                row = cur.fetchone()
                if row is None:
                    return False
                _owner, exp = row
                now_ms = int(time.time() * 1000)
                if now_ms > exp:
                    return False
                return True
            except Exception:
                return False

    def dump_all_locks(self) -> list[dict]:
        with self._thread_lock:
            try:
                cur = self._conn.execute(
                    "SELECT key, owner, expires_at FROM locks ORDER BY key"
                )
                rows = cur.fetchall()
                return [
                    {"key": r[0], "owner": r[1], "expires_at": r[2]} for r in rows
                ]
            except Exception:
                return []

    @contextmanager
    def guard(self, key: str, timeout_sec: float = 5.0) -> Iterator[bool]:
        acquired = self.acquire(key, timeout_sec)
        try:
            yield acquired
        finally:
            if acquired:
                self.release(key)


class Allocator:
    def __init__(self, sqlite_path: Path | str, lock: DistributedLock) -> None:
        self.sqlite_path = Path(sqlite_path)
        self.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = lock
        self._conn = sqlite3.connect(str(self.sqlite_path), check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS seq_counter(
                pipeline_id TEXT,
                instance_id TEXT,
                node_type TEXT,
                value INTEGER DEFAULT 0,
                PRIMARY KEY (pipeline_id, instance_id, node_type)
            )
            """
        )
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS seen_callbacks(
                id TEXT PRIMARY KEY
            )
            """
        )
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS emergency_versions(
                node_id TEXT PRIMARY KEY,
                version INTEGER DEFAULT 0,
                payload TEXT
            )
            """
        )
        self._conn.commit()
        self._thread_lock = threading.RLock()

    def allocate(
        self, pipeline_id: str, instance_id: str, node_type: str
    ) -> int:
        lock_key = LOCK_SEQ.format(
            pipeline_id=pipeline_id, instance_id=instance_id, node_type=node_type
        )
        with self.lock.guard(lock_key, timeout_sec=10.0) as acquired:
            if not acquired:
                raise TimeoutError(f"Failed to acquire seq lock for {lock_key}")
            with self._thread_lock:
                self._conn.execute("BEGIN IMMEDIATE")
                try:
                    cur = self._conn.execute(
                        "SELECT value FROM seq_counter WHERE pipeline_id=? AND instance_id=? AND node_type=?",
                        (pipeline_id, instance_id, node_type),
                    )
                    row = cur.fetchone()
                    if row is None:
                        value = 1
                        self._conn.execute(
                            "INSERT INTO seq_counter(pipeline_id, instance_id, node_type, value) VALUES(?, ?, ?, ?)",
                            (pipeline_id, instance_id, node_type, value),
                        )
                    else:
                        value = row[0] + 1
                        self._conn.execute(
                            "UPDATE seq_counter SET value=? WHERE pipeline_id=? AND instance_id=? AND node_type=?",
                            (value, pipeline_id, instance_id, node_type),
                        )
                    self._conn.commit()
                    return value
                except Exception:
                    self._conn.rollback()
                    raise

    def is_callback_processed(self, key: str) -> bool:
        with self._thread_lock:
            try:
                cur = self._conn.execute(
                    "SELECT id FROM seen_callbacks WHERE id=?", (key,)
                )
                row = cur.fetchone()
                if row is not None:
                    return True
                self._conn.execute(
                    "INSERT INTO seen_callbacks(id) VALUES(?)", (key,)
                )
                self._conn.commit()
                return False
            except sqlite3.IntegrityError:
                return True
            except Exception:
                try:
                    self._conn.rollback()
                except Exception:
                    pass
                return False

    def emergency_version_cas(
        self, node_id: str, payload: dict, expected_version: int
    ) -> tuple[int, bool]:
        import json

        with self._thread_lock:
            self._conn.execute("BEGIN IMMEDIATE")
            try:
                cur = self._conn.execute(
                    "SELECT version FROM emergency_versions WHERE node_id=?",
                    (node_id,),
                )
                row = cur.fetchone()
                current_version = 0 if row is None else row[0]
                if current_version != expected_version:
                    self._conn.rollback()
                    return current_version, False
                new_version = current_version + 1
                payload_str = json.dumps(payload)
                if row is None:
                    self._conn.execute(
                        "INSERT INTO emergency_versions(node_id, version, payload) VALUES(?, ?, ?)",
                        (node_id, new_version, payload_str),
                    )
                else:
                    self._conn.execute(
                        "UPDATE emergency_versions SET version=?, payload=? WHERE node_id=?",
                        (new_version, payload_str, node_id),
                    )
                self._conn.commit()
                return new_version, True
            except Exception:
                self._conn.rollback()
                raise
