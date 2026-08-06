from __future__ import annotations

import base64
import inspect
import os
import random
import string
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest

from audit.engine import (
    R_ADDENDUM_VS_CHANGED,
    R_AUTH_L1_NODE_TYPE,
    R_AUTH_L2_INSTANCE_ID,
    R_AUTH_L3_EXTERNAL_REPO,
    R_CHANGE_CLASS_CONSISTENCY,
    R_CLASSIFICATION_CLEARANCE,
    R_COMMIT_STABILITY,
    R_COMPLETENESS_CONTRACT,
    R_DEPS_DONE,
    R_EXTERNAL_REF_OWNERSHIP,
    R_FILE_FORMAT,
    R_HUMAN_REVIEW_REQUIRED,
    R_IMPACT_CLAIM_COMPLETENESS,
    R_MALWARE_SCAN,
    R_REQUIRED_FIELDS,
    R_SECRET_SCAN,
    R_URL_SAFETY,
    ReviewContext,
    Rule,
    RuleEngine,
)
from audit.hash_chain import repair_chain, validate_chain
from audit.merge_approve import E_HUMAN_REVIEW_REQUIRED, MergeApproveService
from audit.worm_storage import AuditLogEntry, WormStorage
from config.constants import PARTICIPATION_PROFILES
from orchestration.models import (
    ArtifactRef,
    ClassificationLevel,
    DepDeclaration,
    DepPresence,
    DepStrictness,
    NodeDef,
    NodeState,
    NodeStatus,
    PipelineDefinition,
    PipelineState,
    PipelineStatus,
    Provenance,
)
from repo.hub import PrDetail


def _make_basic_pipeline(node_type: str = "product_spec", node_id: str = "n0"):
    profile = PARTICIPATION_PROFILES["fullstack"]
    node_def = NodeDef(
        node_id=node_id,
        node_type=node_type,
        role_assignments=[f"{node_type}-inst-1"],
        deps=[],
        classification=ClassificationLevel.INTERNAL,
    )
    defn = PipelineDefinition(
        id="p-test",
        name="Test Pipeline",
        nodes=[node_def],
        profile=profile,
        classification=ClassificationLevel.INTERNAL,
        root_product_node_id=node_id,
    )
    now = datetime.now(timezone.utc).isoformat()
    ns = NodeState(
        node_id=node_id,
        status=NodeStatus.PENDING_REVIEW,
        pending_pr_count=1,
    )
    state = PipelineState(
        pipeline_id="p-test",
        version=1,
        status=PipelineStatus.ACTIVE,
        created_at=now,
        updated_at=now,
        node_states={node_id: ns},
        cascade_pending=[],
        profile_id=profile.id,
        classification=ClassificationLevel.INTERNAL,
        completed_nodes_count=0,
    )
    return defn, state, node_id


def _make_pr_detail(template_extras: dict | None = None, diff_unified: str = "", files: list[str] | None = None) -> PrDetail:
    base_template = {
        "node_id": "n0",
        "instance_id": "product-spec-inst-1",
        "pipeline_id": "p-test",
        "deps": [],
        "artifact_type": "product_spec",
        "version": 1,
        "change_class": "compatible",
        "classification": 1,
    }
    if template_extras:
        base_template.update(template_extras)
    return PrDetail(
        pr_id="pr-abc123",
        from_branch="feat/n0/v1",
        to_branch="main",
        title="PR n0 v1",
        template=base_template,
        files=files or ["spec.md"],
        diff_unified=diff_unified,
        commits=["abc123def456"],
        state="open",
    )


