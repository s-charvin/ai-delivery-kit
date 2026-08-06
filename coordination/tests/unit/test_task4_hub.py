from __future__ import annotations

import os
import random
import re
import shutil
import string
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from repo.branch_naming import (
    BRANCH_NAME_REGEX,
    allocate_seq,
    format_branch_name,
    validate_branch_name,
)
from repo.hub import (
    HubRepo,
    PRTemplateInvalidError,
    ProtectedBranchError,
    RepoUnreachableError,
)
from repo.manifest import Manifest, bump_version, load_manifest, save_manifest
from repo.pr_template import (
    PR_REQUIRED_FIELDS,
    ensure_pr_template_valid,
    validate_pr_template,
)
from repo.providers.github_provider import GitHubProvider, MockHTTPClient
from repo.providers.local_provider import LocalHubRepo
from tests.fixtures.local_hub_repo import local_hub, make_random_bytes  # noqa: F401


pytestmark = pytest.mark.unit


def _git_available() -> bool:
    try:
        r = subprocess.run(
            ["git", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return r.returncode == 0
    except Exception:
        return False


GIT_AVAILABLE = _git_available()
skip_if_no_git = pytest.mark.skipif(not GIT_AVAILABLE, reason="git not available")


def _valid_template(overrides: dict | None = None) -> dict:
    tpl = {f: f"val_{f}" for f in PR_REQUIRED_FIELDS}
    tpl["deps"] = []
    if overrides:
        tpl.update(overrides)
    return tpl


def _count_commits(repo: LocalHubRepo, branch: str = "main") -> int:
    result = subprocess.run(
        ["git", "-C", str(repo.work_path), "log", branch, "--oneline"],
        capture_output=True,
        text=True,
    )
    lines = [l for l in result.stdout.splitlines() if l.strip()]
    return len(lines)


def test_protocol_isinstance():
    """HubRepo Protocol runtime_checkable 验证"""
    local_obj = object.__new__(LocalHubRepo)
    local_obj.repo_root = Path("/tmp/noop")
    local_obj.hub_path = Path("/tmp/noop/hub.git")
    local_obj.work_path = Path("/tmp/noop/work")
    local_obj._bot_actor = "coordination-bot"
    local_obj._lfs_threshold_mb = 10
    local_obj._lfs_enabled = True
    assert isinstance(local_obj, HubRepo), "LocalHubRepo 必须满足 HubRepo Protocol"

    mock = MockHTTPClient()
    gh = GitHubProvider(owner="o", repo="r", token="x", client=mock)
    assert isinstance(gh, HubRepo), "GitHubProvider 必须满足 HubRepo Protocol"


@skip_if_no_git
def test_TR_4_1_main_protected_push_rejected(local_hub: LocalHubRepo):
    """TR-4.1 AC1.1 main push 拒"""
    assert local_hub.is_main_protected_direct_push() is True

    wp = local_hub.work_path
    bad_file = wp / f"_bad_{random.randint(1000,9999)}.txt"
    bad_file.write_text("should not be pushed")
    subprocess.run(["git", "-C", str(wp), "checkout", "main"], capture_output=True)
    subprocess.run(["git", "-C", str(wp), "add", bad_file.name], capture_output=True)
    subprocess.run(
        ["git", "-C", str(wp), "commit", "-m", "bad: direct push"],
        capture_output=True,
        text=True,
        env={
            **os.environ,
            "GIT_COMMITTER_NAME": "malicious-user",
            "GIT_COMMITTER_EMAIL": "bad@local",
            "GIT_AUTHOR_NAME": "malicious-user",
            "GIT_AUTHOR_EMAIL": "bad@local",
        },
    )
    with pytest.raises(ProtectedBranchError):
        local_hub._check_direct_push_allowed("main", "malicious-user")


def test_TR_4_2_branch_naming_regex():
    """TR-4.2 分支命名正则 + seq 零填充"""
    for _ in range(20):
        ppl = "".join(random.choices(string.ascii_letters + string.digits, k=random.randint(3, 12)))
        inst = "".join(random.choices(string.ascii_letters + string.digits, k=random.randint(3, 12)))
        node = "".join(random.choices(string.ascii_letters + string.digits + "-.", k=random.randint(3, 12)))
        seq = random.randint(1, 9999)
        name = format_branch_name(ppl, inst, node, seq)
        assert validate_branch_name(name), f"branch {name} failed regex: {BRANCH_NAME_REGEX}"
        assert re.fullmatch(BRANCH_NAME_REGEX, name) is not None

    assert format_branch_name("ppl", "inst", "nt", 1).endswith("-001")
    assert format_branch_name("ppl", "inst", "nt", 12).endswith("-012")
    assert format_branch_name("ppl", "inst", "nt", 345).endswith("-345")

    assert allocate_seq(set()) == 1
    assert allocate_seq({1}) == 2
    assert allocate_seq({1, 2, 4}) == 3


def test_TR_4_3_pr_template_missing_field_rejected(local_hub: LocalHubRepo):
    """TR-4.3 PR 缺字段拒"""
    tpl_no_node = _valid_template()
    del tpl_no_node["node_id"]
    missing = validate_pr_template(tpl_no_node)
    assert "node_id" in missing
    with pytest.raises(PRTemplateInvalidError) as exc_info:
        ensure_pr_template_valid(tpl_no_node)
    assert "node_id" in exc_info.value.missing_fields
    assert exc_info.value.code == "E_PR_TEMPLATE_MISSING_FIELD"

    tpl_no_deps = _valid_template()
    del tpl_no_deps["deps"]
    with pytest.raises(PRTemplateInvalidError) as exc_info2:
        ensure_pr_template_valid(tpl_no_deps)
    assert "deps" in exc_info2.value.missing_fields

    prs_before = set()
    prs_dir = local_hub.work_path / ".prs"
    if prs_dir.exists():
        prs_before = set(p.name for p in prs_dir.glob("*.json"))

    try:
        branch = local_hub.create_feat_branch("ppl1", "inst1", "nt", 1)
        local_hub.commit_push_file(branch, "a.txt", b"hello", "feat: add a")
        local_hub.open_pr(branch, "main", "bad pr", tpl_no_node)
    except PRTemplateInvalidError:
        pass

    prs_after = set()
    if prs_dir.exists():
        prs_after = set(p.name for p in prs_dir.glob("*.json"))
    assert prs_before == prs_after, "open_pr 缺字段时不应创建 .prs/* 文件"


@skip_if_no_git
def test_TR_4_4_squash_merge_commits_count(local_hub: LocalHubRepo):
    """TR-4.4 squash merge 精确增量 1"""
    initial_count = _count_commits(local_hub, "main")

    branch1 = local_hub.create_feat_branch("p1", "i1", "n1", 1)
    local_hub.commit_push_file(branch1, "a.txt", b"a", "feat: add a")
    local_hub.commit_push_file(branch1, "b.txt", b"b", "feat: add b")
    pr1 = local_hub.open_pr(branch1, "main", "first", _valid_template({"node_id": "n1"}))
    local_hub.approve_and_squash_merge(pr1, local_hub._bot_actor)
    after_first = _count_commits(local_hub, "main")
    assert after_first == initial_count + 1, (
        f"首次 squash merge 后 main 应只增加 1 条 commit: before={initial_count} after={after_first}"
    )

    branch2 = local_hub.create_feat_branch("p1", "i1", "n2", 2)
    local_hub.commit_push_file(branch2, "c.txt", b"c", "feat: add c")
    local_hub.commit_push_file(branch2, "d.txt", b"d", "feat: add d")
    local_hub.commit_push_file(branch2, "e.txt", b"e", "feat: add e")
    pr2 = local_hub.open_pr(branch2, "main", "second", _valid_template({"node_id": "n2"}))
    local_hub.approve_and_squash_merge(pr2, local_hub._bot_actor)
    after_second = _count_commits(local_hub, "main")
    assert after_second == after_first + 1, (
        f"第二次 squash merge 后 main 应再增加 1 条 commit: after1={after_first} after2={after_second}"
    )


@skip_if_no_git
def test_TR_4_5_lfs_11mb_pointer(local_hub: LocalHubRepo):
    """TR-4.5 11MB LFS"""
    local_hub.ensure_lfs(threshold_mb=10)
    branch = local_hub.create_feat_branch("p1", "i1", "n1", 1)
    big = make_random_bytes(11)
    path = "artifacts/big_11mb.bin"
    local_hub.commit_push_file(branch, path, big, "feat: big file lfs")

    ga = local_hub.work_path / ".gitattributes"
    assert ga.exists(), ".gitattributes 必须创建"
    ga_text = ga.read_text()
    assert "filter=lfs" in ga_text, f".gitattributes 应含 lfs 规则: {ga_text}"

    file_in_tree = local_hub.work_path / path
    if file_in_tree.exists():
        content = file_in_tree.read_text(errors="ignore")
        assert "version https://git-lfs" in content, (
            f"文件应为 LFS 指针, 首行需含 version https://git-lfs: {content[:120]}"
        )
    else:
        raw = local_hub.git_show(path, branch)
        text = raw.decode("utf-8", errors="ignore")
        assert "version https://git-lfs" in text, (
            f"LFS 指针需含 version https://git-lfs, got: {text[:200]}"
        )


@skip_if_no_git
def test_TR_4_6_manifest_version_bump(local_hub: LocalHubRepo):
    """TR-4.6 manifest 版本递加"""
    wp = local_hub.work_path
    pipeline_id = "pipeline-x"

    branch = local_hub.create_feat_branch(pipeline_id, "i1", "n1", 1)
    m = Manifest(pipeline_id=pipeline_id)
    save_manifest(wp, m)
    local_hub.commit_push_file(
        branch,
        f"pipelines/{pipeline_id}/.manifest.yaml",
        (wp / "pipelines" / pipeline_id / ".manifest.yaml").read_bytes(),
        "chore: init manifest",
    )
    pr = local_hub.open_pr(branch, "main", "init", _valid_template({"node_id": "n1", "pipeline_id": pipeline_id}))
    local_hub.approve_and_squash_merge(pr, local_hub._bot_actor)

    loaded = load_manifest(wp, pipeline_id)
    assert loaded is not None
    assert loaded.version == 1
    assert loaded.latest_versions.get("n1", 0) == 0

    m2 = bump_version(loaded, "n1")
    assert m2.latest_versions["n1"] == 1
    assert m2.version == 2

    save_manifest(wp, m2)
    branch2 = local_hub.create_feat_branch(pipeline_id, "i1", "n1", 2)
    local_hub.commit_push_file(
        branch2,
        f"pipelines/{pipeline_id}/.manifest.yaml",
        (wp / "pipelines" / pipeline_id / ".manifest.yaml").read_bytes(),
        "chore: bump manifest",
    )
    pr2 = local_hub.open_pr(branch2, "main", "bump", _valid_template({"node_id": "n1", "pipeline_id": pipeline_id}))
    local_hub.approve_and_squash_merge(pr2, local_hub._bot_actor)

    reloaded = load_manifest(wp, pipeline_id)
    assert reloaded is not None
    assert reloaded.latest_versions["n1"] == 1
    assert reloaded.version == 2

    m3 = bump_version(m2, "n1")
    assert m3.latest_versions["n1"] == 2
    assert m3.version == 3


def test_TR_4_7_hub_offline_github_provider():
    """TR-4.7 hub 断网"""
    mock = MockHTTPClient(always_raise=ConnectionError("offline"))
    gh = GitHubProvider(owner="x", repo="y", token="t", client=mock)
    try:
        gh.commit_push_file("main", "a.txt", b"hello", "feat: a")
    except RepoUnreachableError as e:
        assert e.code == "E_REPO_UNREACHABLE", (
            f"断网应抛 RepoUnreachableError, code 精确 E_REPO_UNREACHABLE, 实际: {e.code}"
        )
    except Exception as e2:
        pytest.fail(f"不允许抛其他异常或 traceback: {type(e2).__name__}: {e2}")
    else:
        pytest.fail("应抛 RepoUnreachableError, 实际未抛异常")

    assert len(mock.requests) >= 1, "至少调用一次 HTTPClient.request"
