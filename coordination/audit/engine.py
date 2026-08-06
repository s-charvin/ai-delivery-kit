from __future__ import annotations

import base64
import math
import re
import struct
import zipfile
from io import BytesIO
from typing import Any, Callable, Literal, Optional

from pydantic import BaseModel, ConfigDict

from config.constants import ERROR_CODES
from orchestration.deps import resolve_effective_deps
from orchestration.models import (
    ClassificationLevel,
    DepStrictness,
    NodeDef,
    NodeStatus,
    PipelineDefinition,
    PipelineState,
)
from repo.hub import PrDetail
from skills.models import SkillDefinition


_DEFAULT_NODE_TYPE_ROLE: dict[str, str] = {
    "product_spec": "product",
    "design_asset": "design",
    "api_contract": "product",
    "client_ui_impl": "client_ui",
    "server_impl": "server_impl",
    "server_test": "server_test",
    "client_test": "client_test",
    "delivery_gate": "ops",
}

_DEFAULT_REQUIRED_FIELDS: list[str] = [
    "node_id",
    "instance_id",
    "pipeline_id",
    "deps",
    "artifact_type",
    "version",
]

_DEFAULT_REVIEW_GATE_EXTS: set[str] = {
    "md",
    "yaml",
    "yml",
    "json",
    "py",
    "tsx",
    "ts",
    "js",
}

_MAX_FILE_SIZE_BYTES: int = 100 * 1024 * 1024


