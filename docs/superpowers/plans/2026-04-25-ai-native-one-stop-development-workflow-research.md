# AI Native One-Stop Development Workflow Research Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce a detailed, source-cited research report and selection recommendation for AI-native one-stop development workflows, mapped back to `spec-dev` optimization decisions.

**Architecture:** The work is documentation-first. Gather current official-source facts, inspect local `spec-dev` architecture, then write one versioned report that combines tool deep dives, layered taxonomy, end-to-end workflow design, and concrete `spec-dev` recommendations.

**Tech Stack:** Markdown, local repository inspection with `rg`/`sed`/`git`, official web sources, `ai-delivery-kit` docs.

---

## File Structure

- Create: `/Users/charvin/Projects/spec-dev/ai-delivery-kit/docs/research/2026-04-25-ai-native-one-stop-development-workflow-research.md`
  - Owns the final research report and selection recommendation.
- Modify: `/Users/charvin/Projects/spec-dev/ai-delivery-kit/docs/superpowers/plans/2026-04-25-ai-native-one-stop-development-workflow-research.md`
  - Tracks execution progress while the report is written.
- Read-only reference: `/Users/charvin/Projects/spec-dev/ai-delivery-kit/docs/superpowers/specs/2026-04-25-ai-native-one-stop-development-workflow-research-design.md`
  - Approved scope and acceptance criteria.
- Read-only local context: `/Users/charvin/Projects/spec-dev/ai-delivery-kit`
  - Project-local workflow skills, `.ai-delivery`, orchestrator, prior plans.
- Read-only local context: `/Users/charvin/Projects/spec-dev/ai-delivery-admin`
  - Admin app, MCP tools, support skill, governed API, tests, README.

## Source Set

Use these source families while writing the report:

- OpenAI official Codex pages, Help Center, and Platform docs.
- Anthropic official Claude Code docs.
- GitHub Docs for Copilot coding agent and code review.
- Cursor official docs for Agent and Background Agents.
- GSD official site or official GitHub repository.
- GitHub Spec Kit official repository and docs.
- OpenSpec official docs.
- BMad Method official docs or repository.
- Lovable official docs.
- Replit Agent official docs.
- Vercel v0 official docs.
- Figma Make official docs and developer docs.
- Supporting coding-agent comparisons from official Windsurf, Factory, or Jules docs only where useful.

## Task 1: Reconfirm Approved Scope And Local Baseline

**Files:**
- Read: `/Users/charvin/Projects/spec-dev/ai-delivery-kit/docs/superpowers/specs/2026-04-25-ai-native-one-stop-development-workflow-research-design.md`
- Read: `/Users/charvin/Projects/spec-dev/ai-delivery-kit/.agents/skills/ai-delivery/ai-delivery-orchestrator/SKILL.md`
- Read: `/Users/charvin/Projects/spec-dev/ai-delivery-kit/.agents/skills/ai-delivery/ai-delivery-orchestrator/references/stage-mapping.md`
- Read: `/Users/charvin/Projects/spec-dev/ai-delivery-admin/README.md`
- Read: `/Users/charvin/Projects/spec-dev/ai-delivery-admin/mcp-server/README.md`

- [x] **Step 1: Read the approved design spec**

Run:

```bash
sed -n '1,260p' docs/superpowers/specs/2026-04-25-ai-native-one-stop-development-workflow-research-design.md
```

Expected: the command prints the approved three-axis report scope, source policy, local context, acceptance criteria, and risks.

- [x] **Step 2: Read the orchestrator chain**

Run:

```bash
sed -n '1,260p' .agents/skills/ai-delivery/ai-delivery-orchestrator/SKILL.md
```

Expected: the command prints the current stage sequence from requirement breakdown through Spec Kit bind and development execution.

- [x] **Step 3: Read current stage mapping**

Run:

```bash
sed -n '1,220p' .agents/skills/ai-delivery/ai-delivery-orchestrator/references/stage-mapping.md
```

Expected: the command prints fixed inputs, outputs, and completion guards for each `ai-delivery` stage.

- [x] **Step 4: Read admin boundaries**

Run from `/Users/charvin/Projects/spec-dev/ai-delivery-admin`:

```bash
sed -n '1,220p' README.md
```

Expected: the command prints the admin ownership boundary, workflow closure model, governed truth contracts, and smoke coverage.

- [x] **Step 5: Read MCP surface summary**

Run from `/Users/charvin/Projects/spec-dev/ai-delivery-admin`:

```bash
sed -n '1,180p' mcp-server/README.md
```

Expected: the command prints binding, read, and governed write tool families.

## Task 2: Gather Current External Source Facts

**Files:**
- Create content in: `/Users/charvin/Projects/spec-dev/ai-delivery-kit/docs/research/2026-04-25-ai-native-one-stop-development-workflow-research.md`

- [x] **Step 1: Browse official source pages for coding agents**

