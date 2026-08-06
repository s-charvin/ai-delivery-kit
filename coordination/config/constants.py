from __future__ import annotations

from orchestration.models import (
    ClassificationLevel,
    NodeStatus,
    ParticipationProfile,
)

ERROR_CODES: dict[str, dict] = {
    "E_PROTECTED_BRANCH": {
        "code": 1001,
        "zh": "受保护分支不允许直接推送",
        "en": "Direct push to protected branch is not allowed",
    },
    "E_PR_TEMPLATE_MISSING_FIELD": {
        "code": 1002,
        "zh": "PR 模板缺少必填字段",
        "en": "PR template is missing required fields",
    },
    "E_REPO_UNREACHABLE": {
        "code": 1003,
        "zh": "代码仓库不可达",
        "en": "Repository is unreachable",
    },
    "E_LFS_PUSH_FAILED": {
        "code": 1004,
        "zh": "LFS 文件推送失败",
        "en": "LFS file push failed",
    },
    "E_BRANCH_NAMING_INVALID": {
        "code": 1005,
        "zh": "分支命名不符合规范",
        "en": "Branch naming does not conform to specification",
    },
    "E_MERGE_CONFLICT": {
        "code": 1006,
        "zh": "合并冲突",
        "en": "Merge conflict detected",
    },
    "E_MANIFEST_INCONSISTENT": {
        "code": 1007,
        "zh": "清单数据不一致",
        "en": "Manifest data inconsistency",
    },
    "E_PERMISSION_DENIED": {
        "code": 2001,
        "zh": "权限不足",
        "en": "Permission denied",
    },
    "E_TOKEN_EXPIRED": {
        "code": 2002,
        "zh": "Token 已过期",
        "en": "Token has expired",
    },
    "E_TOKEN_SCOPE_MISMATCH": {
        "code": 2003,
        "zh": "Token 权限范围不匹配",
        "en": "Token scope mismatch",
    },
    "E_CLEARANCE_MISMATCH": {
        "code": 2004,
        "zh": "安全密级不匹配",
        "en": "Clearance level mismatch",
    },
    "E_BOT_ONLY_ACTION": {
        "code": 2005,
        "zh": "此操作仅允许 Bot 执行",
        "en": "This action is bot-only",
    },
    "E_HUMAN_REVIEW_REQUIRED": {
        "code": 2006,
        "zh": "需要人工审核",
        "en": "Human review required",
    },
    "E_DEPS_NOT_SATISFIED": {
        "code": 3001,
        "zh": "依赖未满足",
        "en": "Dependencies not satisfied",
    },
    "E_ILLEGAL_TRANSITION": {
        "code": 3002,
        "zh": "非法状态转移",
        "en": "Illegal state transition",
    },
    "E_NODE_PENDING_PR_EXISTS": {
        "code": 3003,
        "zh": "节点存在待处理的 PR",
        "en": "Node has pending PRs",
    },
    "E_NOT_OPTIONAL": {
        "code": 3004,
        "zh": "节点非可选，不可跳过",
        "en": "Node is not optional and cannot be skipped",
    },
    "E_NODE_NOT_DONE": {
        "code": 3005,
        "zh": "节点未完成",
        "en": "Node is not done",
    },
    "E_NODE_LOCKED": {
        "code": 3006,
        "zh": "节点已被锁定",
        "en": "Node is locked",
    },
    "E_PIPELINE_CANCELLED": {
        "code": 4001,
        "zh": "管线已取消",
        "en": "Pipeline has been cancelled",
    },
    "E_PIPELINE_PAUSED": {
        "code": 4002,
        "zh": "管线已暂停",
        "en": "Pipeline has been paused",
    },
    "E_PIPELINE_MERGED": {
        "code": 4003,
        "zh": "管线已合并",
        "en": "Pipeline has been merged",
    },
    "E_PIPELINE_NOT_ACTIVE": {
        "code": 4004,
        "zh": "管线非活跃状态",
        "en": "Pipeline is not active",
    },
    "E_ADDENDUM_DELETES_ROWS": {
        "code": 5001,
        "zh": "Addendum 不允许删除行",
        "en": "Addendum must not delete rows",
    },
    "E_ADDENDUM_AUTH": {
        "code": 5002,
        "zh": "Addendum 授权校验失败",
        "en": "Addendum authorization check failed",
    },
    "E_INCOMPATIBLE_NOT_DOWNSTREAM": {
        "code": 5003,
        "zh": "声明不兼容的节点非下游节点",
        "en": "Claimed incompatible node is not a downstream node",
    },
    "E_UNDERCLAIM_IMPACT": {
        "code": 5004,
        "zh": "影响范围声明不足",
        "en": "Impact claim is under-declared",
    },
    "E_CHANGE_CLASS_MISMATCH": {
        "code": 5005,
        "zh": "变更类别不匹配",
        "en": "Change class mismatch",
    },
    "E_REQUIRED_FIELDS_MISSING": {
        "code": 6001,
        "zh": "缺少必填字段",
        "en": "Required fields missing",
    },
    "R_REQUIRED_FIELDS": {
        "code": 6011,
        "zh": "必填字段审查",
        "en": "Required fields review gate",
    },
    "R_SECRET_SCAN": {
        "code": 6002,
        "zh": "密钥扫描不通过",
        "en": "Secret scan failed",
    },
    "R_EXTERNAL_REF_OWNERSHIP": {
        "code": 6003,
        "zh": "外部引用归属校验失败",
        "en": "External reference ownership check failed",
    },
    "R_CHANGE_CLASS_CONSISTENCY": {
        "code": 6004,
        "zh": "变更类别一致性校验失败",
        "en": "Change class consistency check failed",
    },
    "R_LINT_FAIL": {
        "code": 6005,
        "zh": "Lint 检查不通过",
        "en": "Lint check failed",
    },
    "R_TEST_FAIL": {
        "code": 6006,
        "zh": "测试不通过",
        "en": "Test check failed",
    },
    "R_COVERAGE_BELOW_POLICY": {
        "code": 6007,
        "zh": "覆盖率低于策略要求",
        "en": "Coverage below policy threshold",
    },
    "R_SECURITY_SCAN_HIT": {
        "code": 6008,
        "zh": "安全扫描命中问题",
        "en": "Security scan hit issues",
    },
    "E_FORMAT_SCHEMA_INVALID": {
        "code": 6009,
        "zh": "格式 Schema 校验失败",
        "en": "Format schema validation failed",
    },
    "E_EXTERNAL_HEALTH_DEGRADED": {
        "code": 7001,
        "zh": "外部服务健康度下降",
        "en": "External service health degraded",
    },
    "E_CROSS_PIPELINE_REF_BROKEN": {
        "code": 7002,
        "zh": "跨管线引用断裂",
        "en": "Cross-pipeline reference broken",
    },
}


