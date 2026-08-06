#!/usr/bin/env bash
# audit-hashchain-check.sh - Validate the WORM audit hash chain
# Exit codes:
#   0 - chain is valid
#   1 - chain has a gap (first_bad_index reported)
#   2 - usage error / missing deps
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COORD_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

PYTHON_BIN="${PYTHON_BIN:-${COORD_ROOT}/.venv/bin/python}"
WORM_DB_PATH="${WORM_DB_PATH:-${COORD_ROOT}/data/audit_worm.db}"
PIPELINE_ID="${PIPELINE_ID:-}"

if [ ! -x "${PYTHON_BIN}" ]; then
  echo "ERROR: python not found at ${PYTHON_BIN}" >&2
  exit 2
fi

export PYTHONPATH="${COORD_ROOT}:${PYTHONPATH:-}"

"${PYTHON_BIN}" - "${WORM_DB_PATH}" "${PIPELINE_ID}" <<'PYEOF'
import json
import os
import sys
from pathlib import Path

db_path = sys.argv[1]
pipeline_id = sys.argv[2] if len(sys.argv) > 2 else ""

sys.path.insert(0, os.environ.get("PYTHONPATH", "").split(":")[0] or Path(__file__).resolve().parent.parent.parent)

from audit.hash_chain import validate_chain
from audit.worm_storage import WormStorage

try:
    worm = WormStorage(Path(db_path))
except Exception as exc:
    print(f"ERROR opening worm db: {exc}", file=sys.stderr)
    sys.exit(2)

kwargs = {}
if pipeline_id:
    kwargs["pipeline_id"] = pipeline_id
entries = worm.list(limit=100000, **kwargs)

valid, first_bad = validate_chain(entries)

if valid:
    print(json.dumps({"ok": True, "entries": len(entries), "first_bad_index": None}))
    sys.exit(0)
else:
    print(json.dumps({"ok": False, "entries": len(entries), "first_bad_index": first_bad}))
    sys.exit(1)
PYEOF
