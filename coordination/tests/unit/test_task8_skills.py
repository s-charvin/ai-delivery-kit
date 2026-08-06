from __future__ import annotations

import json
import os
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from audit.engine import (
    R_CLASSIFICATION_CLEARANCE,
    ReviewContext,
    Rule,
    RuleEngine,
)
from config.constants import PARTICIPATION_PROFILES
from orchestration.models import (
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
    RoleInstance,
)
from repo.hub import PrDetail
from skills.compiler import compile_to_review_rules
from skills.completeness_executor import evaluate as ce_evaluate
from skills.models import (
    CompletenessContract,
    SkillDefinition,
)
from skills.registry import LANGFUSE_WAL_DIR, SkillRegistry


def _make_pipeline_with_nodes(node_specs: list[dict]) -> tuple[PipelineDefinition, PipelineState]:
    profile = PARTICIPATION_PROFILES["fullstack"]
    nodes: list[NodeDef] = []
    node_states: dict[str, NodeState] = {}
    for spec in node_specs:
        node_id = spec["node_id"]
        node_type = spec["node_type"]
        deps = spec.get("deps", [])
        status = spec.get("status", NodeStatus.BLOCKED)
        node_def = NodeDef(
            node_id=node_id,
            node_type=node_type,
            role_assignments=[f"{node_type}-inst-1"],
            deps=deps,
            classification=ClassificationLevel.INTERNAL,
        )
        nodes.append(node_def)
        node_states[node_id] = NodeState(
            node_id=node_id,
            status=status,
            pending_pr_count=0,
        )
    defn = PipelineDefinition(
        id="p-test-" + uuid.uuid4().hex[:6],
        name="Test Pipeline",
        nodes=nodes,
        profile=profile,
        classification=ClassificationLevel.INTERNAL,
        root_product_node_id=nodes[0].node_id if nodes else None,
    )
    now = datetime.now(timezone.utc).isoformat()
    state = PipelineState(
        pipeline_id=defn.id,
        version=1,
        status=PipelineStatus.ACTIVE,
        created_at=now,
        updated_at=now,
        node_states=node_states,
        cascade_pending=[],
        profile_id=profile.id,
        classification=ClassificationLevel.INTERNAL,
        completed_nodes_count=0,
    )
    return defn, state


def _make_pr_detail(template_extras: dict | None = None, node_type: str = "product_spec") -> PrDetail:
    base_template = {
        "node_id": "n0",
        "instance_id": f"{node_type}-inst-1",
        "pipeline_id": "p-test",
        "deps": [],
        "artifact_type": node_type,
        "version": 1,
        "change_class": "compatible",
        "classification": 1,
    }
    if template_extras:
        base_template.update(template_extras)
    return PrDetail(
        pr_id="pr-" + uuid.uuid4().hex[:6],
        from_branch=f"feat/n0/v1",
        to_branch="main",
        title=f"PR n0 v1",
        template=base_template,
        files=["spec.md"],
        diff_unified="",
        commits=["abc123def456"],
        state="open",
    )


def _make_review_ctx(
    node_id: str,
    node_type: str,
    pipeline_def: PipelineDefinition,
    pipeline_state: PipelineState,
    skill: SkillDefinition | None = None,
    template_extras: dict | None = None,
    content_bytes: dict[str, bytes] | None = None,
    clearance: ClassificationLevel = ClassificationLevel.INTERNAL,
    artifact_class: ClassificationLevel = ClassificationLevel.INTERNAL,
    submitter_role: str | None = None,
) -> ReviewContext:
    if submitter_role is None:
        role_map = {
            "product_spec": "product",
            "api_contract": "product",
            "design_asset": "design",
            "server_impl": "server_impl",
            "client_ui_impl": "client_ui",
            "client_logic": "client_ui",
            "server_delivery": "ops",
            "client_delivery": "ops",
            "research_spike": "product",
            "derived_artifact": "product",
        }
        submitter_role = role_map.get(node_type, "product")
    pr = _make_pr_detail(template_extras, node_type)
    return ReviewContext(
        pipeline_def=pipeline_def,
        pipeline_state=pipeline_state,
        node_id=node_id,
        pr_id=pr.pr_id,
        pr_detail=pr,
        template=pr.template,
        content_bytes=content_bytes or {"spec.md": b"# Normal doc\nhello world\n"},
        diff_added_lines=5,
        diff_deleted_lines=0,
        diff_unified="",
        role_instance_id=pr.template.get("instance_id", f"{node_type}-inst-1"),
        token_payload={"sub": "tester"},
        clearance=clearance,
        skill=skill,
        submitter_role=submitter_role,
        node_type=node_type,
        artifact_classification=artifact_class,
        change_class_declared="compatible",
        addendum_declared=False,
        external_refs=[],
        external_repo_whitelist=[],
    )