def _init_transition_matrix() -> dict[str, dict[str, bool]]:
    statuses = [s.value for s in NodeStatus]
    matrix: dict[str, dict[str, bool]] = {}
    for s1 in statuses:
        matrix[s1] = {}
        for s2 in statuses:
            matrix[s1][s2] = False
    return matrix


TRANSITION_MATRIX: dict[str, dict[str, bool]] = _init_transition_matrix()

VALID_TRANSITIONS: dict[tuple[NodeStatus, NodeStatus], str] = {}


def _set_valid(from_: NodeStatus, to: NodeStatus, tag: str) -> None:
    TRANSITION_MATRIX[from_.value][to.value] = True
    VALID_TRANSITIONS[(from_, to)] = tag


_set_valid(NodeStatus.BLOCKED, NodeStatus.READY, "T1")
_set_valid(NodeStatus.READY, NodeStatus.PENDING_REVIEW, "T2")
_set_valid(NodeStatus.PENDING_REVIEW, NodeStatus.IN_PROGRESS, "T3")
_set_valid(NodeStatus.PENDING_REVIEW, NodeStatus.REVIEW, "T4")
_set_valid(NodeStatus.REVIEW, NodeStatus.DONE, "T5")
_set_valid(NodeStatus.REVIEW, NodeStatus.READY, "T6")
_set_valid(NodeStatus.DONE, NodeStatus.CHANGED, "T7")
_set_valid(NodeStatus.CHANGED, NodeStatus.IN_PROGRESS, "T8")
_set_valid(NodeStatus.IN_PROGRESS, NodeStatus.PENDING_REVIEW, "T9")
_set_valid(NodeStatus.READY, NodeStatus.DRAFT, "T10")
_set_valid(NodeStatus.DRAFT, NodeStatus.PENDING_REVIEW, "T11")
_set_valid(NodeStatus.READY, NodeStatus.SKIPPED, "T12")
_set_valid(NodeStatus.DONE, NodeStatus.DEPRECATED, "D1")
_set_valid(NodeStatus.CHANGED, NodeStatus.DEPRECATED, "D2")
_set_valid(NodeStatus.READY, NodeStatus.DEPRECATED, "D3")
_set_valid(NodeStatus.BLOCKED, NodeStatus.DEPRECATED, "D4")
_set_valid(NodeStatus.DEPRECATED, NodeStatus.SUNSET, "D5")
_set_valid(NodeStatus.DRAFT, NodeStatus.DEPRECATED, "D6")

