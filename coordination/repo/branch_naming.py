from __future__ import annotations

import re
import unicodedata

BRANCH_NAME_REGEX = (
    r"^feat/[a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+/[a-zA-Z0-9_.-]+-[0-9]{3,}$"
)


def _slugify(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    ascii_str = normalized.encode("ascii", "ignore").decode("ascii")
    lower = ascii_str.lower()
    slug = re.sub(r"[^a-z0-9]", "_", lower)
    slug = re.sub(r"_+", "_", slug)
    slug = slug.strip("_")
    return slug or "x"


def validate_branch_name(name: str) -> bool:
    return re.fullmatch(BRANCH_NAME_REGEX, name) is not None


def format_branch_name(
    pipeline_id: str, instance_id: str, node_type: str, seq: int
) -> str:
    ppl_slug = _slugify(pipeline_id)
    inst_slug = _slugify(instance_id)
    node_slug = _slugify(node_type)
    seq_str = f"{seq:03d}"
    branch = f"feat/{ppl_slug}/{inst_slug}/{node_slug}-{seq_str}"
    if not validate_branch_name(branch):
        raise ValueError(f"Generated branch name failed validation: {branch}")
    return branch


def allocate_seq(used_seqs: set[int]) -> int:
    seq = 1
    while seq in used_seqs:
        seq += 1
    return seq
