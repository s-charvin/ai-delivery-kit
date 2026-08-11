from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from orchestration.models import ArtifactRef, NodeState, NodeStatus

# coordination/mcp is a local package literally named `mcp`, which collides with
# the installed mcp SDK on sys.path, so `import mcp.review_validation` fails in
# this sandbox. Load the module file in isolation instead.
_HERE = Path(__file__).resolve().parents[2]


def _load_review_module():
    spec = importlib.util.spec_from_file_location(
        "mcp_review_validation_iso", _HERE / "mcp" / "review_validation.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


_SHA256 = "a" * 64


def _ref(**kwargs):
    base = dict(
        node_id="n1",
        artifact_type="ui",
        version=1,
        uri="file://x",
        ref_hash=_SHA256,
        trace_id="t1",
    )
    base.update(kwargs)
    return ArtifactRef(**base)


def _ns(refs):
    return NodeState(node_id="n1", status=NodeStatus.DONE, artifact_refs=refs)


def test_checks_pass_for_valid_artifacts():
    mod = _load_review_module()
    checks = mod.review_artifact_checks(_ns([_ref()]))
    assert checks == {
        "required_fields": "pass",
        "schema": "pass",
        "sha256": "pass",
        "secret_scan": "pass",
    }


def test_required_fields_fail_when_no_refs():
    mod = _load_review_module()
    checks = mod.review_artifact_checks(_ns([]))
    assert checks["required_fields"] == "fail"
    assert checks["sha256"] == "fail"


def test_sha256_fail_on_bad_hash():
    mod = _load_review_module()
    checks = mod.review_artifact_checks(_ns([_ref(ref_hash="not-a-hash")]))
    assert checks["sha256"] == "fail"
    assert checks["schema"] == "pass"  # version is still an int
    assert checks["required_fields"] == "pass"


def test_secret_scan_fail_on_leak():
    mod = _load_review_module()
    checks = mod.review_artifact_checks(_ns([_ref(trace_id="AKIAIOSFODNN7EXAMPLE")]))
    assert checks["secret_scan"] == "fail"


def test_pr_result_always_needs_human():
    mod = _load_review_module()
    res = mod.review_artifact_pr_result(_ns([_ref()]))
    assert res["verdict"] == "needs_human"
    assert res["needs_human"] is True
    assert set(res["checks"].keys()) == {
        "required_fields",
        "schema",
        "sha256",
        "secret_scan",
    }
