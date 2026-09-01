#!/usr/bin/env bash
set -euo pipefail

# Contract tests for optional, trigger-based change-scenario guidance. These
# assertions intentionally avoid pipeline stage names and keep catalog-wide
# requirements separate from scenario-specific requirements.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
EN_SCENARIO="$ROOT/.agents/skills/ai-delivery-orchestrator/references/scenario-guidance.md"
ZH_SCENARIO="$ROOT/.agents-zh/skills/ai-delivery-orchestrator/references/scenario-guidance.md"
EN_ORCH="$ROOT/.agents/skills/ai-delivery-orchestrator/SKILL.md"
ZH_ORCH="$ROOT/.agents-zh/skills/ai-delivery-orchestrator/SKILL-zh.md"

fail() { echo "FAIL: $*" >&2; exit 1; }

require() {
  local file="$1" needle="$2" label="$3"
  [[ -f "$file" ]] || fail "Missing file: $file"
  grep -F -q -- "$needle" "$file" || fail "$label missing in $(basename "$file"): $needle"
}

for marker in \
  "# Scenario Guidance" \
  "existing-function-semantic-replacement" \
  "preserve" \
  "extend" \
  "compatible_replacement" \
  "breaking_replacement" \
  "unknown" \
  "legacy inventory" \
  "baseline evidence" \
  "generated references" \
  "reuse matrix" \
  "old-to-new behavior diff" \
  "positive and negative acceptance" \
  "retire" \
  "Do not infer compatibility from code location or naming" \
  "Structural reuse is not semantic reuse" \
  "entry points" \
  "persistence" \
  "protocol adapters" \
  "established integration topology" \
  "parallel integration architecture" \
  "side effects" \
  "fresh-context review" \
  "preserve behavior solely for compile compatibility" \
  "mixed" \
  "relationship" \
  "action" \
  "retirement boundary" \
  "primary scenario" \
  "orthogonal" \
  "kebab-case ID" \
  "non-goals" \
  "stable, unique scenario ID" \
  "handoff or dependency" \
  "authorized boundary" \
  "analysis lens" \
  "optional" \
  "workflow steps" \
  "repository-wide" \
  "Recommended decision record" \
  "host workflow" \
  "current action report" \
  "require downstream artifacts" \
  "no scenario wins by default" \
  "Scenario-specific subsections are optional" \
  "summarized at the capability level" \
  "recorded independently" \
  "workflow control tokens" \
  "not delivery phases" \
  "awaiting that fact" \
  "domain-specific field" \
  "example payload fields"; do
  require "$EN_SCENARIO" "$marker" "EN scenario guidance"
done

for marker in \
  "existing-function-semantic-replacement" \
  "relationship" \
  "action" \
  "mixed" \
  "kebab-case ID"; do
  require "$ZH_SCENARIO" "$marker" "ZH scenario guidance"
done

require "$EN_ORCH" "references/scenario-guidance.md" "EN orchestrator scenario reference"
require "$ZH_ORCH" "references/scenario-guidance.md" "ZH orchestrator scenario reference"
require "$EN_ORCH" "scan the scenario registry" "EN orchestrator catalog discovery"

python3 - "$EN_SCENARIO" "$ZH_SCENARIO" "$EN_ORCH" "$ZH_ORCH" <<'PY'
import re
import sys
from pathlib import Path

def scenario_ids(path: str) -> tuple[list[str], list[str]]:
    text = Path(path).read_text(encoding="utf-8")
    registry_headings = ("Scenario registry", "\u573a\u666f\u76ee\u5f55")
    heading = next(
        (
            match
            for candidate in registry_headings
            for match in (
                re.search(r"^##\s+" + re.escape(candidate) + r"\s*$", text, re.MULTILINE),
            )
            if match is not None
        ),
        None,
    )
    if heading is None:
        raise SystemExit(f"FAIL: missing registry heading in {path}")
    remainder = text[heading.end():]
    next_heading = re.search(r"^##\s+", remainder, re.MULTILINE)
    registry_block = remainder if next_heading is None else remainder[:next_heading.start()]
    registry = re.findall(r"^\|\s*`([^`]+)`\s*\|", registry_block, re.MULTILINE)
    sections = re.findall(r"^##\s+`([^`]+)`\s*$", text, re.MULTILINE)
    return registry, sections