def _make_ctx(
    node_type: str = "product_spec",
    submitter_role: str = "product",
    template_extras: dict | None = None,
    content: dict[str, bytes] | None = None,
    diff_unified: str = "",
    added: int = 5,
    deleted: int = 0,
    clearance: ClassificationLevel = ClassificationLevel.INTERNAL,
    artifact_class: ClassificationLevel = ClassificationLevel.INTERNAL,
    change_class_declared: str = "compatible",
    addendum_declared: bool = False,
    external_refs: list[str] | None = None,
    external_whitelist: list[str] | None = None,
    node_def_extras: dict | None = None,
    skill=None,
) -> ReviewContext:
    defn, state, node_id = _make_basic_pipeline(node_type)
    if node_def_extras:
        for i, n in enumerate(defn.nodes):
            if n.node_id == node_id:
                data = n.model_dump()
                data.update(node_def_extras)
                defn.nodes[i] = NodeDef.model_validate(data)
    pr = _make_pr_detail(template_extras, diff_unified)
    content_bytes = content or {"spec.md": b"# Normal doc\nhello world\n"}
    return ReviewContext(
        pipeline_def=defn,
        pipeline_state=state,
        node_id=node_id,
        pr_id=pr.pr_id,
        pr_detail=pr,
        template=pr.template,
        content_bytes=content_bytes,
        diff_added_lines=added,
        diff_deleted_lines=deleted,
        diff_unified=diff_unified,
        role_instance_id=pr.template.get("instance_id", f"{node_type}-inst-1"),
        token_payload={"sub": "tester"},
        clearance=clearance,
        skill=skill,
        submitter_role=submitter_role,
        node_type=node_type,
        artifact_classification=artifact_class,
        change_class_declared=change_class_declared,
        addendum_declared=addendum_declared,
        external_refs=external_refs or [],
        external_repo_whitelist=external_whitelist or [],
    )


class _SimpleStateStore:
    def __init__(self, defn: PipelineDefinition, state: PipelineState):
        self._defn = defn
        self._state = state
        self.pending_prs: dict[str, str] = {}

    def get_def(self, pid: str) -> PipelineDefinition:
        return self._defn

    def get_state(self, pid: str) -> PipelineState:
        return self._state

    def set_state(self, pid: str, state: PipelineState) -> None:
        self._state = state


def _rand_b64(n: int) -> str:
    raw = bytes([random.randint(0, 255) for _ in range(n)])
    return base64.b64encode(raw).decode("ascii").rstrip("=")


