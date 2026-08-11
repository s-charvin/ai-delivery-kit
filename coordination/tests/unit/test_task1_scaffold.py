"""Task 1 脚手架验收测试 (TR-1.1 ~ TR-1.3)."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]

MODULE_DIRS = [
    "orchestration",
    "crew",
    "mcp",
    "skills",
    "skills/definitions",
    "audit",
    "monitoring",
    "visual",
    "docker",
    "tests",
    "config",
    "scripts",
    "utils",
    "repo",
    "repo/providers",
]

REQUIRED_MODULES = [
    "orchestration",
    "crew",
    "mcp",
    "skills",
    "audit",
    "monitoring",
    "visual",
    "docker",
    "tests",
    "config",
    "scripts",
    "utils",
    "repo",
]

REQUIRED_IMPORTS = [
    "crewai",
    "mcp",
    "langfuse",
    "pydantic",
    "httpx",
    "jwt",
    "cryptography",
    "yaml",
    "jsonpath_ng",
    "fastapi",
]


def _venv_python() -> str | None:
    candidates = [
        PROJECT_ROOT / ".venv" / "bin" / "python",
        PROJECT_ROOT / "venv" / "bin" / "python",
    ]
    for p in candidates:
        if p.exists():
            return str(p)
    return None


def test_docker_compose_valid():
    """TR-1.1: docker compose config 语法校验通过 (无 docker 环境时 skip)."""
    compose_file = PROJECT_ROOT / "docker" / "docker-compose.yml"
    assert compose_file.exists(), f"Missing {compose_file}"

    if not shutil.which("docker"):
        pytest.skip("docker CLI not available in this environment")

    try:
        subprocess.run(
            ["docker", "compose", "-f", str(compose_file), "config"],
            check=True,
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
        )
    except subprocess.CalledProcessError as exc:
        pytest.fail(
            f"docker compose config failed with exit {exc.returncode}\n"
            f"STDOUT:\n{exc.stdout}\nSTDERR:\n{exc.stderr}"
        )


def test_dependencies_importable(tmp_path):
    """TR-1.2: 核心依赖包可被 import.

    优先使用项目 venv 的 python 子进程验证;
    若无 venv 则 monkeypatch sys.path 回退为当前解释器.
    """
    venv_py = _venv_python()
    import_stmt = "import " + ", ".join(REQUIRED_IMPORTS)

    sandbox_home = tmp_path / "home"
    sandbox_home.mkdir(exist_ok=True)
    mem0_dir = sandbox_home / ".mem0"
    mem0_dir.mkdir(exist_ok=True)
    safe_env = {
        **os.environ,
        "PYTHONPATH": str(PROJECT_ROOT),
        "HOME": str(sandbox_home),
        "MEM0_DIR": str(mem0_dir),
    }

    if venv_py:
        proc = subprocess.run(
            [venv_py, "-c", import_stmt],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
            env=safe_env,
        )
        if proc.returncode != 0:
            pytest.fail(
                f"Dependency import failed (via venv {venv_py}).\n"
                f"STDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
            )
    else:
        orig_path = sys.path.copy()
        orig_home = os.environ.get("HOME")
        orig_mem0 = os.environ.get("MEM0_DIR")
        try:
            os.environ["HOME"] = str(sandbox_home)
            os.environ["MEM0_DIR"] = str(mem0_dir)
            if str(PROJECT_ROOT) not in sys.path:
                sys.path.insert(0, str(PROJECT_ROOT))
            for mod in REQUIRED_IMPORTS:
                __import__(mod)
        except ImportError as exc:
            pytest.fail(
                f"Failed to import {exc.name}. Install deps or run init-dev.sh first.\n"
                f"Original error: {exc}"
            )
        finally:
            sys.path[:] = orig_path
            if orig_home is None:
                os.environ.pop("HOME", None)
            else:
                os.environ["HOME"] = orig_home
            if orig_mem0 is None:
                os.environ.pop("MEM0_DIR", None)
            else:
                os.environ["MEM0_DIR"] = orig_mem0


def test_module_directories_exist():
    """TR-1.3: 12 个模块目录存在且含 __init__.py."""
    missing_dirs: list[str] = []
    missing_init: list[str] = []

    for rel in REQUIRED_MODULES:
        d = PROJECT_ROOT / rel
        if not d.is_dir():
            missing_dirs.append(rel)
            continue
        if not (d / "__init__.py").is_file():
            missing_init.append(rel)

    assert not missing_dirs, f"Missing module directories: {missing_dirs}"
    assert not missing_init, f"Missing __init__.py in: {missing_init}"
