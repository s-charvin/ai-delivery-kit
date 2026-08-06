from __future__ import annotations

import fnmatch
import json
import re
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from skills.models import (
    CompletenessContract,
    FormatSpec,
    ModificationRules,
    OutputGuides,
    ReviewGates,
    SkillDefinition,
)

LANGFUSE_WAL_DIR = Path("data/wal/langfuse")
LANGFUSE_WAL_DIR.mkdir(parents=True, exist_ok=True)


def _write_wal_span(span_type: str, name: str, inputs: dict, outputs: Any = None, error: str | None = None) -> None:
    LANGFUSE_WAL_DIR.mkdir(parents=True, exist_ok=True)
    ts = int(time.time() * 1000)
    uid = uuid.uuid4().hex[:8]
    fname = f"{ts}-{uid}.jsonl"
    fpath = LANGFUSE_WAL_DIR / fname
    start_iso = datetime.now(timezone.utc).isoformat()
    span = {
        "trace_id": uuid.uuid4().hex,
        "span_id": uuid.uuid4().hex,
        "name": name,
        "span_type": span_type,
        "start_time": start_iso,
        "end_time": start_iso,
        "status": "error" if error else "ok",
        "inputs": inputs,
        "outputs": outputs,
        "error": error,
        "metadata": {},
    }
    line = json.dumps(span, ensure_ascii=False)
    with open(fpath, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def _wildcard_to_regex(pattern: str) -> re.Pattern:
    p = pattern.replace("*", "___WILDCARD___")
    p = re.escape(p)
    p = p.replace("___WILDCARD___", r".*")
    p = p.replace(r"\.", r"[._]")
    return re.compile(r"^" + p + r"$")


def _node_type_matches(pattern: str, node_type: str) -> bool:
    if pattern == "*":
        return True
    if pattern == node_type:
        return True
    if "*" in pattern:
        regex = _wildcard_to_regex(pattern)
        if regex.match(node_type):
            return True
        alt_pattern = pattern.replace(".", "_").replace("*", "___")
        parts = node_type.split("_")
        for i in range(1, len(parts) + 1):
            prefix = "_".join(parts[:i])
            if prefix and "*" in pattern:
                pattern_prefix = pattern.split(".")[0] if "." in pattern else pattern.split("*")[0]
                if prefix.startswith(pattern_prefix) or pattern_prefix.startswith(prefix):
                    prefix_regex = _wildcard_to_regex(pattern)
                    if prefix_regex.match(prefix + "_" if not prefix.endswith("_") else prefix + "x"):
                        return True
        normal_alt = pattern.replace(".", "_")
        if normal_alt == node_type:
            return True
    return False


class SkillRegistry:
    def __init__(self, skill_root: Path):
        self.root = Path(skill_root)
        self._cache: dict[str, SkillDefinition] = {}
        self._wildcard_patterns: list[tuple[str, re.Pattern]] = []
        self._mtime: float = 0.0
        self.reload()

    def _collect_skill_yamls(self) -> list[Path]:
        if not self.root.exists():
            return []
        result: list[Path] = []
        for child in sorted(self.root.iterdir()):
            if child.is_dir():
                skill_yaml = child / "skill.yaml"
                if skill_yaml.exists() and skill_yaml.is_file():
                    result.append(skill_yaml)
        return result

    def _latest_skill_mtime(self) -> float:
        yamls = self._collect_skill_yamls()
        if not yamls:
            return 0.0
        return max(p.stat().st_mtime for p in yamls)

    @staticmethod
    def _parse_skill_yaml(yaml_path: Path) -> SkillDefinition:
        with open(yaml_path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}

        if "format" in raw and isinstance(raw["format"], str):
            raw["format"] = {"spec": raw["format"]}

        if "completeness_contract" in raw and raw["completeness_contract"] is not None:
            cc = raw["completeness_contract"]
            if isinstance(cc, dict):
                raw["completeness_contract"] = CompletenessContract(**cc)
            else:
                raw["completeness_contract"] = None

        if "deps" in raw and isinstance(raw["deps"], list):
            parsed_deps = []
            for dep in raw["deps"]:
                if isinstance(dep, str):
                    from orchestration.models import DepDeclaration, DepPresence
                    parsed_deps.append(DepDeclaration(upstream=dep, presence=DepPresence.REQUIRED))
                elif isinstance(dep, dict):
                    from orchestration.models import DepDeclaration
                    parsed_deps.append(DepDeclaration(**dep))
            raw["deps"] = parsed_deps

        return SkillDefinition.model_validate(raw)

    def reload(self) -> int:
        self._cache = {}
        self._wildcard_patterns = []

        yamls = self._collect_skill_yamls()
        for ypath in yamls:
            try:
                skill = self._parse_skill_yaml(ypath)
                self._cache[skill.id] = skill
                for nt in skill.for_node_types:
                    if "*" in nt:
                        self._wildcard_patterns.append((skill.id, _wildcard_to_regex(nt)))
            except Exception:
                continue

        self._mtime = self._latest_skill_mtime()
        return len(self._cache)

    def auto_reload(self) -> bool:
        latest = self._latest_skill_mtime()
        if latest > self._mtime:
            self.reload()
            return True
        return False

    def _match_level1(self, node_type: str) -> SkillDefinition | None:
        exact_candidates: list[SkillDefinition] = []
        for skill in self._cache.values():
            for nt in skill.for_node_types:
                if nt == node_type:
                    exact_candidates.append(skill)
                    break
        if not exact_candidates:
            return None
        exact_candidates.sort(key=lambda s: int(getattr(s, "priority", 0) if hasattr(s, "priority") else 0))
        return exact_candidates[0]

    def _match_level2(self, node_type: str, role_wildcard: str | None = None) -> SkillDefinition | None:
        candidates: list[tuple[int, SkillDefinition]] = []

        patterns_to_try: list[str] = []
        if role_wildcard:
            patterns_to_try.append(role_wildcard)
        parts = node_type.split("_")
        for i in range(1, len(parts) + 1):
            patterns_to_try.append("_".join(parts[:i]) + ".*")

        for skill_id, regex in self._wildcard_patterns:
            skill = self._cache.get(skill_id)
            if skill is None:
                continue
            if regex.match(node_type):
                candidates.append((0, skill))
                continue
            for pat in patterns_to_try:
                if fnmatch.fnmatch(pat, "*") and _wildcard_to_regex(pat).match(node_type):
                    for nt in skill.for_node_types:
                        if "*" in nt and _wildcard_to_regex(nt).match(pat.replace(".*", "_x")):
                            candidates.append((1, skill))
                            break

        for skill in self._cache.values():
            for nt in skill.for_node_types:
                if "*" in nt and _node_type_matches(nt, node_type):
                    found = any(id(skill) == id(c[1]) for c in candidates)
                    if not found:
                        candidates.append((2, skill))
                    break

        if not candidates:
            return None
        candidates.sort(key=lambda t: (t[0],))
        return candidates[0][1]

    def _match_level3(self, node_type: str) -> SkillDefinition:
        if "generic-skill" in self._cache:
            return self._cache["generic-skill"]

        _write_wal_span(
            span_type="ALR-SKILL-MISS",
            name="skill_match_fallback",
            inputs={"node_type": node_type},
            outputs={"fallback": "empty generic"},
            error=f"No skill matched node_type={node_type}, no generic-skill registered",
        )

        return SkillDefinition(
            id="generic-skill",
            name="Generic Fallback Skill",
            version="0.0.0",
            description="Auto-constructed empty fallback generic skill",
            for_node_types=["*"],
            required_fields=["node_id", "version", "classification"],
            format=FormatSpec(spec="Any"),
            modification_rules=ModificationRules(),
            output_guides=OutputGuides(),
            review_gates=ReviewGates(),
            metadata={"_fallback": True},
        )

    def match(self, node_type: str, role_wildcard: str | None = None) -> SkillDefinition:
        l1 = self._match_level1(node_type)
        if l1 is not None:
            return l1

        l2 = self._match_level2(node_type, role_wildcard)
        if l2 is not None:
            return l2

        if "generic-skill" not in self._cache:
            _write_wal_span(
                span_type="ALR-SKILL-MISS",
                name="skill_match_fallback_generic",
                inputs={"node_type": node_type, "role_wildcard": role_wildcard},
                outputs={"fallback": "generic-skill"},
                error=f"L1/L2 miss for node_type={node_type}",
            )

        return self._match_level3(node_type)

    def all_skills(self) -> list[SkillDefinition]:
        return list(self._cache.values())

    def get(self, skill_id: str) -> SkillDefinition | None:
        return self._cache.get(skill_id)