class TestTr71Rules34Cases:
    EXPECTED_RULE_IDS = {
        "R_AUTH_L1_NODE_TYPE",
        "R_AUTH_L2_INSTANCE_ID",
        "R_AUTH_L3_EXTERNAL_REPO",
        "R_REQUIRED_FIELDS",
        "R_CLASSIFICATION_CLEARANCE",
        "R_DEPS_DONE",
        "R_FILE_FORMAT",
        "R_COMPLETENESS_CONTRACT",
        "R_SECRET_SCAN",
        "R_URL_SAFETY",
        "R_MALWARE_SCAN",
        "R_EXTERNAL_REF_OWNERSHIP",
        "R_COMMIT_STABILITY",
        "R_ADDENDUM_VS_CHANGED",
        "R_CHANGE_CLASS_CONSISTENCY",
        "R_IMPACT_CLAIM_COMPLETENESS",
        "R_HUMAN_REVIEW_REQUIRED",
    }

    def test_all_rule_constants_exist(self):
        for rid in self.EXPECTED_RULE_IDS:
            import audit.engine as eng

            assert hasattr(eng, rid), f"Missing rule constant {rid}"
            rule = getattr(eng, rid)
            assert isinstance(rule, Rule)
            assert rule.rule_id == rid

    def test_default_engine_has_17_rules(self):
        engine = RuleEngine()
        ids = {r.rule_id for r in engine.rules}
        assert ids == self.EXPECTED_RULE_IDS
        assert len(engine.rules) == 17

    def test_r_auth_l1_node_type_pass(self):
        ctx = _make_ctx(node_type="product_spec", submitter_role="product")
        engine = RuleEngine(rules=[R_AUTH_L1_NODE_TYPE])
        res = engine.evaluate(ctx)
        check = next(c for c in res["checks"] if c["rule_id"] == "R_AUTH_L1_NODE_TYPE")
        assert check["pass"] is True

    def test_r_auth_l1_node_type_fail(self):
        ctx = _make_ctx(node_type="product_spec", submitter_role="ops")
        engine = RuleEngine(rules=[R_AUTH_L1_NODE_TYPE])
        res = engine.evaluate(ctx)
        check = next(c for c in res["checks"] if c["rule_id"] == "R_AUTH_L1_NODE_TYPE")
        assert check["pass"] is False
        assert check["on_fail"] == "reject"

    def test_r_auth_l2_instance_id_pass(self):
        ctx = _make_ctx(
            template_extras={"instance_id": "product-spec-inst-1"},
            node_def_extras={"role_assignments": ["product-spec-inst-1"]},
        )
        engine = RuleEngine(rules=[R_AUTH_L2_INSTANCE_ID])
        res = engine.evaluate(ctx)
        check = next(c for c in res["checks"] if c["rule_id"] == "R_AUTH_L2_INSTANCE_ID")
        assert check["pass"] is True

    def test_r_auth_l2_instance_id_fail(self):
        ctx = _make_ctx(
            template_extras={"instance_id": "bad-inst-id"},
            node_def_extras={"role_assignments": ["product-spec-inst-1"]},
        )
        engine = RuleEngine(rules=[R_AUTH_L2_INSTANCE_ID])
        res = engine.evaluate(ctx)
        check = next(c for c in res["checks"] if c["rule_id"] == "R_AUTH_L2_INSTANCE_ID")
        assert check["pass"] is False
        assert check["on_fail"] == "reject"

    def test_r_auth_l3_external_repo_pass(self):
        ctx = _make_ctx(
            external_refs=["https://github.com/myorg/myrepo"],
            external_whitelist=["myorg"],
        )
        engine = RuleEngine(rules=[R_AUTH_L3_EXTERNAL_REPO])
        res = engine.evaluate(ctx)
        check = next(c for c in res["checks"] if c["rule_id"] == "R_AUTH_L3_EXTERNAL_REPO")
        assert check["pass"] is True

    def test_r_auth_l3_external_repo_fail(self):
        ctx = _make_ctx(
            external_refs=["https://github.com/evilorg/leak"],
            external_whitelist=["safeorg"],
        )
        engine = RuleEngine(rules=[R_AUTH_L3_EXTERNAL_REPO])
        res = engine.evaluate(ctx)
        check = next(c for c in res["checks"] if c["rule_id"] == "R_AUTH_L3_EXTERNAL_REPO")
        assert check["pass"] is False

    def test_r_required_fields_pass(self):
        ctx = _make_ctx(template_extras={
            "node_id": "n0",
            "instance_id": "i1",
            "pipeline_id": "p-test",
            "deps": [],
            "artifact_type": "x",
            "version": 1,
        })
        engine = RuleEngine(rules=[R_REQUIRED_FIELDS])
        res = engine.evaluate(ctx)
        check = next(c for c in res["checks"] if c["rule_id"] == "R_REQUIRED_FIELDS")
        assert check["pass"] is True

    def test_r_required_fields_fail(self):
        ctx = _make_ctx(template_extras={})
        for k in ["node_id", "instance_id", "pipeline_id", "deps", "artifact_type", "version"]:
            if k in ctx.template:
                del ctx.template[k]
        engine = RuleEngine(rules=[R_REQUIRED_FIELDS])
        res = engine.evaluate(ctx)
        check = next(c for c in res["checks"] if c["rule_id"] == "R_REQUIRED_FIELDS")
        assert check["pass"] is False

    def test_r_classification_clearance_pass(self):
        ctx = _make_ctx(
            clearance=ClassificationLevel.CONFIDENTIAL,
            artifact_class=ClassificationLevel.INTERNAL,
        )
        engine = RuleEngine(rules=[R_CLASSIFICATION_CLEARANCE])
        res = engine.evaluate(ctx)
        check = next(c for c in res["checks"] if c["rule_id"] == "R_CLASSIFICATION_CLEARANCE")
        assert check["pass"] is True

    def test_r_classification_clearance_fail(self):
        ctx = _make_ctx(
            clearance=ClassificationLevel.PUBLIC,
            artifact_class=ClassificationLevel.CONFIDENTIAL,
        )
        engine = RuleEngine(rules=[R_CLASSIFICATION_CLEARANCE])
        res = engine.evaluate(ctx)
        check = next(c for c in res["checks"] if c["rule_id"] == "R_CLASSIFICATION_CLEARANCE")
        assert check["pass"] is False

    def test_r_deps_done_pass(self):
        ctx = _make_ctx(node_type="product_spec")
        engine = RuleEngine(rules=[R_DEPS_DONE])
        res = engine.evaluate(ctx)
        check = next(c for c in res["checks"] if c["rule_id"] == "R_DEPS_DONE")
        assert check["pass"] is True

    def test_r_deps_done_fail(self):
        defn, state, node_id = _make_basic_pipeline("server_impl")
        dep_decl = DepDeclaration(
            upstream="n_up",
            presence=DepPresence.REQUIRED,
            strictness=DepStrictness.STRICT,
        )
        defn.nodes.append(NodeDef(
            node_id="n_up",
            node_type="product_spec",
            deps=[],
        ))
        for i, n in enumerate(defn.nodes):
            if n.node_id == node_id:
                data = n.model_dump()
                data["deps"] = [dep_decl.model_dump()]
                defn.nodes[i] = NodeDef.model_validate(data)
        state.node_states["n_up"] = NodeState(node_id="n_up", status=NodeStatus.BLOCKED)
        pr = _make_pr_detail()
        ctx = ReviewContext(
            pipeline_def=defn,
            pipeline_state=state,
            node_id=node_id,
            pr_id=pr.pr_id,
            pr_detail=pr,
            template=pr.template,
            content_bytes={"x.py": b"x=1"},
            diff_added_lines=1,
            diff_deleted_lines=0,
            diff_unified="",
            role_instance_id="s1",
            token_payload={},
            clearance=ClassificationLevel.INTERNAL,
            submitter_role="server_impl",
            node_type="server_impl",
            artifact_classification=ClassificationLevel.INTERNAL,
            change_class_declared="compatible",
            addendum_declared=False,
            external_refs=[],
        )
        engine = RuleEngine(rules=[R_DEPS_DONE])
        res = engine.evaluate(ctx)
        check = next(c for c in res["checks"] if c["rule_id"] == "R_DEPS_DONE")
        assert check["pass"] is False

    def test_r_file_format_pass(self):
        ctx = _make_ctx(content={"readme.md": b"# hi", "cfg.json": b"{}", "a.yaml": b"a: 1"})
        engine = RuleEngine(rules=[R_FILE_FORMAT])
        res = engine.evaluate(ctx)
        check = next(c for c in res["checks"] if c["rule_id"] == "R_FILE_FORMAT")
        assert check["pass"] is True

    def test_r_file_format_fail_empty(self):
        ctx = _make_ctx(content={"a.md": b""})
        engine = RuleEngine(rules=[R_FILE_FORMAT])
        res = engine.evaluate(ctx)
        check = next(c for c in res["checks"] if c["rule_id"] == "R_FILE_FORMAT")
        assert check["pass"] is False

    def test_r_completeness_contract_pass(self):
        ctx = _make_ctx(content={"x.json": b'{"a": {"b": 1}}'})
        engine = RuleEngine(rules=[R_COMPLETENESS_CONTRACT])
        res = engine.evaluate(ctx)
        check = next(c for c in res["checks"] if c["rule_id"] == "R_COMPLETENESS_CONTRACT")
        assert check["pass"] is True

    def test_r_completeness_contract_fail_trivial(self):
        ctx = _make_ctx(content={"x.json": b'{"a": {"b": 1}}'})
        from skills.models import CompletenessContract

        class _FakeSkill:
            def __init__(self):
                self.review_gates = type("RG", (), {})()
                self.completeness_contract = CompletenessContract(
                    json_paths=["$.missing.path"], mode="and", threshold=1.0
                )

        sk = _FakeSkill()
        ctx = _make_ctx(
            content={"x.json": b'{"a": {"b": 1}}'},
            skill=sk,
        )
        engine = RuleEngine(rules=[R_COMPLETENESS_CONTRACT])
        res = engine.evaluate(ctx)
        check = next(c for c in res["checks"] if c["rule_id"] == "R_COMPLETENESS_CONTRACT")
        assert check["pass"] is False

    def test_r_secret_scan_pass(self):
        ctx = _make_ctx(content={"doc.md": b"hello world\nhttps://example.com/path"})
        engine = RuleEngine(rules=[R_SECRET_SCAN])
        res = engine.evaluate(ctx)
        check = next(c for c in res["checks"] if c["rule_id"] == "R_SECRET_SCAN")
        assert check["pass"] is True

    def test_r_secret_scan_fail(self):
        ctx = _make_ctx(content={"doc.md": b"key=AKIAIOSFODNN7EXAMPLE\n"})
        engine = RuleEngine(rules=[R_SECRET_SCAN])
        res = engine.evaluate(ctx)
        check = next(c for c in res["checks"] if c["rule_id"] == "R_SECRET_SCAN")
        assert check["pass"] is False

    def test_r_url_safety_pass(self):
        ctx = _make_ctx(external_refs=["https://example.com/doc"])
        engine = RuleEngine(rules=[R_URL_SAFETY])
        res = engine.evaluate(ctx)
        check = next(c for c in res["checks"] if c["rule_id"] == "R_URL_SAFETY")
        assert check["pass"] is True

    def test_r_url_safety_fail(self):
        ctx = _make_ctx(external_refs=["https://evil.com/download"])
        engine = RuleEngine(rules=[R_URL_SAFETY])
        res = engine.evaluate(ctx)
        check = next(c for c in res["checks"] if c["rule_id"] == "R_URL_SAFETY")
        assert check["pass"] is False

    def test_r_malware_scan_pass(self):
        ctx = _make_ctx(content={"a.md": b"# hello", "b.py": b"print(1)\n"})
        engine = RuleEngine(rules=[R_MALWARE_SCAN])
        res = engine.evaluate(ctx)
        check = next(c for c in res["checks"] if c["rule_id"] == "R_MALWARE_SCAN")
        assert check["pass"] is True

    def test_r_malware_scan_fail_mz(self):
        ctx = _make_ctx(content={"a.exe": b"MZ\x90\x00\x03\x00rest of binary"})
        engine = RuleEngine(rules=[R_MALWARE_SCAN])
        res = engine.evaluate(ctx)
        check = next(c for c in res["checks"] if c["rule_id"] == "R_MALWARE_SCAN")
        assert check["pass"] is False

    def test_r_external_ref_ownership_pass(self):
        ctx = _make_ctx(external_refs=["https://github.com/org/repo/commit/abc123"])
        engine = RuleEngine(rules=[R_EXTERNAL_REF_OWNERSHIP])
        res = engine.evaluate(ctx)
        check = next(c for c in res["checks"] if c["rule_id"] == "R_EXTERNAL_REF_OWNERSHIP")
        assert check["pass"] is True

    def test_r_external_ref_ownership_stub_always_pass(self):
        ctx = _make_ctx(external_refs=["https://somewhere.else/abc123"])
        engine = RuleEngine(rules=[R_EXTERNAL_REF_OWNERSHIP])
        res = engine.evaluate(ctx)
        check = next(c for c in res["checks"] if c["rule_id"] == "R_EXTERNAL_REF_OWNERSHIP")
        assert check["pass"] is True

    def test_r_commit_stability_pass(self):
        ctx = _make_ctx(template_extras={"volatile_declared": True})
        engine = RuleEngine(rules=[R_COMMIT_STABILITY])
        res = engine.evaluate(ctx)
        check = next(c for c in res["checks"] if c["rule_id"] == "R_COMMIT_STABILITY")
        assert check["pass"] is True

    def test_r_commit_stability_warn(self):
        ctx = _make_ctx(template_extras={})
        engine = RuleEngine(rules=[R_COMMIT_STABILITY])
        res = engine.evaluate(ctx)
        check = next(c for c in res["checks"] if c["rule_id"] == "R_COMMIT_STABILITY")
        assert check["pass"] is False
        assert check["on_fail"] == "warn"

    def test_r_addendum_vs_changed_pass(self):
        ctx = _make_ctx(addendum_declared=True, deleted=0)
        engine = RuleEngine(rules=[R_ADDENDUM_VS_CHANGED])
        res = engine.evaluate(ctx)
        check = next(c for c in res["checks"] if c["rule_id"] == "R_ADDENDUM_VS_CHANGED")
        assert check["pass"] is True

    def test_r_addendum_vs_changed_fail(self):
        ctx = _make_ctx(addendum_declared=True, deleted=1)
        engine = RuleEngine(rules=[R_ADDENDUM_VS_CHANGED])
        res = engine.evaluate(ctx)
        check = next(c for c in res["checks"] if c["rule_id"] == "R_ADDENDUM_VS_CHANGED")
        assert check["pass"] is False
        assert "E_ADDENDUM_DELETES_ROWS" in check["message"]

    def test_r_change_class_consistency_pass(self):
        ctx = _make_ctx(
            change_class_declared="compatible",
            diff_unified="+  endpoints:\n+    /a: get\n",
        )
        engine = RuleEngine(rules=[R_CHANGE_CLASS_CONSISTENCY])
        res = engine.evaluate(ctx)
        check = next(c for c in res["checks"] if c["rule_id"] == "R_CHANGE_CLASS_CONSISTENCY")
        assert check["pass"] is True

    def test_r_change_class_consistency_fail(self):
        ctx = _make_ctx(
            change_class_declared="compatible",
            diff_unified='-  "endpoints":\n-    /old: delete\n',
        )
        engine = RuleEngine(rules=[R_CHANGE_CLASS_CONSISTENCY])
        res = engine.evaluate(ctx)
        check = next(c for c in res["checks"] if c["rule_id"] == "R_CHANGE_CLASS_CONSISTENCY")
        assert check["pass"] is False

    def test_r_impact_claim_completeness_pass(self):
        ctx = _make_ctx(template_extras={
            "modification_declaration": {"impact_claimed_downstream": []},
        })
        engine = RuleEngine(rules=[R_IMPACT_CLAIM_COMPLETENESS])
        res = engine.evaluate(ctx)
        check = next(c for c in res["checks"] if c["rule_id"] == "R_IMPACT_CLAIM_COMPLETENESS")
        assert check["pass"] is True

    def test_r_impact_claim_completeness_fail(self):
        defn, state, node_id = _make_basic_pipeline("product_spec")
        defn.nodes.append(NodeDef(
            node_id="n_down",
            node_type="server_impl",
            deps=[DepDeclaration(upstream=node_id, presence=DepPresence.REQUIRED)],
        ))
        state.node_states["n_down"] = NodeState(node_id="n_down", status=NodeStatus.BLOCKED)
        pr = _make_pr_detail(template_extras={
            "modification_declaration": {"impact_claimed_downstream": ["wrong_id"]},
        })
        ctx = ReviewContext(
            pipeline_def=defn,
            pipeline_state=state,
            node_id=node_id,
            pr_id=pr.pr_id,
            pr_detail=pr,
            template=pr.template,
            content_bytes={"x.md": b"x"},
            diff_added_lines=1,
            diff_deleted_lines=0,
            diff_unified="",
            role_instance_id="p1",
            token_payload={},
            clearance=ClassificationLevel.INTERNAL,
            submitter_role="product",
            node_type="product_spec",
            artifact_classification=ClassificationLevel.INTERNAL,
            change_class_declared="compatible",
            addendum_declared=False,
            external_refs=[],
        )
        engine = RuleEngine(rules=[R_IMPACT_CLAIM_COMPLETENESS])
        res = engine.evaluate(ctx)
        check = next(c for c in res["checks"] if c["rule_id"] == "R_IMPACT_CLAIM_COMPLETENESS")
        assert check["pass"] is False

    def test_r_human_review_required_pass_normal(self):
        ctx = _make_ctx(
            node_type="product_spec",
            change_class_declared="compatible",
            artifact_class=ClassificationLevel.INTERNAL,
            template_extras={"version": 2},
        )
        engine = RuleEngine(rules=[R_HUMAN_REVIEW_REQUIRED])
        res = engine.evaluate(ctx)
        check = next(c for c in res["checks"] if c["rule_id"] == "R_HUMAN_REVIEW_REQUIRED")
        assert check["pass"] is True

    def test_r_human_review_required_needs_human(self):
        ctx = _make_ctx(
            node_type="design_asset",
            change_class_declared="compatible",
        )
        engine = RuleEngine(rules=[R_HUMAN_REVIEW_REQUIRED])
        res = engine.evaluate(ctx)
        check = next(c for c in res["checks"] if c["rule_id"] == "R_HUMAN_REVIEW_REQUIRED")
        assert check["pass"] is False
        assert check["on_fail"] == "needs_human"