def section_body(path: str, heading: str) -> str:
    text = Path(path).read_text(encoding="utf-8")
    match = re.search(
        rf"^##\s+`?{re.escape(heading)}`?\s*$", text, re.MULTILINE
    )
    if match is None:
        raise SystemExit(f"FAIL: missing section {heading!r} in {path}")
    remainder = text[match.end():]
    next_heading = re.search(r"^##\s+", remainder, re.MULTILINE)
    return remainder if next_heading is None else remainder[:next_heading.start()]

def scenario_sections(path: str) -> dict[str, str]:
    text = Path(path).read_text(encoding="utf-8")
    matches = list(re.finditer(r"^##\s+`([^`]+)`\s*$", text, re.MULTILINE))
    sections = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections[match.group(1)] = text[match.end():end]
    return sections

def subsection_body(body: str, headings: tuple[str, ...]) -> str:
    heading = next(
        (
            match
            for candidate in headings
            for match in (
                re.search(r"^###\s+" + re.escape(candidate) + r"\s*$", body, re.MULTILINE),
            )
            if match is not None
        ),
        None,
    )
    if heading is None:
        raise SystemExit(f"FAIL: missing subsection from {headings!r}")
    remainder = body[heading.end():]
    next_heading = re.search(r"^###\s+", remainder, re.MULTILINE)
    return remainder if next_heading is None else remainder[:next_heading.start()]

