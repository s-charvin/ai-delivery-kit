#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from orchestration.locks import SQLiteAdvisoryLockImpl


def main() -> None:
    parser = argparse.ArgumentParser(description="Dump current SQLite advisory locks")
    parser.add_argument(
        "--sqlite-path",
        type=str,
        default="data/locks.sqlite3",
        help="Path to SQLite database file",
    )
    args = parser.parse_args()

    sqlite_path = Path(args.sqlite_path)
    if not sqlite_path.exists():
        print(f"No lock database found at {sqlite_path}")
        return

    lock_impl = SQLiteAdvisoryLockImpl(sqlite_path)
    locks = lock_impl.dump_all_locks()

    if not locks:
        print("No active locks.")
        return

    print(f"Found {len(locks)} active lock(s):")
    print("=" * 80)
    for i, lock in enumerate(locks, 1):
        print(f"Lock #{i}:")
        print(f"  Key:        {lock['key']}")
        print(f"  Owner:      {lock['owner']}")
        print(f"  Expires at: {lock['expires_at']} (ms epoch)")
        print("-" * 80)


if __name__ == "__main__":
    main()
