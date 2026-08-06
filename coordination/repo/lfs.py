from __future__ import annotations

import hashlib
from pathlib import Path

DEFAULT_THRESHOLD_MB = 10


def should_use_lfs(size_bytes: int, threshold_mb: int = DEFAULT_THRESHOLD_MB) -> bool:
    threshold_bytes = threshold_mb * 1024 * 1024
    return size_bytes > threshold_bytes


def gitattributes_entry(path_glob: str) -> str:
    return f"{path_glob} filter=lfs diff=lfs merge=lfs -text"


def ensure_gitattributes(workdir: Path, path_glob: str) -> None:
    gitattributes_path = workdir / ".gitattributes"
    entry = gitattributes_entry(path_glob)
    if gitattributes_path.exists():
        existing = gitattributes_path.read_text()
        if entry in existing:
            return
        with open(gitattributes_path, "a") as f:
            if not existing.endswith("\n"):
                f.write("\n")
            f.write(entry + "\n")
    else:
        gitattributes_path.write_text(entry + "\n")


def generate_lfs_pointer(content_bytes: bytes) -> str:
    sha256_hash = hashlib.sha256(content_bytes).hexdigest()
    oid = f"sha256:{sha256_hash}"
    size = len(content_bytes)
    lines = [
        "version https://git-lfs.github.com/spec/v1",
        f"oid {oid}",
        f"size {size}",
        "",
    ]
    return "\n".join(lines)