Use web search and official docs to gather source-backed facts for:

- OpenAI Codex
- Claude Code
- GitHub Copilot coding agent
- Cursor

Expected facts to capture:

- execution mode: local, IDE, cloud, or background
- parallelism and worktree or sandbox model
- project instruction mechanism
- MCP or tool extension mechanism
- PR or review integration
- safety and governance boundary

- [x] **Step 2: Browse official source pages for orchestration and spec frameworks**

Use official docs or official repositories for:

- GSD
- Spec Kit
- OpenSpec
- BMad

Expected facts to capture:

- primary artifact model
- workflow phases
- supported AI tools
- change or task decomposition model
- strength in greenfield or brownfield work
- execution governance model

- [x] **Step 3: Browse official source pages for app-generation and design-to-code platforms**

Use official docs for:

- Lovable
- Replit Agent
- v0
- Figma Make

Expected facts to capture:

- prompt-to-app or design-to-code capability
- frontend/backend/data coverage
- deployment or hosting path
- source-code ownership or GitHub sync model
- best-fit use case
- risk in complex brownfield repositories

- [x] **Step 4: Keep source links in the draft**

For every external product section, add a short `Sources:` line with at least one official URL.

Expected: every named external tool or methodology has a source URL in the draft report.

## Task 3: Write Tool And Methodology Deep Dives

**Files:**
- Modify: `/Users/charvin/Projects/spec-dev/ai-delivery-kit/docs/research/2026-04-25-ai-native-one-stop-development-workflow-research.md`

- [x] **Step 1: Create the report file with top-level structure**

Create:

```markdown
# AI Native One-Stop Development Workflow Research

Date: 2026-04-25
Status: research-report

## Executive Conclusion

## Tool And Methodology Deep Dives

## Layered Taxonomy

## End-To-End One-Stop Workflow

## Current spec-dev Workflow Assessment

## spec-dev Optimization Recommendations

## Phased Adoption Roadmap

## Source Index
```

Expected: the file exists with all required top-level sections.

- [x] **Step 2: Write the executive conclusion**

Include these decisions:

- no single product should own the full workflow
- the recommended stack is `truth sources + orchestration + coding agents + governed writes + observability`
- `spec-dev` should keep `.ai-delivery`, traceability, governed MCP, worktree isolation, and blocker recovery
- `spec-dev` should simplify duplicated gates and status vocabulary
- cloud full-stack tools are useful for prototyping, not as sole truth for complex brownfield engineering

Expected: the section gives clear selection guidance before detailed analysis.

- [x] **Step 3: Write one fixed-format deep dive per named tool**

For each tool, use this structure:

```markdown
### <Tool Name>

**定位**

**核心机制**

**端到端覆盖**

**自动化能力**

**治理与可观测**

**风险与限制**

**适用场景**

**对 spec-dev 的启发**

Sources:
- <official source URL>
```

Expected: all named tools from the approved spec appear exactly once in this section.

- [x] **Step 4: Add a comparison table**

Add a table with columns:

- Tool
- Best Role
- Requirement
- UI
- Backend/API
- Client
- Test/Review
- Governance
- Recommended `spec-dev` Use

Expected: the table makes cross-tool tradeoffs visible without replacing the detailed sections.

## Task 4: Write Layered Taxonomy And Target Architecture

**Files:**
- Modify: `/Users/charvin/Projects/spec-dev/ai-delivery-kit/docs/research/2026-04-25-ai-native-one-stop-development-workflow-research.md`

- [x] **Step 1: Write taxonomy by capability layer**

Write subsections for:

- coding agents
- workflow orchestration frameworks
- spec-driven frameworks
- design-to-code platforms
- cloud full-stack generation platforms
- governance and observability layers

Expected: each subsection compares representative tools and identifies what `spec-dev` should absorb from that layer.

- [x] **Step 2: Write the `spec-dev` target architecture**

Include this target architecture:

```text
Requirement truth + Design truth
        |
        v
.ai-delivery governed fact layer
        |
        v
Orchestrator / stage gate decision layer
        |
        v
Spec Kit bridge and task generation
        |
        v
Worktree-isolated coding agents
        |
        v
Review, visual acceptance, verification, merge
        |
        v
Runtime observability and feedback loop
```

Expected: the report states what owns truth, what owns execution, and what owns governance.

## Task 5: Write End-To-End Workflow Recommendation

**Files:**
- Modify: `/Users/charvin/Projects/spec-dev/ai-delivery-kit/docs/research/2026-04-25-ai-native-one-stop-development-workflow-research.md`

- [x] **Step 1: Write stage-by-stage workflow**

Write sections for:

- requirements
- design and UI
- API and backend
- client implementation
- testing
- review
- merge and deployment
- operations feedback

Expected: each stage lists recommended tools, inputs, outputs, gates, AI automation boundary, and human approval point.