class TestTr72SecretScan:
    def test_secret_scan_hit_aws_and_high_entropy(self):
        secret_b64 = _rand_b64(20)
        content = f"AKIAIOSFODNN7EXAMPLE random_high_entropy={secret_b64}\n".encode()
        ctx = _make_ctx(content={"config.env": content})
        engine = RuleEngine()
        res = engine.evaluate(ctx)
        assert res["verdict"] == "reject"
        assert res["rejected_by"] == "R_SECRET_SCAN"

    def test_secret_scan_pass_normal_doc(self):
        content = b"hello world! This is normal documentation with normal URLs https://example.com/path\n"
        ctx = _make_ctx(content={"README.md": content})
        engine = RuleEngine()
        res = engine.evaluate(ctx)
        secret_checks = [c for c in res["checks"] if c["rule_id"] == "R_SECRET_SCAN"]
        assert len(secret_checks) == 1
        assert secret_checks[0]["pass"] is True


class TestTr73AddendumVsChanged:
    def test_addendum_add_only_pass(self):
        ctx = _make_ctx(
            addendum_declared=True,
            added=5,
            deleted=0,
        )
        engine = RuleEngine()
        res = engine.evaluate(ctx)
        add_checks = [c for c in res["checks"] if c["rule_id"] == "R_ADDENDUM_VS_CHANGED"]
        assert add_checks[0]["pass"] is True

    def test_addendum_with_deletes_reject(self):
        ctx = _make_ctx(
            addendum_declared=True,
            added=3,
            deleted=1,
        )
        engine = RuleEngine()
        res = engine.evaluate(ctx)
        add_checks = [c for c in res["checks"] if c["rule_id"] == "R_ADDENDUM_VS_CHANGED"]
        assert add_checks[0]["pass"] is False
        assert res["rejected_by"] == "R_ADDENDUM_VS_CHANGED" or "addendum" in (add_checks[0]["message"].lower())


