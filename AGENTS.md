# AGENTS.md

Guidance for Codex in this repository.

## Stack

- Backend: Python / FastAPI / Clean Architecture / DDD
- Frontend: Next.js 15 / App Router / Server Components / Server Actions / daisyUI
- Migrations: Alembic
- Python package manager: uv

The backend, frontend, and docs app folders may be absent in a clean workflow test. Recreate them
only from memory and MCP-backed rules.

## Non-Negotiable Rules

1. Keep product intent, architecture decisions, and implementation slices separate.
   The product flow is `PRDs -> ADRs -> feature slices with rules`. The `product-owner` first offers
   opinionated PRD directions for the user to pick, then writes complete product PRDs. The
   `software-architect` turns accepted PRDs into ADRs, fetches the needed guideline slugs, derives
   `memory/feature/<feature-slice>/slice.md` files, and maintains the single global
   `memory/rules.md`. Developers and QA read the linked PRDs/ADRs/slices; they do not refetch
   guideline text.

2. Route work through the agent system.
   Start product or feature work with `orchestrator`. It sequences the loop:
   `product-owner` proposes PRD options and writes the selected PRD set, `business-challenger` scores
   the PRDs, `software-architect` writes ADRs and MCP-backed feature slices, and
   `technical-challenger` scores the ADR/slice plan. The loop repeats until both challengers accept
   at **at least 90 percent** (capped at 3 rounds, then the user is asked). Only then does the main
   thread execute the Agent Plan rows, returning to the orchestrator for `ESCALATE`, `BLOCKED`, or
   QA finding fan-out.
   Incomplete information is always asked back to the user, with planning held in plan mode until
   the answer arrives.

3. Keep Claude and Codex guidance mirrored.
   `CLAUDE.md` and `AGENTS.md` must stay structurally aligned. `.claude/` and `.codex/` support
   files must stay mirrored by role, hook, template, and guideline-routing purpose, except for
   runtime-specific names and tool syntax.

4. Block subagent reads of agent infrastructure.
   Only the main thread and the coordination tier (`orchestrator`, `product-owner`,
   `software-architect`, `business-challenger`, `technical-challenger`) may read root guidance,
   agent config, hooks, workflow scripts, settings, or cross-runtime support files.
   Implementer/QA subagents may read those files only when the orchestrator handoff names the exact
   path. Any subagent may read `.codex/templates/**` and `.codex/skills/**` - reference material,
   not agent infrastructure.

## Agent Roles

| Agent | Responsibility |
|---|---|
| `orchestrator` | Coordinates the PRD/ADR/slice challenge loop and routes only the required implementer/QA agents; no planning, no MCP |
| `product-owner` | Offers opinionated PRD options, writes complete PRDs, defines users/use cases/outcomes/requirements, and asks product questions; no MCP |
| `business-challenger` | Challenges PRD problem clarity, target users, use cases, scope, outcomes, requirements, and business risk; read-only |
| `software-architect` | Converts accepted PRDs into ADRs and MCP-backed feature slices, writes `memory/rules.md`, and emits the Agent Plan |
| `technical-challenger` | Challenges ADRs, provenance, architecture, contracts, feasibility, coverage, operations, and security; read-only |
| `backend-developer` | Implements backend code and tests from memory; no MCP access |
| `frontend-developer` | Implements frontend code and tests from memory; no MCP access |
| `qa-checker` | Writes/heals Playwright story tests when needed, runs them, and produces qa-evidence.json/e2e-coverage.json; no MCP access |
| `qa-challenger` | Reviews qa-checker's evidence and the slice, and returns the final `APPROVED` or `BLOCKED` merge verdict; read-only |

The orchestrator runs product or feature work through
`product-owner` -> `business-challenger` -> `software-architect` -> `technical-challenger` before
routing implementation. The product-owner starts with 2-3 concrete PRD direction options when the
request allows different product shapes; the user picks before full PRDs are written.
`business-challenger` scores its 6-persona panel and `technical-challenger` scores its 8-persona
panel; all challenges stop only when both acceptance scores are at least 90 percent. If the loop
hits its round cap or any coordination agent flags missing information, the orchestrator asks the
user and holds planning in plan mode.

Routing is conditional. Backend-only work skips frontend. Frontend-only work skips backend.
Docs/config/copy/minimal changes can route straight to `qa-challenger` review (no Playwright work
for `qa-checker` to do). Foundation work is one
cross-cutting monorepo slice when it touches repo layout, root manifests, bootstrap scripts,
workspace config, or both app roots.

Split large products into coherent PRDs, then into component ADRs, then into business feature
slices. Big components may have parent PRDs/ADRs plus smaller component PRDs/ADRs. Feature slices
must link their parent PRD and ADR so implementer/QA agents can read or grep the bigger context when
needed. Slice by business feature, not by layer. Write one `slice.md` per business feature (never
split a single feature into scaffold, endpoint, CRUD, page, and test slices). When features depend on
each other, keep them separate and link the ordering through each slice's `## Dependencies`.

## PRD, ADR, And Memory Contract

The product-owner writes PRDs under `memory/PRD/<purpose>/prd.md`. A PRD is a
complete product artifact, not a feature slice. It must cover:

- Problem/opportunity, target users, target use cases, and current journey or landscape when useful.
- Proposed solution/elevator pitch and the top MVP value propositions.
- 2-3 measurable goals or non-failure outcomes.
- MVP functional requirements bucketed by user journey or use case, with P0/P1/P2 priority.
- Non-goals, product risks, dependencies, open questions, and appendix links.

When the request is broad, the product-owner first returns 2-3 opinionated PRD direction options and
waits for the user's selection before writing full PRDs. Large product areas should split into a
parent PRD plus smaller component PRDs, linked through `## Components` and `## Dependencies`.

The software-architect writes ADRs under `memory/ADR/<purpose>/adr.md` from
accepted PRDs, then derives memory:

- One `memory/PRD/<purpose>/prd.md` per selected product or component PRD.
- One `memory/ADR/<purpose>/adr.md` per architectural decision.
- One `memory/feature/<feature-slice>/slice.md` per business feature.
- The single global `memory/rules.md`, one block per guideline slug, reused across every
  feature and never split by category. There is no per-slice `rules.md`.
- One `agent-evidence/prompt-N/agent-evidence.json` per user prompt, with `prompt-N`
  incrementing by 1 without gaps. It records the source prompt hash, one root `x_request_id`
  propagated through every routed planning/QA agent record, what each agent interpreted, what it
  produced, when it ran, and hashes generated by
  `python scripts/validate/cli.py agent-evidence-hash --file <path> --write`.

Each ADR records the architectural decision, context from PRDs, options considered, decision,
consequences, affected components, and feature slices it enables. Each `slice.md` links the rest of
the plan through a `## Dependencies` section: `PRD:` lists the parent PRD(s), `ADR:` lists the
architectural decision(s), `Depends on:` lists sibling feature slices it needs first, and `Rules:`
lists the guideline slugs it draws on (each defined as a block in `memory/rules.md`). Every
block in `memory/rules.md` must cite `Source: get_guideline("<slug>")`, and the orchestrator
sequences features by their `Depends on:` graph.

Full slices must include `Status`, `Request`, `Slice Boundary`, `Dependencies`, `Do Not Touch`,
`Implementation Plan`, `Acceptance Criteria`, `QA Handoff`, and provenance. User-facing slices also
need `E2E Test Stories`, with each row mapped to one Playwright `test(...)`. Acceptance criteria must
use stable `AC-###` IDs, `Test Coverage` must map every criterion to backend/frontend-unit/E2E/harness
tests, and user-facing slices must include `e2e-coverage.json` mapping initial-prompt user stories
to Playwright tests.

Do not create role-specific memory directories such as `00-shared/`, `backend/`,
`frontend/`, `qa-checker/`, or `qa-challenger/`; rules live in the single global
`memory/rules.md`, never split by category. Do not put prompt interpretation evidence or
validator allow-lists in memory.

## Deterministic Enforcement

Hooks in `.codex/hooks/` are registered by `.codex/hooks.json` and enabled by `.codex/config.toml`.
They own formatting, forbidden edits/reads, MCP scope, commit secret checks, changed-file
formatting, and developer stop gates.

Workflow scripts own mechanical review. Use `python scripts/validate/cli.py doctor --root .` for
the full integrity check; see `scripts/README.md` for the complete validator command list.

Hooks run the applicable script checks automatically. `validate-tools` runs inside the developer
stop hook; it is not a QA step. QA evidence must be machine-readable `qa-evidence.json`, generated
by the gate runner, with command/cwd/exit-code/timestamp/output-path records, successful
`docker compose up` evidence when `docker-compose.yml` exists, and backend/frontend unit coverage
at or above 80 percent.
Agent interpretation evidence must be machine-readable
`agent-evidence/prompt-N/agent-evidence.json`; stale hashes, missing prompt numbers, missing
`x_request_id` propagation, or hand-written hashes are rejected by
`python scripts/validate/cli.py agent-evidence --root .`.

## MCP Budget

- Prefer existing `memory/feature/`, repo files, tests, and prior handoffs.
- The software-architect may call `get_metadata()` once per slice only when routing does not identify the
  needed slugs. No other agent calls MCP.
- Fetch only specific guidelines required for the slice.
- Never call broad context tools such as `get_all_context` for normal feature work.
- If a downstream agent lacks context, it asks the orchestrator once for a targeted update; the
  orchestrator routes back through the product-owner for product gaps or the software-architect for
  MCP-backed technical gaps. If still blocked, it returns `ESCALATE` or `BLOCKED`.
- Correctness beats compactness. Unsupported concrete paths, commands, dependencies, tests, and
  acceptance criteria must be marked `BLOCKED`, not guessed.

## Development Commands

The scaffold commands depend on which app folders exist. Bootstrap scripts are the stable entry
points:

| Task | Command |
|---|---|
| Bootstrap full toolchain on macOS | `bash scripts/bootstrap.sh` |
| Bootstrap full toolchain on Windows | `powershell -ExecutionPolicy Bypass -File scripts\bootstrap.ps1` |
| Connect clone to your own repo on macOS | `bash scripts/init-project.sh` |
| Connect clone to your own repo on Windows | `powershell -ExecutionPolicy Bypass -File scripts\init-project.ps1` |

When a slice creates backend or frontend manifests, that slice must document its run, lint,
type-check, test, and migration commands in memory.

## Environment

Variables go in `.env` files, which are gitignored. Document required keys in `.env.example` when a
slice introduces configuration.