S1_NOTE = "S1: sunset is a terminal state; no outgoing transitions allowed"
S2_NOTE = "S2: in_progress -> blocked is an illegal transition"

ClassificationLevelAlias = ClassificationLevel
PUBLIC = ClassificationLevel.PUBLIC
INTERNAL = ClassificationLevel.INTERNAL
CONFIDENTIAL = ClassificationLevel.CONFIDENTIAL
RESTRICTED = ClassificationLevel.RESTRICTED

PARTICIPATION_PROFILES: dict[str, ParticipationProfile] = {
    "fullstack": ParticipationProfile(
        id="fullstack",
        name="fullstack",
        roles_present=[
            "product",
            "design",
            "client_ui",
            "server_impl",
            "server_test",
            "client_test",
            "ops",
        ],
        roles_absent=[],
        core_node_types=[
            "product_spec",
            "api_contract",
            "design_asset",
            "client_ui_impl",
            "server_impl",
            "server_test",
            "client_test",
            "delivery_gate",
        ],
    ),
    "server_only": ParticipationProfile(
        id="server_only",
        name="server_only",
        roles_present=["product", "server_impl", "server_test", "ops"],
        roles_absent=["design", "client_ui", "client_test"],
        core_node_types=[
            "product_spec",
            "api_contract",
            "server_impl",
            "server_test",
            "delivery_gate",
        ],
    ),
    "no_design_client": ParticipationProfile(
        id="no_design_client",
        name="no_design_client",
        roles_present=[
            "product",
            "client_ui",
            "server_impl",
            "server_test",
            "client_test",
            "ops",
        ],
        roles_absent=["design"],
        core_node_types=[
            "product_spec",
            "api_contract",
            "client_ui_impl",
            "server_impl",
            "server_test",
            "client_test",
            "delivery_gate",
        ],
    ),
    "design_only": ParticipationProfile(
        id="design_only",
        name="design_only",
        roles_present=["design"],
        roles_absent=[
            "product",
            "client_ui",
            "server_impl",
            "server_test",
            "client_test",
            "ops",
        ],
        allow_design_as_root=True,
        core_node_types=["design_asset"],
        allow_non_product_root=True,
    ),
    "tech_debt": ParticipationProfile(
        id="tech_debt",
        name="tech_debt",
        roles_present=["server_impl", "ops"],
        roles_absent=["product", "design", "client_ui", "server_test", "client_test"],
        allow_non_product_root=True,
        core_node_types=["server_impl", "delivery_gate"],
        tech_debt_hotfix_mode=True,
    ),
    "custom": ParticipationProfile(
        id="custom",
        name="custom",
        roles_present=[],
        roles_absent=[],
        core_node_types=[],
    ),
}