class TestTr74ChangeClassConsistency:
    def test_compatible_but_deletes_endpoints_reject(self):
        diff = """--- a/api.yaml
+++ b/api.yaml
@@ -1,4 +1,2 @@
 title: myapi
-  endpoints:
-    /v1/old: get
 version: 1
"""
        ctx = _make_ctx(
            change_class_declared="compatible",
            diff_unified=diff,
            added=2,
            deleted=2,
        )
        engine = RuleEngine()
        res = engine.evaluate(ctx)
        ccc = [c for c in res["checks"] if c["rule_id"] == "R_CHANGE_CLASS_CONSISTENCY"]
        assert ccc[0]["pass"] is False
        assert res["rejected_by"] == "R_CHANGE_CLASS_CONSISTENCY" or any(
            c["rule_id"] == "R_CHANGE_CLASS_CONSISTENCY" and not c["pass"] for c in res["checks"]
        )

    def test_breaking_allows_delete(self):
        diff = """--- a/api.yaml
+++ b/api.yaml
@@ -1,4 +1,2 @@
-  endpoints:
-    /old: delete
 version: 1
"""
        ctx = _make_ctx(
            change_class_declared="breaking",
            diff_unified=diff,
        )
        engine = RuleEngine(rules=[R_CHANGE_CLASS_CONSISTENCY])
        res = engine.evaluate(ctx)
        ccc = [c for c in res["checks"] if c["rule_id"] == "R_CHANGE_CLASS_CONSISTENCY"]
        assert ccc[0]["pass"] is True