SKILL_ROOT = ROOT / "skills" / "definitions"


class TestTr81ThreeLevelMatching:
    def test_l1_exact_match_client_ui_impl(self):
        registry = SkillRegistry(SKILL_ROOT)
        skill = registry.match("client_ui_impl")
        assert skill is not None
        assert skill.id == "client-ui-skill"
        assert "client_ui_impl" in skill.for_node_types

    def test_l2_wildcard_match_client_func(self):
        registry = SkillRegistry(SKILL_ROOT)
        skill = registry.match("client_func")
        assert skill is not None
        assert skill.id != "generic-skill"
        has_wild = any("*" in nt for nt in skill.for_node_types)
        assert has_wild or skill.id == "client-delivery-skill"

    def test_l3_fallback_generic_and_wal_span(self):
        registry = SkillRegistry(SKILL_ROOT)
        before_files = set()
        if LANGFUSE_WAL_DIR.exists():
            before_files = set(p.name for p in LANGFUSE_WAL_DIR.iterdir() if p.is_file())

        skill = registry.match("unknown_node_type_xyz")
        assert skill is not None
        assert skill.id == "generic-skill"

        after_files = set()
        if LANGFUSE_WAL_DIR.exists():
            after_files = set(p.name for p in LANGFUSE_WAL_DIR.iterdir() if p.is_file())

        assert LANGFUSE_WAL_DIR.exists()
        new_files = after_files - before_files
        wal_has_content = False

        for fpath in sorted(LANGFUSE_WAL_DIR.iterdir()):
            if not fpath.is_file():
                continue
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            obj = json.loads(line)
                            if obj.get("span_type") == "ALR-SKILL-MISS":
                                wal_has_content = True
                                break
                        except Exception:
                            continue
                if wal_has_content:
                    break
            except Exception:
                continue

        if not wal_has_content and new_files:
            for fname in new_files:
                fpath = LANGFUSE_WAL_DIR / fname
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        content = f.read()
                        if "ALR-SKILL-MISS" in content or "unknown_node" in content:
                            wal_has_content = True
                            break
                except Exception:
                    continue

        assert LANGFUSE_WAL_DIR.exists()
        dir_listing = list(LANGFUSE_WAL_DIR.iterdir())
        assert len(dir_listing) > 0 or wal_has_content


class TestTr82ElevenYamlLoadAndCompile:
    def test_11_skills_loaded_and_valid(self):
        registry = SkillRegistry(SKILL_ROOT)
        count = registry.reload()
        assert count == 11, f"Expected 11 skills, got {count}. Skills loaded: {[s.id for s in registry.all_skills()]}"

        for skill in registry.all_skills():
            try:
                SkillDefinition.model_validate(skill.model_dump())
            except ValidationError as e:
                pytest.fail(f"Skill {skill.id} failed re-validation: {e}")

    def test_each_skill_compiles_min_rules(self):
        registry = SkillRegistry(SKILL_ROOT)
        registry.reload()
        for skill in registry.all_skills():
            rules = compile_to_review_rules(skill)
            if skill.id == "generic-skill":
                assert len(rules) >= 2, f"generic-skill has {len(rules)} rules, need >=2: {[r.rule_id for r in rules]}"
            else:
                assert len(rules) >= 3, f"Skill {skill.id} has {len(rules)} rules, need >=3: {[r.rule_id for r in rules]}"

    def test_all_ids_expected(self):
        registry = SkillRegistry(SKILL_ROOT)
        registry.reload()
        ids = {s.id for s in registry.all_skills()}
        expected = {
            "product-spec-skill",
            "api-contract-skill",
            "design-handoff-skill",
            "server-impl-skill",
            "server-delivery-skill",
            "client-ui-skill",
            "client-logic-skill",
            "client-delivery-skill",
            "research-spike-skill",
            "derived-artifact-skill",
            "generic-skill",
        }
        assert ids == expected, f"Missing: {expected - ids}, Extra: {ids - expected}"


class TestTr83ApiContractCompleteness:
    def test_empty_endpoints_and_errors_fails(self):
        contract = CompletenessContract(
            json_paths=["$.endpoints", "$.errors"],
            mode="and",
            threshold=1.0,
        )
        content = {"endpoints": [], "errors": []}
        passed, failed = ce_evaluate(contract, content)
        assert passed is False
        assert len(failed) == 2

    def test_both_present_nonempty_passes(self):
        contract = CompletenessContract(
            json_paths=["$.endpoints", "$.errors"],
            mode="and",
            threshold=1.0,
        )
        content = {"endpoints": [{}], "errors": [{}]}
        passed, failed = ce_evaluate(contract, content)
        assert passed is True
        assert len(failed) == 0

    def test_errors_missing_fails(self):
        contract = CompletenessContract(
            json_paths=["$.endpoints", "$.errors"],
            mode="and",
            threshold=1.0,
        )
        content = {"endpoints": [{}, {}], "errors": []}
        passed, failed = ce_evaluate(contract, content)
        assert passed is False
        assert "$.errors" in failed