- [x] **Step 2: Add one recommended integrated chain**

Include a concise chain such as:

```text
Product requirement
-> requirement breakdown
-> API context capture
-> Figma evidence and UI acceptance
-> interaction and delivery slices
-> Spec Kit spec/plan/tasks
-> worktree-isolated Codex or Claude Code implementation
-> automated tests and code review
-> visual acceptance
-> governed merge
-> deployed feedback and follow-up tasks
```

Expected: the chain is practical enough to become a later implementation plan.

## Task 6: Write Current `spec-dev` Assessment And Optimization Recommendations

**Files:**
- Modify: `/Users/charvin/Projects/spec-dev/ai-delivery-kit/docs/research/2026-04-25-ai-native-one-stop-development-workflow-research.md`

- [x] **Step 1: Assess current strengths**

Cover:

- `.ai-delivery` as local truth
- project-local workflow skills
- `ai-delivery-orchestrator`
- Spec Kit bridge
- governed MCP writes
- admin observability
- blocker and resume model
- worktree and merge governance

Expected: the assessment is grounded in local files, not only external tool research.

- [x] **Step 2: Assess current risks**

Cover:

- duplicated stage names and status vocabulary
- too many markdown artifacts for agents to keep synchronized
- risk that `todo.md`, `traceability.json`, `status.json`, and Spec Kit bindings drift
- API stage over-gating risk, even after non-blocking policy
- missing CI or cloud-agent feedback loop
- limited automatic visual acceptance and deployment feedback

Expected: each risk includes a practical mitigation direction.

- [x] **Step 3: Write optimization recommendations**

Group recommendations into:

- keep
- absorb
- avoid
- split
- merge
- refactor
- add

Expected: recommendations are concrete enough to convert into tasks.

- [x] **Step 4: Write phased adoption roadmap**

Write:

- near term: documentation, status vocabulary, source index, source-of-truth simplification
- mid term: orchestrator and admin workflow simplification, CI review agent, visual acceptance loop
- long term: background agents, automated triage, deployment feedback, multi-agent scheduling

Expected: roadmap distinguishes low-risk changes from architecture-level changes.

## Task 7: Verify, Self-Review, And Commit

**Files:**
- Modify: `/Users/charvin/Projects/spec-dev/ai-delivery-kit/docs/research/2026-04-25-ai-native-one-stop-development-workflow-research.md`
- Modify: `/Users/charvin/Projects/spec-dev/ai-delivery-kit/docs/superpowers/plans/2026-04-25-ai-native-one-stop-development-workflow-research.md`

- [x] **Step 1: Verify required tool coverage**

Run:

```bash
rg -n "Codex|Claude Code|GitHub Copilot|Cursor|GSD|Spec Kit|OpenSpec|BMad|Lovable|Replit|v0|Figma Make" docs/research/2026-04-25-ai-native-one-stop-development-workflow-research.md
```

Expected: each named tool appears in a dedicated deep-dive heading and in the source index.

- [x] **Step 2: Verify required structure**

Run:

```bash
rg -n "^## " docs/research/2026-04-25-ai-native-one-stop-development-workflow-research.md
```

Expected: output includes all major sections from the approved spec.

- [x] **Step 3: Verify no unresolved placeholders**

Run:

```bash
rg -n "TB[D]|TO[D]O|PLACEHOLDE[R]|待[定]|未[定]" docs/research/2026-04-25-ai-native-one-stop-development-workflow-research.md docs/superpowers/plans/2026-04-25-ai-native-one-stop-development-workflow-research.md
```

Expected: no matches.

- [x] **Step 4: Verify source links exist**

Run:

```bash
rg -n "https?://" docs/research/2026-04-25-ai-native-one-stop-development-workflow-research.md
```

Expected: output includes official-source URLs for all externally researched products.

- [x] **Step 5: Review git diff**

Run:

```bash
git diff -- docs/research/2026-04-25-ai-native-one-stop-development-workflow-research.md docs/superpowers/plans/2026-04-25-ai-native-one-stop-development-workflow-research.md
```

Expected: diff contains the report and plan progress updates only.

- [x] **Step 6: Commit**

Run:

```bash
git add docs/research/2026-04-25-ai-native-one-stop-development-workflow-research.md docs/superpowers/plans/2026-04-25-ai-native-one-stop-development-workflow-research.md
git commit -m "docs: add ai-native development workflow research"
```

Expected: git creates a docs commit containing the research report and updated execution plan.

## Self-Review Checklist

- [x] Every requirement in the approved design spec is covered by a task above.
- [x] Every named tool or methodology has a dedicated report section.
- [x] The report will cite official sources for external facts.
- [x] The report will distinguish facts from engineering judgment.
- [x] The report will map every major finding back to `spec-dev`.
- [x] The final verification steps check coverage, structure, placeholders, links, diff, and commit.
