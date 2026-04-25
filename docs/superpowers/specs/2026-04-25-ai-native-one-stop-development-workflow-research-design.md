# AI Native One-Stop Development Workflow Research Design

Date: 2026-04-25
Status: approved-for-spec-review

## Goal

Produce a detailed research report and selection recommendation for modern AI-native software delivery workflows that can move from requirements to UI, backend, client implementation, tests, review, merge, deployment, and feedback with minimal human coordination.

The report should help decide how `spec-dev` should evolve so AI agents can safely take over more development work while humans keep control over product truth, governance decisions, and high-risk approvals.

## Output

Primary report:

`/Users/charvin/Projects/spec-dev/docs/research/2026-04-25-ai-native-one-stop-development-workflow-research.md`

If the final report needs to live inside a git repository for easier review and versioning, use:

`/Users/charvin/Projects/spec-dev/ai-delivery-kit/docs/research/2026-04-25-ai-native-one-stop-development-workflow-research.md`

## Research Scope

The report will include three complementary analysis axes.

### Axis 1: Tool And Methodology Deep Dives

Research these tools and methodologies one by one:

- OpenAI Codex
- Claude Code
- GitHub Copilot coding agent
- Cursor
- GSD
- Spec Kit
- OpenSpec
- BMad
- Lovable
- Replit Agent
- v0
- Figma Make

Each section will cover:

- positioning
- core mechanism
- coverage across requirement, UI, backend, client, tests, review, merge, deployment, and feedback
- automation strength
- governance and observability strength
- risks and limitations
- suitable scenarios
- lessons for `spec-dev`

### Axis 2: Layered Taxonomy

Group the ecosystem by capability layer:

- coding agents
- workflow orchestration frameworks
- spec-driven frameworks
- design-to-code platforms
- cloud full-stack generation platforms
- governance and observability layers

For each layer, compare representative tools and derive the target role that layer should play in `spec-dev`.

### Axis 3: End-To-End Delivery Chain

Reconstruct a recommended one-stop workflow by development stage:

- requirements
- design and UI
- API and backend
- client implementation
- testing
- review
- merge and deployment
- operations feedback

Each stage will specify:

- recommended tool combination
- required inputs
- expected outputs
- automation boundary
- governance gates
- human approval points

## Source Policy

Use official sources first and avoid treating marketing claims as proven engineering facts.

- OpenAI Codex: OpenAI official pages, OpenAI Help Center, and OpenAI Platform docs.
- Claude Code: Anthropic official docs, especially subagents, hooks, MCP, GitHub Actions, SDK, settings, and common workflows.
- GitHub Copilot: GitHub Docs, especially coding agent, PR creation, code review, custom instructions, MCP, and security boundaries.
- Cursor, Windsurf, Factory, and Jules: official docs as supporting comparisons for coding-agent direction.
- GSD, Spec Kit, OpenSpec, and BMad: official docs or official GitHub repositories.
- Lovable, Replit Agent, v0, and Figma Make: official docs or official product docs.
- `spec-dev`: local repository inspection is authoritative for current architecture and workflow state.

The report must cite source URLs for external facts and clearly separate source-backed facts from engineering judgment.

## Local Context To Inspect

The report will use these local projects as the `spec-dev` baseline:

- `/Users/charvin/Projects/spec-dev/ai-delivery-kit`
- `/Users/charvin/Projects/spec-dev/ai-delivery-admin`

Important local concepts to evaluate:

- `.ai-delivery` as workflow truth
- `ai-delivery-orchestrator`
- project-local workflow skills
- `ai-delivery-admin-support`
- governed MCP tool surface
- `traceability.json`
- Spec Kit bridge artifacts
- Superpowers execution discipline
- API contract mapping
- UI acceptance and visual acceptance gates
- blocker recovery
- worktree and merge governance

## Recommended Report Structure

1. Executive conclusion
2. Tool and methodology deep dives
3. Layered taxonomy analysis
4. End-to-end one-stop workflow recommendation
5. Current `spec-dev` workflow assessment
6. `spec-dev` optimization recommendations
7. Phased adoption roadmap
8. Source index

## Key Hypotheses To Validate

The report should validate or revise these working hypotheses:

- The best practical architecture is not a single tool, but a stack: `spec truth + design truth + orchestration + coding agents + governed writes + observable runtime`.
- `spec-dev` already has strong governance primitives, but may have too many overlapping gates and too much duplicated status vocabulary.
- Cloud full-stack generators are useful for MVP and exploration, but risky as the only source of truth for complex brownfield engineering.
- Coding agents become safer when tasks are slice-scoped, worktree-isolated, test-backed, and governed through MCP or equivalent controlled write surfaces.
- The next `spec-dev` improvement should focus on simplifying orchestration and making state, blockers, and recovery more automatic, not on adding more free-form documents.

## `spec-dev` Evaluation Criteria

Assess current and proposed workflows against:

- AI autonomy
- human control
- traceability
- recovery from blockers
- context efficiency
- UI fidelity
- API/backend tolerance
- parallel execution safety
- testability
- review quality
- operational observability
- maintenance cost

## Non-Goals

This report will not:

- implement code changes
- install or configure third-party tools
- replace current `ai-delivery-admin` or `ai-delivery-kit` architecture
- produce a vendor pricing comparison beyond high-level adoption notes
- claim that any external tool can safely replace human review for high-risk changes

## Acceptance Criteria

The report is complete when it:

- covers all named tools and methodologies
- includes all three analysis axes requested by the user
- maps external findings back to concrete `spec-dev` recommendations
- distinguishes facts, source citations, and engineering judgment
- includes a practical staged roadmap
- gives enough detail for a later implementation plan to be written without redoing the research

## Risks And Mitigations

Risk: AI coding products change quickly.

Mitigation: cite retrieval date and prefer current official docs.

Risk: the report becomes too generic.

Mitigation: every major section must end with implications for `spec-dev`.

Risk: the report over-recommends automation.

Mitigation: explicitly mark human approval points and non-automatable governance decisions.

Risk: local workflow complexity is misread.

Mitigation: base `spec-dev` assessment on local files, existing plans, skills, admin MCP surfaces, and real repository structure.