en_registry, en_sections = scenario_ids(sys.argv[1])
zh_registry, zh_sections = scenario_ids(sys.argv[2])
for label, registry, sections in (
    ("EN", en_registry, en_sections),
    ("ZH", zh_registry, zh_sections),
):
    if len(registry) != len(set(registry)):
        raise SystemExit(f"FAIL: duplicate {label} scenario ID")
    if len(sections) != len(set(sections)):
        raise SystemExit(f"FAIL: duplicate {label} scenario section")
    if set(registry) != set(sections):
        raise SystemExit(f"FAIL: {label} registry/section mismatch")
    if any(not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", value) for value in registry):
        raise SystemExit(f"FAIL: {label} scenario ID is not stable kebab-case")
if set(en_registry) != set(zh_registry):
    raise SystemExit("FAIL: EN/ZH scenario registry mismatch")

# Every catalog entry follows the same extensible base shape. Headings can be
# localized, and the affected-surface role may use the most natural label for
# that scenario. Scenario-specific subsections are not globally required.
required_headings = {
    "EN": ("Trigger", "Decision model", "Boundaries", "Evidence", "Non-goals"),
    "ZH": (
        "\u89e6\u53d1\u6761\u4ef6", "\u51b3\u7b56\u6a21\u578b", "\u8fb9\u754c",
        "\u8bc1\u636e", "\u975e\u76ee\u6807",
    ),
}
surface_headings = {
    "EN": ("Inventory", "Affected surfaces", "Applicability"),
    "ZH": ("\u5f71\u54cd\u6e05\u5355", "\u53d7\u5f71\u54cd\u8868\u9762", "\u9002\u7528\u6027"),
}
for label, path, registry in (("EN", sys.argv[1], en_registry), ("ZH", sys.argv[2], zh_registry)):
    sections = scenario_sections(path)
    for scenario_id in registry:
        body = sections[scenario_id]
        headings = set(re.findall(r"^###\s+([^#\n]+?)\s*$", body, re.MULTILINE))
        missing = [heading for heading in required_headings[label] if heading not in headings]
        if missing:
            raise SystemExit(f"FAIL: {label} scenario {scenario_id} missing shape headings: {missing}")
        if not any(heading in headings for heading in surface_headings[label]):
            raise SystemExit(
                f"FAIL: {label} scenario {scenario_id} missing affected-surfaces/applicability heading"
            )

# Reuse/retirement is required by this scenario's semantics, not by the catalog
# base shape. Future scenarios may define different scenario-specific sections.
for label, path in (("EN", sys.argv[1]), ("ZH", sys.argv[2])):
    current = scenario_sections(path)["existing-function-semantic-replacement"]
    if not re.search(
        r"^####\s+.*(?:Reuse|Retire(?:d|ment)?|\u590d\u7528|\u9000\u5f79).*",
        current,
        re.MULTILINE | re.IGNORECASE,
    ):
        raise SystemExit(f"FAIL: {label} semantic-replacement scenario missing reuse/retirement subsection")

en_text = Path(sys.argv[1]).read_text(encoding="utf-8")
zh_text = Path(sys.argv[2]).read_text(encoding="utf-8")
zh_orch_text = Path(sys.argv[4]).read_text(encoding="utf-8")

def normalized(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()

semantic_pairs = (
    (
        "`preserve`: implementation may change while external behavior remains the same",
        "`preserve`\uff1a\u53ef\u4ee5\u66f4\u6362\u5b9e\u73b0\uff0c\u4f46\u5916\u90e8\u884c\u4e3a\u4fdd\u6301\u4e0d\u53d8",
    ),
    (
        "`extend`: the old behavior remains valid and the requirement adds behavior",
        "`extend`\uff1a\u65e7\u884c\u4e3a\u4ecd\u7136\u6709\u6548\uff0c\u9700\u6c42\u5728\u5176\u4e0a\u589e\u52a0\u884c\u4e3a",
    ),
    (
        "`compatible_replacement`: implementation and internal model change while the external contract remains intentionally compatible",
        "`compatible_replacement`\uff1a\u5b9e\u73b0\u548c\u5185\u90e8\u6a21\u578b\u6539\u53d8\uff0c\u4f46\u5916\u90e8\u5951\u7ea6\u6309\u610f\u56fe\u4fdd\u6301\u517c\u5bb9",
    ),
    (
        "`breaking_replacement`: the old business meaning, flow, or contract is intentionally replaced",
        "`breaking_replacement`\uff1a\u65e7\u4e1a\u52a1\u542b\u4e49\u3001\u6d41\u7a0b\u6216\u5951\u7ea6\u88ab\u6709\u610f\u66ff\u6362",
    ),
    (
        "`unknown`: the requirement does not establish whether old behavior remains",
        "`unknown`\uff08\u672a\u77e5\uff09\uff1a\u9700\u6c42\u6ca1\u6709\u8bf4\u660e\u65e7\u884c\u4e3a\u662f\u5426\u7ee7\u7eed\u5b58\u5728",
    ),
    (
        "`mixed`: different surfaces have explicitly different relationships",
        "`mixed`\uff08\u6df7\u5408\uff09\uff1a\u4e0d\u540c\u8868\u9762\u660e\u786e\u5177\u6709\u4e0d\u540c\u5173\u7cfb",
    ),
    (
        "Do not select this scenario for a greenfield capability",
        "\u6ca1\u6709\u65e2\u6709\u884c\u4e3a\u7684\u5168\u65b0\u80fd\u529b",
    ),
    (
        "relationship and the delivery action are recorded independently for each inventoried surface",
        "\u6bcf\u4e2a\u8868\u9762\u4ecd\u9700\u5206\u522b\u8bb0\u5f55\u65b0\u65e7\u5173\u7cfb\u548c\u4ea4\u4ed8\u52a8\u4f5c",
    ),
    (
        "mark only the dependent decision or task as awaiting that fact",
        "\u53ea\u5728\u5bbf\u4e3b\u5de5\u4f5c\u6d41\u65e2\u6709\u8bb0\u6cd5\u4e2d\u6807\u8bb0\u4f9d\u8d56\u8be5\u4e8b\u5b9e\u7684 \u51b3\u7b56\u6216\u4efb\u52a1\u6b63\u5728\u7b49\u5f85",
    ),
    (
        "For every retired or isolated surface, name the retirement boundary and attach negative evidence",
        "\u6bcf\u4e2a\u9000\u5f79\u6216\u9694\u79bb\u8868\u9762\u90fd\u8981\u5199\u660e\u9000\u5f79\u8fb9\u754c\u5e76\u9644\u4e0a\u8be5\u8fb9\u754c\u7684\u8d1f\u5411\u8bc1\u636e",
    ),
)
normalized_en = normalized(en_text)
normalized_zh = normalized(zh_text)
for en_marker, zh_marker in semantic_pairs:
    if en_marker not in normalized_en:
        raise SystemExit(f"FAIL: EN scenario semantic contract missing: {en_marker}")
    if zh_marker not in normalized_zh:
        raise SystemExit(f"FAIL: ZH scenario semantic contract missing: {zh_marker}")

for marker in (
    "\u573a\u666f\u6307\u5bfc", "\u5efa\u8bae\u7684\u51b3\u7b56\u8bb0\u5f55",
    "\u573a\u666f\u76ee\u5f55", "\u5bbf\u4e3b\u5de5\u4f5c\u6d41",
    "\u5f53\u524d\u52a8\u4f5c\u62a5\u544a", "\u5de5\u4f5c\u6d41\u63a7\u5236 token",
    "\u6b63\u5728\u7b49\u5f85", "\u975e\u76ee\u6807", "\u9886\u57df\u5b57\u6bb5\u540d",
    "\u5206\u6790\u89c6\u89d2", "\u5de5\u4f5c\u6d41\u6b65\u9aa4", "\u4ea4\u4ed8\u9636\u6bb5", "\u5168\u4ed3\u5e93",
    "\u53ef\u9009",
    "\u4ea4\u63a5\u6216\u4f9d\u8d56", "\u6388\u6743\u8fb9\u754c",
    "\u793a\u4f8b\u8f7d\u8377\u5b57\u6bb5",
    "\u4efb\u4f55\u573a\u666f\u90fd\u4e0d\u80fd\u9ed8\u8ba4\u80dc\u51fa",
    "\u6bcf\u4e2a\u8868\u9762\u4ecd\u9700\u5206\u522b\u8bb0\u5f55\u65b0\u65e7\u5173\u7cfb\u548c\u4ea4\u4ed8\u52a8\u4f5c",
):
    if marker not in zh_text:
        raise SystemExit(f"FAIL: ZH scenario guidance missing marker: {marker}")
if "\u68c0\u67e5\u573a\u666f\u76ee\u5f55\u4e2d\u7684\u89e6\u53d1\u6761\u4ef6" not in zh_orch_text:
    raise SystemExit("FAIL: ZH orchestrator missing generic catalog discovery")

# Scenario references are portable guidance. Keep this check structural rather
# than listing product names, business fields, or framework names. Markdown
# prose remains free to use ordinary domain words. Snake-case decision values
# are portable only when declared by that scenario's decision model.
structural_binding_patterns = tuple(
    re.compile(pattern)
    for pattern in (
        # Uppercase control identifiers (for example, a checkpoint token).
        r"(?<![A-Za-z0-9])[A-Z]{2,}[A-Z0-9]*(?:[-_][A-Z0-9]+)+(?![A-Za-z0-9])",
        # Project/class identifiers.
        r"(?<![A-Za-z0-9])(?:[A-Z][a-z0-9]+){2,}(?![A-Za-z0-9])",
        # Hidden, absolute, or extension-bearing repository paths.
        r"(?<![A-Za-z0-9])(?:\.\.?/|/)[A-Za-z0-9_.~/-]+",
        r"(?<![A-Za-z0-9])(?:[A-Za-z0-9_-]+/)+[A-Za-z0-9_.-]+\.[A-Za-z0-9]+(?![A-Za-z0-9])",
        # Package-qualified or otherwise dotted machine names.
        r"(?<![A-Za-z0-9])(?:[A-Za-z_][A-Za-z0-9_-]*\.){2,}[A-Za-z_][A-Za-z0-9_-]*(?![A-Za-z0-9])",
    )
)
snake_identifier = re.compile(r"[a-z][a-z0-9]*(?:_[a-z0-9]+)+")

decision_headings = {
    "EN": ("Decision model",),
    "ZH": ("\u51b3\u7b56\u6a21\u578b",),
}
declared_snake_tokens = {}
for label, path in (("EN", sys.argv[1]), ("ZH", sys.argv[2])):
    tokens = set()
    for body in scenario_sections(path).values():
        decision_body = subsection_body(body, decision_headings[label])
        tokens.update(
            token
            for token in re.findall(r"`([^`\n]+)`", decision_body)
            if snake_identifier.fullmatch(token)
        )
    declared_snake_tokens[label] = tokens
if declared_snake_tokens["EN"] != declared_snake_tokens["ZH"]:
    raise SystemExit("FAIL: EN/ZH declared snake-case decision values differ")

def strip_markdown_code(text: str) -> str:
    """Leave prose for structural checks; inspect code spans separately."""
    text = re.sub(r"```.*?```", " ", text, flags=re.DOTALL)
    text = re.sub(r"`[^`\n]+`", " ", text)
    # Link labels and destinations are checked separately below.
    return re.sub(r"\[[^\]]+\]\([^)]*\)", " ", text)

def fenced_code_violations(content: str, allowed_snake_tokens: set[str]) -> list[str]:
    violations = []
    blocks = re.findall(r"```[^\n]*\n(.*?)```", content, re.DOTALL)
    for block in blocks:
        for token in snake_identifier.findall(block):
            if token not in allowed_snake_tokens:
                violations.append(f"undeclared snake-case token {token!r}")
        for pattern in structural_binding_patterns:
            match = pattern.search(block)
            if match:
                violations.append(f"structural host binding {match.group(0)!r}")
    return violations

for label, content in (("EN", en_text), ("ZH", zh_text)):
    fenced_violations = fenced_code_violations(
        content, declared_snake_tokens[label]
    )
    if fenced_violations:
        raise SystemExit(
            f"FAIL: {label} scenario guidance fenced code is not portable: "
            f"{fenced_violations!r}"
        )

    code_tokens = [token.strip() for token in re.findall(r"`([^`\n]+)`", content)]
    for token in code_tokens:
        if (
            snake_identifier.fullmatch(token)
            and token not in declared_snake_tokens[label]
        ):
            raise SystemExit(
                f"FAIL: undeclared snake-case token {token!r} in "
                f"{label} scenario guidance inline code"
            )
        for pattern in structural_binding_patterns:
            match = pattern.search(token)
            if match:
                raise SystemExit(
                    f"FAIL: structural host binding {match.group(0)!r} in "
                    f"{label} scenario guidance inline code"
                )

    for link_label, destination in re.findall(r"\[([^\]]+)\]\(([^)]*)\)", content):
        for value in (link_label, destination):
            for pattern in structural_binding_patterns:
                match = pattern.search(value)
                if match:
                    raise SystemExit(
                        f"FAIL: structural host binding {match.group(0)!r} in "
                        f"{label} scenario guidance Markdown link"
                    )

    prose = strip_markdown_code(content)
    for pattern in structural_binding_patterns:
        match = pattern.search(prose)
        if match:
            raise SystemExit(
                f"FAIL: structural host binding {match.group(0)!r} in {label} scenario guidance"
            )

# Exercise the structural policy with neutral fixtures so it cannot silently
# become a no-op while remaining independent of any real project vocabulary.
structural_probes = (
    "DemoFeatureController",
    "demo.project.legacy_field",
    "CP-001",
    ".host/workflow/status.json",
)
for probe in structural_probes:
    if not any(pattern.search(probe) for pattern in structural_binding_patterns):
        raise SystemExit(f"FAIL: structural portability probe was not recognized: {probe}")

project_field_probe = "sample_payload_field"
if not snake_identifier.fullmatch(project_field_probe):
    raise SystemExit(
        f"FAIL: project-field portability probe was not recognized: {project_field_probe}"
    )
if project_field_probe in declared_snake_tokens["EN"]:
    raise SystemExit(
        f"FAIL: project-field portability probe was unexpectedly declared: {project_field_probe}"
    )

project_link_probe = "docs/sample/payload.md"
if not any(pattern.search(project_link_probe) for pattern in structural_binding_patterns):
    raise SystemExit(
        f"FAIL: project-link portability probe was not recognized: {project_link_probe}"
    )

fenced_binding_probe = """```text
DemoFeatureController
sample_payload_field
.host/workflow/status.json
```"""
fenced_probe_violations = fenced_code_violations(
    fenced_binding_probe, declared_snake_tokens["EN"]
)
if len(fenced_probe_violations) < 3:
    raise SystemExit(
        "FAIL: fenced-code portability probe did not exercise all binding classes: "
        f"{fenced_probe_violations!r}"
    )

# A generic inline token remains valid so future catalog entries are not
# constrained to today's relationship/action vocabulary.
portable_inline_probe = "http-method"
if any(pattern.search(portable_inline_probe) for pattern in structural_binding_patterns):
    raise SystemExit(
        f"FAIL: generic inline token was rejected by structural binding check: {portable_inline_probe}"
    )

# Ordinary domain wording, including a numbered review stage, remains portable.
probe = "A stage 1 review may hand off an unrelated surface to another owner."
if any(pattern.search(probe) for pattern in structural_binding_patterns):
    raise SystemExit("FAIL: portable domain wording was rejected by structural binding check")

# The orchestrator may define its own host lifecycle elsewhere, but this
# optional attachment must remain advisory and free of host-specific controls.
orchestrator_markers = (
    (sys.argv[3], "Scenario guidance", ("optional", "advisory")),
    (sys.argv[4], "\u573a\u666f\u6307\u5bfc", ("\u53ef\u9009", "\u6307\u5bfc\u6027\u5185\u5bb9")),
)
stage_binding_patterns = (
    re.compile(
        r"\b(?:Stage\s+(?:[0-9]+[A-Za-z]?|[A-Za-z][A-Za-z0-9_-]*)|"
        r"(?:the\s+)?[0-9]+[A-Za-z]?\s+stage)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:\u7b2c\s*(?:[0-9]+[A-Za-z]?|[\u4e00\u4e8c\u4e09\u56db\u4e94\u516d\u4e03\u516b\u4e5d\u5341\u767e]+)\s*\u9636\u6bb5|"
        r"\u9636\u6bb5\s*(?:[0-9]+[A-Za-z]?|[\u4e00\u4e8c\u4e09\u56db\u4e94\u516d\u4e03\u516b\u4e5d\u5341\u767e]+)|"
        r"[0-9]+[A-Za-z]?\s*\u9636\u6bb5)"
    ),
)
for path, heading, markers in orchestrator_markers:
    body = section_body(path, heading)
    body_lower = body.lower()
    for marker in markers:
        if marker.lower() not in body_lower:
            raise SystemExit(
                f"FAIL: orchestrator section {path} missing advisory marker: {marker}"
            )
    prose = strip_markdown_code(body)
    for pattern in structural_binding_patterns:
        if pattern.search(prose):
            raise SystemExit(
                f"FAIL: structural host binding {pattern.pattern!r} in orchestrator section {path}"
            )
    links = re.findall(r"\[([^\]]+)\]\(([^)]*)\)", body)
    if links != [("references/scenario-guidance.md", "references/scenario-guidance.md")]:
        raise SystemExit(
            f"FAIL: orchestrator scenario section has unexpected Markdown links: {links!r}"
        )
    for pattern in stage_binding_patterns:
        match = pattern.search(body)
        if match:
            raise SystemExit(
                f"FAIL: orchestrator scenario guidance is bound to a delivery stage: {match.group(0)!r}"
            )

stage_binding_probes = (
    "During Stage 1 requirement analysis, scan the registry.",
    "During Stage 3a requirement analysis, scan the registry.",
    "During the 3a stage, scan the registry.",
    "\u5728\u7b2c 2 \u9636\u6bb5\u68c0\u67e5\u573a\u666f\u76ee\u5f55\u3002",
    "\u5728\u7b2c 3b \u9636\u6bb5\u68c0\u67e5\u573a\u666f\u76ee\u5f55\u3002",
    "\u5728 3a \u9636\u6bb5\u68c0\u67e5\u573a\u666f\u76ee\u5f55\u3002",
)
for probe in stage_binding_probes:
    if not any(pattern.search(probe) for pattern in stage_binding_patterns):
        raise SystemExit(f"FAIL: delivery-stage binding probe was not recognized: {probe}")
PY

echo "PASS: change-scenario guidance markers"