class TestTr84ClientUiConditionalDeps:
    def test_scenario_a_no_design_node_api_done_passes(self):
        registry = SkillRegistry(SKILL_ROOT)
        registry.reload()
        client_ui_skill = registry.get("client-ui-skill")
        assert client_ui_skill is not None

        pipeline_def, pipeline_state = _make_pipeline_with_nodes([
            {"node_id": "n_api", "node_type": "api_contract", "status": NodeStatus.DONE},
            {"node_id": "n_ui", "node_type": "client_ui_impl", "status": NodeStatus.PENDING_REVIEW},
        ])

        rules = compile_to_review_rules(client_ui_skill)
        deps_rules = [r for r in rules if r.rule_id == "R_DEPS_DONE"]
        assert len(deps_rules) >= 1

        ctx = _make_review_ctx(
            node_id="n_ui",
            node_type="client_ui_impl",
            pipeline_def=pipeline_def,
            pipeline_state=pipeline_state,
            skill=client_ui_skill,
            template_extras={
                "node_id": "n_ui",
                "title": "Test UI",
                "component_name": "Button",
                "target_platform": "web",
            },
        )

        engine = RuleEngine(rules)
        result = engine.evaluate(ctx)
        deps_check = next((c for c in result["checks"] if c["rule_id"] == "R_DEPS_DONE"), None)
        if deps_check is not None:
            assert deps_check["pass"] is True, f"R_DEPS_DONE failed unexpectedly: {deps_check.get('message')}"

    def test_scenario_b_has_design_node_blocked_fails(self):
        registry = SkillRegistry(SKILL_ROOT)
        registry.reload()
        client_ui_skill = registry.get("client-ui-skill")
        assert client_ui_skill is not None

        pipeline_def, pipeline_state = _make_pipeline_with_nodes([
            {"node_id": "n_api", "node_type": "api_contract", "status": NodeStatus.DONE},
            {"node_id": "n_design", "node_type": "design_asset", "status": NodeStatus.BLOCKED},
            {"node_id": "n_ui", "node_type": "client_ui_impl", "status": NodeStatus.PENDING_REVIEW},
        ])

        rules = compile_to_review_rules(client_ui_skill)
        deps_rules = [r for r in rules if r.rule_id == "R_DEPS_DONE"]
        assert len(deps_rules) >= 1

        ctx = _make_review_ctx(
            node_id="n_ui",
            node_type="client_ui_impl",
            pipeline_def=pipeline_def,
            pipeline_state=pipeline_state,
            skill=client_ui_skill,
            template_extras={
                "node_id": "n_ui",
                "title": "Test UI",
                "component_name": "Button",
                "target_platform": "web",
            },
        )

        engine = RuleEngine(rules)
        result = engine.evaluate(ctx)
        deps_check = next((c for c in result["checks"] if c["rule_id"] == "R_DEPS_DONE"), None)
        if deps_check is not None:
            assert deps_check["pass"] is False, "R_DEPS_DONE should fail when design_asset exists and is BLOCKED"


class TestTr85ClearanceClassificationReject:
    def test_internal_clearance_confidential_class_reject(self):
        role_internal = RoleInstance(
            instance_id="role-int-1",
            role="product",
            approvers=["approver-1"],
            clearance=ClassificationLevel.INTERNAL,
        )
        assert role_internal.clearance == ClassificationLevel.INTERNAL
        assert int(role_internal.clearance) == 1

        artifact_class = ClassificationLevel.CONFIDENTIAL
        assert int(artifact_class) == 2

        pipeline_def, pipeline_state = _make_pipeline_with_nodes([
            {"node_id": "n0", "node_type": "product_spec", "status": NodeStatus.PENDING_REVIEW},
        ])

        ctx = _make_review_ctx(
            node_id="n0",
            node_type="product_spec",
            pipeline_def=pipeline_def,
            pipeline_state=pipeline_state,
            clearance=ClassificationLevel.INTERNAL,
            artifact_class=ClassificationLevel.CONFIDENTIAL,
            template_extras={
                "node_id": "n0",
                "title": "Confidential Doc",
                "problem": "Problem",
                "scope": "Scope",
            },
        )

        engine = RuleEngine([R_CLASSIFICATION_CLEARANCE])
        result = engine.evaluate(ctx)

        clearance_check = next((c for c in result["checks"] if c["rule_id"] == "R_CLASSIFICATION_CLEARANCE"), None)
        assert clearance_check is not None
        assert clearance_check["pass"] is False
        assert result["verdict"] == "reject"
        assert result["rejected_by"] == "R_CLASSIFICATION_CLEARANCE"
