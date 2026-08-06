from __future__ import annotations

from typing import TYPE_CHECKING, Any

from skills.models import SkillDefinition

if TYPE_CHECKING:
    from audit.engine import Rule


def _make_no_path_traversal_condition():
    def _cond(ctx: Any) -> bool:
        for path in (ctx.content_bytes or {}).keys():
            if ".." in path.split("/") or ".." in path.split("\\"):
                return False
            if ".." in str(path):
                return False
        return True
    return _cond


def compile_to_review_rules(skill: SkillDefinition) -> list["Rule"]:
    from audit.engine import Rule

    rules: list[Rule] = []

    def _r_classification_clearance_closure():
        def _cond(ctx):
            try:
                clearance_val = int(getattr(ctx, "clearance", 0))
            except Exception:
                clearance_val = 0
            try:
                artifact_val = int(getattr(ctx, "artifact_classification", 0))
            except Exception:
                artifact_val = 0
            return clearance_val >= artifact_val
        return _cond

    rules.append(Rule(
        rule_id="R_CLASSIFICATION_CLEARANCE",
        priority=88,
        on_fail="reject",
        condition=_r_classification_clearance_closure(),
        message_template="Clearance below artifact classification level",
    ))

    if skill.required_fields:
        required_fields = list(skill.required_fields)

        def _r_required_fields_closure(fields):
            def _cond(ctx):
                keys = set((ctx.template or {}).keys())
                return all(f in keys for f in fields)
            return _cond

        rules.append(Rule(
            rule_id="R_REQUIRED_FIELDS",
            priority=90,
            on_fail="reject",
            condition=_r_required_fields_closure(required_fields),
            message_template=f"Template missing required fields: {required_fields}",
        ))

    if skill.deps:
        from orchestration.models import DepPresence, DepStrictness, NodeStatus
        from orchestration.deps import resolve_effective_deps

        skill_deps = list(skill.deps)

        def _r_deps_done_closure(deps_list):
            def _cond(ctx):
                try:
                    effective = resolve_effective_deps(ctx.node_id, ctx.pipeline_def, ctx.pipeline_state)
                except Exception:
                    effective = []

                ctx_deps_map: dict[str, Any] = {}
                for up_id, decl in effective:
                    ctx_deps_map[up_id] = decl

                node_map: dict[str, Any] = {n.node_id: n for n in getattr(ctx.pipeline_def, "nodes", [])}

                for skill_dep in deps_list:
                    dep_upstream = skill_dep.upstream
                    presence = skill_dep.presence
                    if isinstance(presence, str):
                        presence = DepPresence(presence)
                    strictness = skill_dep.strictness
                    if isinstance(strictness, str):
                        strictness = DepStrictness(strictness)

                    up_node_in_pipeline = None
                    for nid, ndef in node_map.items():
                        if getattr(ndef, "node_type", None) == dep_upstream:
                            up_node_in_pipeline = nid
                            break
                        if nid == dep_upstream:
                            up_node_in_pipeline = nid
                            break

                    if up_node_in_pipeline is None:
                        if presence == DepPresence.IF_PRESENT:
                            continue
                        if presence == DepPresence.OPTIONAL:
                            continue
                        if presence == DepPresence.REQUIRED:
                            return False
                        continue

                    up_state = None
                    if hasattr(ctx.pipeline_state, "node_states"):
                        up_state = ctx.pipeline_state.node_states.get(up_node_in_pipeline)

                    if up_state is None:
                        if presence == DepPresence.IF_PRESENT:
                            return False
                        if presence == DepPresence.REQUIRED:
                            return False
                        continue

                    up_status = up_state.status
                    if isinstance(up_status, str):
                        up_status = NodeStatus(up_status)

                    up_ok: bool
                    if strictness == DepStrictness.ACCEPTS_DRAFT:
                        up_ok = up_status in {NodeStatus.DONE, NodeStatus.DRAFT}
                    else:
                        up_ok = up_status == NodeStatus.DONE

                    if presence in {DepPresence.REQUIRED, DepPresence.IF_PRESENT}:
                        if not up_ok:
                            return False

                return True
            return _cond

        rules.append(Rule(
            rule_id="R_DEPS_DONE",
            priority=85,
            on_fail="reject",
            condition=_r_deps_done_closure(skill_deps),
            message_template="Skill deps not satisfied for upstream dependencies",
        ))

    if skill.completeness_contract is not None:
        contract = skill.completeness_contract
        on_fail_action = "reject"
        if skill.metadata and isinstance(skill.metadata, dict):
            on_fail_meta = skill.metadata.get("completeness_on_fail")
            if on_fail_meta in {"reject", "warn", "needs_human"}:
                on_fail_action = on_fail_meta

        def _r_completeness_closure(cc):
            def _cond(ctx):
                from skills.completeness_executor import evaluate
                import json
                try:
                    import yaml as _yaml
                except Exception:
                    _yaml = None

                content_obj = None
                for content in (ctx.content_bytes or {}).values():
                    try:
                        content_obj = json.loads(content.decode("utf-8"))
                        break
                    except Exception:
                        pass
                    if _yaml is not None:
                        try:
                            content_obj = _yaml.safe_load(content.decode("utf-8"))
                            if content_obj is not None:
                                break
                        except Exception:
                            pass

                if content_obj is None:
                    content_obj = ctx.template or {}

                passed, _ = evaluate(cc, content_obj)
                return passed
            return _cond

        rules.append(Rule(
            rule_id="R_COMPLETENESS_CONTRACT",
            priority=80,
            on_fail=on_fail_action,
            condition=_r_completeness_closure(contract),
            message_template="Completeness contract json_paths not satisfied",
        ))

    format_ok = True
    try:
        max_len = skill.output_guides.max_len_bytes if skill.output_guides else 10_000_000
        allowed_exts_meta = skill.metadata.get("allowed_extensions") if isinstance(skill.metadata, dict) else None
        allowed_exts: set[str] | None = None
        if allowed_exts_meta and isinstance(allowed_exts_meta, list):
            allowed_exts = {e.lower().lstrip(".") for e in allowed_exts_meta if isinstance(e, str)}

        def _r_file_format_closure(max_bytes, ext_set):
            def _cond(ctx):
                total = 0
                for path, content in (ctx.content_bytes or {}).items():
                    if not content or len(content) == 0:
                        return False
                    if ext_set is not None:
                        ext = path.rsplit(".", 1)[-1].lower() if "." in path else ""
                        if ext and ext not in ext_set:
                            return False
                    total += len(content)
                    if total > max_bytes:
                        return False
                return True
            return _cond

        rules.append(Rule(
            rule_id="R_FILE_FORMAT",
            priority=82,
            on_fail="reject",
            condition=_r_file_format_closure(max_len, allowed_exts),
            message_template=f"File format/size check failed (max_bytes={max_len}, allowed_exts={allowed_exts})",
        ))
    except Exception:
        format_ok = False

    if skill.review_gates and skill.review_gates.requires_human:
        def _r_human_review_closure(_skill):
            def _cond(ctx):
                return False
            return _cond

        rules.append(Rule(
            rule_id="R_HUMAN_REVIEW_REQUIRED",
            priority=60,
            on_fail="needs_human",
            condition=_r_human_review_closure(skill),
            message_template="Human review required by skill review_gates.requires_human",
        ))

    if skill.metadata and isinstance(skill.metadata, dict):
        no_traversal = skill.metadata.get("no_path_traversal")
        if no_traversal:
            rules.append(Rule(
                rule_id="R_NO_PATH_TRAVERSAL",
                priority=91,
                on_fail="reject",
                condition=_make_no_path_traversal_condition(),
                message_template="Path traversal detected in content paths (contains '..')",
            ))

    if skill.id == "generic-skill":
        rules.append(Rule(
            rule_id="R_NO_PATH_TRAVERSAL",
            priority=91,
            on_fail="reject",
            condition=_make_no_path_traversal_condition(),
            message_template="Path traversal detected in content paths (contains '..')",
        ))

    return rules