class Rule(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    rule_id: str
    priority: int
    on_fail: Literal["reject", "warn", "needs_human"]
    condition: str | Callable[["ReviewContext"], bool]
    message_template: str


class ReviewContext(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    pipeline_def: PipelineDefinition
    pipeline_state: PipelineState
    node_id: str
    pr_id: str
    pr_detail: PrDetail
    template: dict
    content_bytes: dict[str, bytes]
    diff_added_lines: int
    diff_deleted_lines: int
    diff_unified: str
    role_instance_id: str
    token_payload: dict
    clearance: ClassificationLevel
    skill: Any = None
    submitter_role: str
    node_type: str
    artifact_classification: ClassificationLevel
    change_class_declared: str
    addendum_declared: bool
    external_refs: list[str]
    external_repo_whitelist: list[str] = []
    trace_id: str = ""


def _shannon_entropy(data: str) -> float:
    if not data:
        return 0.0
    freq: dict[str, int] = {}
    for ch in data:
        freq[ch] = freq.get(ch, 0) + 1
    n = len(data)
    entropy = 0.0
    for count in freq.values():
        p = count / n
        entropy -= p * math.log2(p)
    return entropy


_SECRET_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("aws_access_key", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("aws_secret_key", re.compile(r"(?i)aws(.{0,20})?(?:[\"'`]([A-Za-z0-9/+=]{40})[\"'`])")),
    ("gcp_service_account", re.compile(r"\"type\":\s*\"service_account\"")),
    (
        "azure_storage_key",
        re.compile(
            r"DefaultEndpointsProtocol=https;AccountName=[^;]+;AccountKey=[A-Za-z0-9+/=]{88};EndpointSuffix=core\.windows\.net"
        ),
    ),
    ("openai_api_key", re.compile(r"sk-[A-Za-z0-9]{20,}")),
    ("stripe_live_key", re.compile(r"sk_live_[0-9a-zA-Z]{24,}")),
    ("stripe_test_key", re.compile(r"sk_test_[0-9a-zA-Z]{24,}")),
    ("private_key_block", re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----")),
    ("github_pat", re.compile(r"ghp_[A-Za-z0-9]{36}")),
    ("github_oauth", re.compile(r"gho_[A-Za-z0-9]{36}")),
    ("slack_token", re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}")),
    ("slack_webhook", re.compile(r"https://hooks\.slack\.com/services/T[A-Z0-9]{8}/B[A-Z0-9]{8}/[A-Za-z0-9]{24}")),
    ("jwt_token", re.compile(r"eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+")),
    ("twilio_api_key", re.compile(r"SK[0-9a-fA-F]{32}")),
    ("sendgrid_api_key", re.compile(r"SG\.[A-Za-z0-9_-]{22}\.[A-Za-z0-9_-]{43}")),
    ("facebook_access_token", re.compile(r"EAACEdEose0cBA[0-9A-Za-z]+")),
    ("twitter_bearer", re.compile(r"AAAAAAAAAAAAAAAAAAAAAA[A-Za-z0-9%]+")),
    ("heroku_api_key", re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")),
    ("mailgun_api_key", re.compile(r"key-[0-9a-zA-Z]{32}")),
    ("paypal_braintree", re.compile(r"access_token\$production\$[0-9a-z]{16}\$[0-9a-f]{32}")),
    ("square_access_token", re.compile(r"sq0atp-[0-9A-Za-z\-_]{22}")),
    ("square_oauth_secret", re.compile(r"sq0csp-[0-9A-Za-z\\-_]{43}")),
    ("lyft_client_id_or_secret", re.compile(r"[a-z]*(?:_client_id|_client_secret)[\"' :=]+[\"']([a-zA-Z0-9]{16,})[\"']")),
    ("google_captcha", re.compile(r"6L[0-9A-Za-z_-]{34}")),
    ("generic_secret_assign", re.compile(r"(?i)(?:secret|password|passwd|api[_-]?key|token|private[_-]?key)\s*[:=]\s*[\"'][^\"'\s]{8,}[\"']")),
]

_HIGH_ENTROPY_PATTERN = re.compile(r"[A-Za-z0-9/+=]{20,}")

_URL_BLACKLIST_PATTERN = re.compile(r"evil\.com|phishy\.xyz", re.IGNORECASE)

_EXTERNAL_GIT_REF_PATTERN = re.compile(r"https://(github|gitlab)\.com/([^/\s]+)/([^/\s]+)")


def _r_auth_l1_node_type(ctx: ReviewContext) -> bool:
    expected_role = _DEFAULT_NODE_TYPE_ROLE.get(ctx.node_type)
    if expected_role is None:
        return True
    submitter_roles: list[str]
    if isinstance(ctx.submitter_role, str):
        submitter_roles = [ctx.submitter_role]
    else:
        submitter_roles = list(ctx.submitter_role)
    return expected_role in submitter_roles


def _r_auth_l2_instance_id(ctx: ReviewContext) -> bool:
    node_def: NodeDef | None = None
    for n in ctx.pipeline_def.nodes:
        if n.node_id == ctx.node_id:
            node_def = n
            break
    if node_def is None:
        return False
    if not node_def.role_assignments:
        return True
    return ctx.role_instance_id in node_def.role_assignments


def _r_auth_l3_external_repo(ctx: ReviewContext) -> bool:
    for ref in ctx.external_refs:
        m = _EXTERNAL_GIT_REF_PATTERN.search(ref)
        if not m:
            continue
        owner = m.group(2)
        if ctx.external_repo_whitelist and owner not in ctx.external_repo_whitelist:
            return False
    return True


def _r_required_fields(ctx: ReviewContext) -> bool:
    if ctx.skill is not None and ctx.skill.required_fields:
        required = ctx.skill.required_fields
    else:
        required = _DEFAULT_REQUIRED_FIELDS
    keys = set(ctx.template.keys())
    return all(f in keys for f in required)


def _r_classification_clearance(ctx: ReviewContext) -> bool:
    return int(ctx.clearance) >= int(ctx.artifact_classification)


def _r_deps_done(ctx: ReviewContext) -> bool:
    deps = resolve_effective_deps(ctx.node_id, ctx.pipeline_def, ctx.pipeline_state)
    for up_id, decl in deps:
        up_state = ctx.pipeline_state.node_states.get(up_id)
        if up_state is None:
            return False
        up_status = (
            NodeStatus(up_state.status)
            if isinstance(up_state.status, str)
            else up_state.status
        )
        strictness = (
            DepStrictness(decl.strictness)
            if isinstance(decl.strictness, str)
            else decl.strictness
        )
        if strictness == DepStrictness.ACCEPTS_DRAFT:
            if up_status not in {NodeStatus.DONE, NodeStatus.DRAFT}:
                return False
        else:
            if up_status != NodeStatus.DONE:
                return False
    return True


def _r_file_format(ctx: ReviewContext) -> bool:
    allowed_exts: set[str] = _DEFAULT_REVIEW_GATE_EXTS
    if ctx.skill is not None and hasattr(ctx.skill.review_gates, "model_dump"):
        pass
    total_size = 0
    for path, content in ctx.content_bytes.items():
        if not content or len(content) == 0:
            return False
        ext = path.rsplit(".", 1)[-1].lower() if "." in path else ""
        if ext and ext not in allowed_exts:
            return False
        total_size += len(content)
        if total_size > _MAX_FILE_SIZE_BYTES:
            return False
    return True


def _jsonpath_get(obj: Any, path: str) -> list[Any]:
    parts = [p for p in path.replace("$.", "").split(".") if p]
    results: list[Any] = []

    def _walk(current: Any, idx: int) -> None:
        if idx >= len(parts):
            results.append(current)
            return
        part = parts[idx]
        if part == "*" or part == "[*]":
            if isinstance(current, list):
                for item in current:
                    _walk(item, idx + 1)
            elif isinstance(current, dict):
                for v in current.values():
                    _walk(v, idx + 1)
            return
        arr_match = re.match(r"(.+)\[(\d+)\]", part)
        if arr_match:
            key = arr_match.group(1)
            arr_idx = int(arr_match.group(2))
            if isinstance(current, dict) and key in current:
                inner = current[key]
                if isinstance(inner, list) and 0 <= arr_idx < len(inner):
                    _walk(inner[arr_idx], idx + 1)
            return
        if isinstance(current, dict) and part in current:
            _walk(current[part], idx + 1)

    _walk(obj, 0)
    return results


def _parse_content(content: bytes) -> Any:
    try:
        import json

        return json.loads(content.decode("utf-8"))
    except Exception:
        pass
    try:
        import yaml

        return yaml.safe_load(content.decode("utf-8"))
    except Exception:
        return None


def _r_completeness_contract(ctx: ReviewContext) -> bool:
    if ctx.skill is None or not hasattr(ctx.skill, "review_gates"):
        return True
    contract = getattr(ctx.skill, "completeness_contract", None)
    if contract is None:
        return True
    paths = getattr(contract, "json_paths", [])
    mode = getattr(contract, "mode", "and")
    if not paths:
        return True
    all_present: list[bool] = []
    for content in ctx.content_bytes.values():
        parsed = _parse_content(content)
        if parsed is None:
            continue
        for jp in paths:
            found = _jsonpath_get(parsed, jp)
            all_present.append(len(found) > 0 and all(v is not None for v in found))
    if not all_present:
        return False
    if mode == "and":
        return all(all_present)
    return any(all_present)


def _r_secret_scan(ctx: ReviewContext) -> bool:
    for path, content in ctx.content_bytes.items():
        try:
            text = content.decode("utf-8", errors="ignore")
        except Exception:
            text = str(content)
        for _name, pattern in _SECRET_PATTERNS:
            if pattern.search(text):
                return False
        for match in _HIGH_ENTROPY_PATTERN.findall(text):
            if len(match) >= 20 and _shannon_entropy(match) >= 4.5:
                b64_valid = True
                try:
                    base64.b64decode(match, validate=True)
                except Exception:
                    b64_valid = False
                if b64_valid and _shannon_entropy(match) >= 4.5:
                    return False
                if not b64_valid and _shannon_entropy(match) >= 4.5:
                    if re.search(r"[0-9]", match) and re.search(r"[a-z]", match) and re.search(r"[A-Z]", match):
                        return False
    return True


def _r_url_safety(ctx: ReviewContext) -> bool:
    for ref in ctx.external_refs:
        if _URL_BLACKLIST_PATTERN.search(ref):
            return False
    return True


_EXE_MAGIC = b"MZ"
_ELF_MAGIC = b"\x7fELF"
_SHEBANG_BASH = b"#!/bin/bash"
_SHEBANG_SH = b"#!/bin/sh"
_ZIP_MAGIC = b"PK\x03\x04"
_ZIP_CDIR_MAGIC = b"PK\x01\x02"


def _scan_zip_for_exe(data: bytes) -> bool:
    try:
        with zipfile.ZipFile(BytesIO(data), "r") as zf:
            for name in zf.namelist():
                lower = name.lower()
                if lower.endswith(".exe") or lower.endswith(".dll"):
                    return True
    except Exception:
        pos = data.find(_ZIP_CDIR_MAGIC)
        while pos != -1 and pos + 46 <= len(data):
            try:
                name_len = struct.unpack_from("<H", data, pos + 28)[0]
                extra_len = struct.unpack_from("<H", data, pos + 30)[0]
                comment_len = struct.unpack_from("<H", data, pos + 32)[0]
                name_start = pos + 46
                name = data[name_start : name_start + name_len].decode("utf-8", errors="ignore")
                lower = name.lower()
                if lower.endswith(".exe") or lower.endswith(".dll"):
                    return True
                pos = data.find(_ZIP_CDIR_MAGIC, pos + 46 + name_len + extra_len + comment_len)
            except Exception:
                break
    return False


def _r_malware_scan(ctx: ReviewContext) -> bool:
    for path, content in ctx.content_bytes.items():
        if not content:
            continue
        head = content[: min(len(content), 16)]
        if head.startswith(_EXE_MAGIC):
            return False
        if head.startswith(_ELF_MAGIC):
            return False
        if content.startswith(_SHEBANG_BASH) or content.startswith(_SHEBANG_SH):
            return False
        if content.startswith(_ZIP_MAGIC):
            if _scan_zip_for_exe(content):
                return False
    return True


def _r_external_ref_ownership(ctx: ReviewContext) -> bool:
    return True


def _r_commit_stability(ctx: ReviewContext) -> bool:
    volatile_declared = ctx.template.get("volatile_declared") or ctx.template.get(
        "is_volatile"
    )
    if volatile_declared:
        return True
    return False


def _r_addendum_vs_changed(ctx: ReviewContext) -> bool:
    if ctx.addendum_declared and ctx.diff_deleted_lines > 0:
        return False
    return True


_CHANGE_CLASS_DELETE_ENDPOINT_PATTERNS: list[re.Pattern] = [
    re.compile(r'-  "endpoints"'),
    re.compile(r"-  .*endpoints.*:"),
    re.compile(r"-\s*endpoints\s*:"),
]


def _r_change_class_consistency(ctx: ReviewContext) -> bool:
    if ctx.change_class_declared != "compatible":
        return True
    for pat in _CHANGE_CLASS_DELETE_ENDPOINT_PATTERNS:
        if pat.search(ctx.diff_unified):
            return False
    return True


def _r_impact_claim_completeness(ctx: ReviewContext) -> bool:
    mod_decl = ctx.template.get("modification_declaration", {})
    if isinstance(mod_decl, dict):
        impact_downstream = mod_decl.get("impact_claimed_downstream", []) or []
    else:
        impact_downstream = []
    if not impact_downstream:
        return True
    from orchestration.deps import compute_downstream

    direct_downstream = compute_downstream(ctx.node_id, ctx.pipeline_def)
    if not direct_downstream:
        return True
    claimed_set = set(impact_downstream)
    for ds in direct_downstream:
        if ds not in claimed_set:
            return False
    return True


def _r_human_review_required(ctx: ReviewContext) -> bool:
    if ctx.node_type == "api_contract":
        version = ctx.template.get("version", 0)
        try:
            if int(version) == 1:
                return False
        except Exception:
            pass
    if ctx.node_type == "design_asset":
        return False
    if ctx.node_type in {"client_delivery", "server_delivery"}:
        return False
    if int(ctx.artifact_classification) >= int(ClassificationLevel.CONFIDENTIAL):
        return False
    if ctx.change_class_declared == "breaking":
        return False
    return True


R_AUTH_L1_NODE_TYPE = Rule(
    rule_id="R_AUTH_L1_NODE_TYPE",
    priority=95,
    on_fail="reject",
    condition=_r_auth_l1_node_type,
    message_template="Submitter role {submitter_role} not allowed for node_type {node_type}",
)

R_AUTH_L2_INSTANCE_ID = Rule(
    rule_id="R_AUTH_L2_INSTANCE_ID",
    priority=94,
    on_fail="reject",
    condition=_r_auth_l2_instance_id,
    message_template="role_instance_id {role_instance_id} not in node role_assignments",
)

R_AUTH_L3_EXTERNAL_REPO = Rule(
    rule_id="R_AUTH_L3_EXTERNAL_REPO",
    priority=93,
    on_fail="reject",
    condition=_r_auth_l3_external_repo,
    message_template="External git ref owner not in whitelist",
)

R_REQUIRED_FIELDS = Rule(
    rule_id="R_REQUIRED_FIELDS",
    priority=90,
    on_fail="reject",
    condition=_r_required_fields,
    message_template="Template missing required fields",
)

R_CLASSIFICATION_CLEARANCE = Rule(
    rule_id="R_CLASSIFICATION_CLEARANCE",
    priority=88,
    on_fail="reject",
    condition=_r_classification_clearance,
    message_template="Clearance {clearance} below artifact classification {artifact_classification}",
)

R_DEPS_DONE = Rule(
    rule_id="R_DEPS_DONE",
    priority=85,
    on_fail="reject",
    condition=_r_deps_done,
    message_template="Upstream dependencies not all done",
)

R_FILE_FORMAT = Rule(
    rule_id="R_FILE_FORMAT",
    priority=82,
    on_fail="reject",
    condition=_r_file_format,
    message_template="File format/size/empty check failed",
)

R_COMPLETENESS_CONTRACT = Rule(
    rule_id="R_COMPLETENESS_CONTRACT",
    priority=80,
    on_fail="reject",
    condition=_r_completeness_contract,
    message_template="Completeness contract not satisfied",
)

R_SECRET_SCAN = Rule(
    rule_id="R_SECRET_SCAN",
    priority=99,
    on_fail="reject",
    condition=_r_secret_scan,
    message_template="Secret scan detected potential secrets",
)

R_URL_SAFETY = Rule(
    rule_id="R_URL_SAFETY",
    priority=97,
    on_fail="reject",
    condition=_r_url_safety,
    message_template="URL safety check hit blacklisted domain",
)

R_MALWARE_SCAN = Rule(
    rule_id="R_MALWARE_SCAN",
    priority=98,
    on_fail="reject",
    condition=_r_malware_scan,
    message_template="Malware scan detected executable or script payload",
)

R_EXTERNAL_REF_OWNERSHIP = Rule(
    rule_id="R_EXTERNAL_REF_OWNERSHIP",
    priority=83,
    on_fail="reject",
    condition=_r_external_ref_ownership,
    message_template="External reference ownership not verified",
)

R_COMMIT_STABILITY = Rule(
    rule_id="R_COMMIT_STABILITY",
    priority=81,
    on_fail="warn",
    condition=_r_commit_stability,
    message_template="Commit stability (volatile) flag not declared",
)

R_ADDENDUM_VS_CHANGED = Rule(
    rule_id="R_ADDENDUM_VS_CHANGED",
    priority=87,
    on_fail="reject",
    condition=_r_addendum_vs_changed,
    message_template="E_ADDENDUM_DELETES_ROWS: addendum declares no deletes but diff deleted {diff_deleted_lines} lines",
)

R_CHANGE_CLASS_CONSISTENCY = Rule(
    rule_id="R_CHANGE_CLASS_CONSISTENCY",
    priority=85,
    on_fail="reject",
    condition=_r_change_class_consistency,
    message_template="E_CHANGE_CLASS_MISMATCH: declared compatible but diff removes endpoints",
)

R_IMPACT_CLAIM_COMPLETENESS = Rule(
    rule_id="R_IMPACT_CLAIM_COMPLETENESS",
    priority=70,
    on_fail="reject",
    condition=_r_impact_claim_completeness,
    message_template="E_UNDERCLAIM_IMPACT: impact_claimed_downstream missing direct downstream IDs",
)

R_HUMAN_REVIEW_REQUIRED = Rule(
    rule_id="R_HUMAN_REVIEW_REQUIRED",
    priority=60,
    on_fail="needs_human",
    condition=_r_human_review_required,
    message_template="Human review required for this artifact type/classification",
)


class RuleEngine:
    def __init__(self, rules: list[Rule] | None = None):
        self.rules: list[Rule] = sorted(
            rules or self.default_rules(), key=lambda r: -r.priority
        )

    @classmethod
    def default_rules(cls) -> list[Rule]:
        return [
            R_AUTH_L1_NODE_TYPE,
            R_AUTH_L2_INSTANCE_ID,
            R_AUTH_L3_EXTERNAL_REPO,
            R_REQUIRED_FIELDS,
            R_CLASSIFICATION_CLEARANCE,
            R_DEPS_DONE,
            R_FILE_FORMAT,
            R_COMPLETENESS_CONTRACT,
            R_SECRET_SCAN,
            R_URL_SAFETY,
            R_MALWARE_SCAN,
            R_EXTERNAL_REF_OWNERSHIP,
            R_COMMIT_STABILITY,
            R_ADDENDUM_VS_CHANGED,
            R_CHANGE_CLASS_CONSISTENCY,
            R_IMPACT_CLAIM_COMPLETENESS,
            R_HUMAN_REVIEW_REQUIRED,
        ]

    def _format_message(self, template: str, ctx: ReviewContext) -> str:
        try:
            return template.format(
                submitter_role=ctx.submitter_role,
                node_type=ctx.node_type,
                role_instance_id=ctx.role_instance_id,
                clearance=int(ctx.clearance),
                artifact_classification=int(ctx.artifact_classification),
                diff_deleted_lines=ctx.diff_deleted_lines,
            )
        except Exception:
            return template

    def evaluate(self, ctx: ReviewContext) -> dict:
        checks: list[dict] = []
        warnings: list[str] = []
        verdict: Literal["pass", "reject", "needs_human"] = "pass"
        rejected_by: str | None = None
        needs_human_flag = False

        for rule in self.rules:
            cond = rule.condition
            if callable(cond):
                try:
                    passed = bool(cond(ctx))
                except Exception:
                    passed = False
            else:
                passed = False
            message = self._format_message(rule.message_template, ctx)
            checks.append(
                {
                    "rule_id": rule.rule_id,
                    "on_fail": rule.on_fail,
                    "pass": passed,
                    "message": "" if passed else message,
                }
            )
            if passed:
                continue
            if rule.on_fail == "reject":
                verdict = "reject"
                if rejected_by is None:
                    rejected_by = rule.rule_id
            elif rule.on_fail == "needs_human":
                needs_human_flag = True
                if verdict == "pass":
                    verdict = "needs_human"
            elif rule.on_fail == "warn":
                warnings.append(message)

        summary_parts = []
        if verdict == "pass":
            summary_parts.append(f"All {len(self.rules)} rules passed")
        elif verdict == "reject":
            summary_parts.append(f"Rejected by {rejected_by}")
        elif verdict == "needs_human":
            summary_parts.append("Needs human review")
        if warnings:
            summary_parts.append(f"{len(warnings)} warning(s)")
        summary = "; ".join(summary_parts)

        return {
            "verdict": verdict,
            "checks": checks,
            "summary": summary,
            "needs_human": needs_human_flag,
            "rejected_by": rejected_by,
            "warnings": warnings,
        }