class TestTr75HashChainBreak:
    def test_worm_chain_break_locates_id_20(self, tmp_path: Path):
        db = tmp_path / "worm.db"
        worm = WormStorage(db)
        for i in range(50):
            entry = AuditLogEntry(
                prev_hash="",
                action="TEST",
                actor="bot",
                payload={"i": i + 1},
                hash="",
                created_at=datetime.now(timezone.utc).isoformat(),
            )
            worm.insert(entry)

        all_entries = worm.list(limit=100)
        assert len(all_entries) == 50

        conn = worm._raw_connection()
        cur = conn.cursor()
        cur.execute("UPDATE audit_log SET hash = ? WHERE id = ?", ("sha256:BROKEN", 20))
        conn.commit()

        broken_entries = worm.list(limit=100)
        valid, first_bad = validate_chain(broken_entries)
        assert valid is False
        assert first_bad is not None
        entry_at_bad = broken_entries[first_bad]
        assert entry_at_bad.id == 20


class TestTr76WormOnlyInsert:
    def test_no_update_delete_public_methods(self):
        methods = [name for name, _ in inspect.getmembers(WormStorage, predicate=inspect.isfunction)]
        assert "update" not in methods
        assert "delete" not in methods

    def test_getattr_raises_on_update_delete(self, tmp_path: Path):
        w = WormStorage(tmp_path / "worm2.db")
        with pytest.raises(AttributeError):
            getattr(w, "update")
        with pytest.raises(AttributeError):
            getattr(w, "delete")

    def test_insert_only(self, tmp_path: Path):
        w = WormStorage(tmp_path / "worm3.db")
        assert hasattr(w, "insert")
        assert hasattr(w, "list")
        assert hasattr(w, "tip_hash")
        assert callable(getattr(w, "insert"))
        assert callable(getattr(w, "list"))
        assert isinstance(w.tip_hash, str)


