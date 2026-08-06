from __future__ import annotations

import os
import shutil

import pytest

from repo.providers.local_provider import LocalHubRepo


def make_random_bytes(size_mb: int) -> bytes:
    return os.urandom(size_mb * 1024 * 1024)


@pytest.fixture
def local_hub(tmp_path) -> LocalHubRepo:
    repo_root = tmp_path / "test-hub"
    if repo_root.exists():
        shutil.rmtree(repo_root)
    hub = LocalHubRepo(repo_root=repo_root, init_bare_if_missing=True)
    try:
        yield hub
    finally:
        try:
            if repo_root.exists():
                shutil.rmtree(repo_root, ignore_errors=True)
        except Exception:
            pass
