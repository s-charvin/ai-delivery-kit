#!/usr/bin/env python3
"""Shared validation helpers for solution-design state-flow contracts."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime
from pathlib import Path
from typing import Any

DESIGN_REVIEW_MODES = frozenset({"none", "self", "human"})
TRANSITION_ID_RE = re.compile(r"\bT-[0-9]{3,}\b")
MERMAID_BLOCK_RE = re.compile(r"```mermaid\s*\n(.*?)```", re.IGNORECASE | re.DOTALL)

STATE_FLOW_START = "<!-- ai-delivery:state-flow:start -->"
STATE_FLOW_END = "<!-- ai-delivery:state-flow:end -->"
STATE_FLOW_SECTION_MARKERS = (
    "<!-- ai-delivery:state-flow:taxonomy -->",
    "<!-- ai-delivery:state-flow:mvi-loop -->",
    "<!-- ai-delivery:state-flow:lifecycle -->",
    "<!-- ai-delivery:state-flow:projection -->",
    "<!-- ai-delivery:state-flow:matrix -->",
    "<!-- ai-delivery:state-flow:sequences -->",
    "<!-- ai-delivery:state-flow:invariants -->",
    "<!-- ai-delivery:state-flow:traceability -->",
)
STATE_FLOW_POLICY_MARKERS = (
    "<!-- ai-delivery:state-flow:stale-result -->",
    "<!-- ai-delivery:state-flow:concurrency -->",
)


def sha256_file(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def _iso_timestamp(value: object) -> bool:
    if not isinstance(value, str) or not value:
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None


def _state_flow_body(text: str) -> str:
    start = text.find(STATE_FLOW_START)
    end = text.find(STATE_FLOW_END)
    if start < 0 or end < 0 or end <= start:
        return ""
    return text[start + len(STATE_FLOW_START):end]


def _transition_ids_in_matrix(body: str) -> list[str]:
    marker = "<!-- ai-delivery:state-flow:matrix -->"
    start = body.find(marker)
    if start < 0:
        return []
    section = body[start + len(marker):]
    ids: list[str] = []
    seen_matrix_row = False
    for line in section.splitlines():
        if line.lstrip().startswith("<!-- ai-delivery:state-flow:"):
            break
        if seen_matrix_row and re.search(r"^\|\s*Transition ID\s*\|", line, re.IGNORECASE):
            break
        row_ids = TRANSITION_ID_RE.findall(line)
        ids.extend(row_ids)
        if row_ids:
            seen_matrix_row = True
    return ids


def validate_design_document(
    path: Path,
    *,
    state_flow_required: bool,
) -> list[str]:
    """Validate the machine-checkable parts of a localized design.md."""
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return [f"cannot read design.md: {exc}"]

    has_start = STATE_FLOW_START in text
    has_end = STATE_FLOW_END in text
    if not state_flow_required and not has_start and not has_end:
        return []

    errors: list[str] = []
    if has_start != has_end:
        errors.append("state-flow contract must have matching start/end markers")
        return errors

    body = _state_flow_body(text)
    for marker in STATE_FLOW_SECTION_MARKERS:
        if marker not in body:
            errors.append(f"state-flow contract missing section marker: {marker}")
    for marker in STATE_FLOW_POLICY_MARKERS:
        if marker not in body:
            errors.append(f"state-flow contract missing policy marker: {marker}")

    mermaid_blocks = MERMAID_BLOCK_RE.findall(body)
    if not any(re.search(r"^\s*flowchart\b", block, re.MULTILINE | re.IGNORECASE) for block in mermaid_blocks):
        errors.append("state-flow contract requires a Mermaid flowchart MVI loop")
    if not any(re.search(r"^\s*stateDiagram-v2\b", block, re.MULTILINE | re.IGNORECASE) for block in mermaid_blocks):
        errors.append("state-flow contract requires a Mermaid stateDiagram-v2 lifecycle")

    matrix_ids = _transition_ids_in_matrix(body)
    if not matrix_ids:
        errors.append("state-flow transition matrix must contain at least one T-### row")
    duplicates = sorted({item for item in matrix_ids if matrix_ids.count(item) > 1})
    if duplicates:
        errors.append("state-flow transition matrix has duplicate IDs: " + ", ".join(duplicates))

    diagram_ids: list[str] = []
    for block in mermaid_blocks:
        diagram_ids.extend(TRANSITION_ID_RE.findall(block))
    missing = sorted(set(diagram_ids) - set(matrix_ids))
    if missing:
        errors.append("state-flow diagrams reference unknown transition IDs: " + ", ".join(missing))

    sequences = body[body.find("<!-- ai-delivery:state-flow:sequences -->"):] if "<!-- ai-delivery:state-flow:sequences -->" in body else ""
    has_sequence = any(re.search(r"^\s*sequenceDiagram\b", block, re.MULTILINE | re.IGNORECASE) for block in mermaid_blocks)
    if not has_sequence and "not_applicable" not in sequences:
        errors.append("state-flow sequences must include a sequenceDiagram or explicit not_applicable rationale")
    if "UiEffect" not in body:
        errors.append("state-flow contract must distinguish one-shot UI effects")

    return errors


def validate_design_review(
    entry: dict[str, Any],
    subreq_dir: Path,
    *,
    status: str,
    legacy_allowed: bool,
) -> list[str]:
    """Validate approval metadata and bind it to the exact design bytes."""
    mode = entry.get("design_mode")
    if mode == "none":
        review = entry.get("design_review")
        if review is None and legacy_allowed:
            return []
        if not isinstance(review, dict):
            return ["design_review object is required"]
        errors: list[str] = []
        if review.get("review_mode") != "none":
            errors.append("design_mode=none requires design_review.review_mode=none")
        for key in ("reviewed_design_sha256", "reviewed_at", "reviewed_by"):
            if review.get(key) is not None:
                errors.append(f"design_mode=none requires design_review.{key}=null")
        return errors
    review = entry.get("design_review")
    if not isinstance(review, dict):
        if legacy_allowed:
            return []
        return ["design_review object is required"]

    review_mode = review.get("review_mode")
    if review_mode not in DESIGN_REVIEW_MODES:
        return ["design_review.review_mode must be one of: none, self, human"]
    approved = entry.get("design_approved") is True
    design_path = subreq_dir / "design.md"
    actual_hash = sha256_file(design_path) if design_path.is_file() else None
    recorded_hash = review.get("reviewed_design_sha256")
    errors: list[str] = []

    if not approved:
        if review_mode != "none":
            errors.append("unapproved design must use design_review.review_mode=none")
        if recorded_hash is not None:
            errors.append("unapproved design must not retain reviewed_design_sha256")
        return errors

    if not design_path.is_file():
        return ["design_approved=true requires design.md"]
    expected_review_mode = "self" if mode == "light" else "human"
    if review_mode != expected_review_mode:
        errors.append(f"design_mode={mode} requires design_review.review_mode={expected_review_mode}")
    if not isinstance(recorded_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", recorded_hash):
        errors.append("design_review.reviewed_design_sha256 must be a lowercase SHA-256")
    elif actual_hash != recorded_hash:
        errors.append("design_review hash does not match current design.md")
    if not _iso_timestamp(review.get("reviewed_at")):
        errors.append("design_review.reviewed_at must be an ISO-8601 timestamp with timezone")
    if not isinstance(review.get("reviewed_by"), str) or not review.get("reviewed_by", "").strip():
        errors.append("design_review.reviewed_by must be a non-empty string")
    return errors


def validate_design_entry(
    entry: dict[str, Any],
    subreq_dir: Path,
    *,
    status: str,
    legacy_allowed: bool,
) -> list[str]:
    errors = validate_design_review(entry, subreq_dir, status=status, legacy_allowed=legacy_allowed)
    design_path = subreq_dir / "design.md"
    if entry.get("state_flow_required") is True:
        if entry.get("design_mode") != "full":
            errors.append("state_flow_required=true requires design_mode=full")
        if design_path.is_file():
            errors.extend(
                f"state-flow: {message}"
                for message in validate_design_document(design_path, state_flow_required=True)
            )
    return errors