class TestTr77NeedsHumanScenarios:
    def test_case1_api_contract_v1_needs_human_no_approvals(self, tmp_path: Path):
        defn, state, node_id = _make_basic_pipeline("api_contract")
        for i, n in enumerate(defn.nodes):
            if n.node_id == node_id:
                data = n.model_dump()
                data["node_type"] = "api_contract"
                data["role_assignments"] = []
                defn.nodes[i] = NodeDef.model_validate(data)
        store = _SimpleStateStore(defn, state)
        store.pending_prs[node_id] = "pr-case1"
        worm = WormStorage(tmp_path / "case1.db")
        service = MergeApproveService(hub=None, worm=worm, state_store=store)
        with pytest.raises(E_HUMAN_REVIEW_REQUIRED):
            service.approve(
                pipeline_id="p-test",
                pr_id="pr-case1",
                bot_actor="bot",
                human_approvals=0,
                required_humans=1,
            )

    def test_case2_confidential_classification_human_approved(self, tmp_path: Path):
        defn, state, node_id = _make_basic_pipeline("product_spec")
        for i, n in enumerate(defn.nodes):
            if n.node_id == node_id:
                data = n.model_dump()
                data["classification"] = int(ClassificationLevel.CONFIDENTIAL)
                data["role_assignments"] = []
                defn.nodes[i] = NodeDef.model_validate(data)
        store = _SimpleStateStore(defn, state)
        store.pending_prs[node_id] = "pr-case2"
        worm = WormStorage(tmp_path / "case2.db")
        service = MergeApproveService(hub=None, worm=worm, state_store=store)
        result = service.approve(
            pipeline_id="p-test",
            pr_id="pr-case2",
            bot_actor="bot",
            human_approvals=1,
            required_humans=1,
        )
        assert result["node_new_status"] == "done"
        assert "commit_sha" in result
        assert "artifact_ref" in result

    def test_case3_breaking_change_no_human_reject(self, tmp_path: Path):
        defn, state, node_id = _make_basic_pipeline("server_impl")
        for i, n in enumerate(defn.nodes):
            if n.node_id == node_id:
                data = n.model_dump()
                data["node_type"] = "server_impl"
                data["role_assignments"] = []
                defn.nodes[i] = NodeDef.model_validate(data)
        store = _SimpleStateStore(defn, state)
        store.pending_prs[node_id] = "pr-case3"
        worm = WormStorage(tmp_path / "case3.db")
        from audit.engine import Rule, RuleEngine

        def force_needs_human(ctx):
            return False

        engine = RuleEngine(
            rules=[
                Rule(
                    rule_id="FORCE_NEEDS_HUMAN",
                    priority=100,
                    on_fail="needs_human",
                    condition=force_needs_human,
                    message_template="forced",
                )
            ]
        )
        service = MergeApproveService(hub=None, worm=worm, state_store=store, engine=engine)
        with pytest.raises(E_HUMAN_REVIEW_REQUIRED):
            service.approve(
                pipeline_id="p-test",
                pr_id="pr-case3",
                bot_actor="bot",
                human_approvals=0,
                required_humans=1,
            )
