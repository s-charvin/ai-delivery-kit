#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${PROJECT_ROOT}"

echo "[1/4] Creating Python virtual environment (.venv) with python3.11..."
if command -v python3.11 >/dev/null 2>&1; then
    python3.11 -m venv .venv
elif command -v python3 >/dev/null 2>&1; then
    PY_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    if [ "$PY_VERSION" = "3.11" ] || [ "$PY_VERSION" = "3.12" ]; then
        python3 -m venv .venv
    else
        echo "ERROR: python3.11+ is required. Found ${PY_VERSION}. Install python3.11 and retry."
        exit 1
    fi
else
    echo "ERROR: python3.11 is not installed. Install python3.11 and retry."
    exit 1
fi

echo "[2/4] Activating venv and installing dependencies (pip install -e \".[dev]\")..."
source .venv/bin/activate
pip install --upgrade pip
pip install -e ".[dev]"

echo "[3/4] Creating empty SQLite DB at tests/fixtures/checkpoint.sqlite..."
FIXTURE_DIR="${PROJECT_ROOT}/tests/fixtures"
mkdir -p "${FIXTURE_DIR}"
DB_FILE="${FIXTURE_DIR}/checkpoint.sqlite"
if [ ! -f "${DB_FILE}" ]; then
    python - <<PYEOF
import sqlite3
import pathlib

db_path = pathlib.Path(r"${DB_FILE}")
conn = sqlite3.connect(db_path)
cur = conn.cursor()
cur.execute("""
    CREATE TABLE IF NOT EXISTS checkpoints (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pipeline_id TEXT NOT NULL,
        node_id TEXT NOT NULL,
        state_json TEXT NOT NULL,
        hash_sha256 TEXT NOT NULL,
        prev_hash TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")
conn.commit()
conn.close()
print(f"  Created {db_path}")
PYEOF
else
    echo "  ${DB_FILE} already exists, skipping."
fi

echo ""
echo "[4/4] Dev env ready. Run pytest to verify."
echo "  source ${PROJECT_ROOT}/.venv/bin/activate"
echo "  cd ${PROJECT_ROOT} && python -m pytest tests/unit/test_task1_scaffold.py -v"
