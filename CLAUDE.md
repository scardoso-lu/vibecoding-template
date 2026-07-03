# CLAUDE.md

Guidance for Claude Code (claude.ai/code) in this repository.

## Stack

- Backend: Python / FastAPI / Clean Architecture / DDD
- Frontend: Next.js 15 / App Router / Server Components / Server Actions / daisyUI
- Migrations: Alembic
- Python package manager: uv

The backend, frontend, and docs app folders may be absent in a clean workflow test. Recreate them
only from feature memory and MCP-backed rules.

## Non-Negotiable Rules

1. Use feature-slice memory for guidelines.
   The `fullstack-guidelines` MCP server is the source of truth. The `planner` fetches the
   needed slugs, writes one `feature-memory/<feature>/slice.md` per business feature plus the single
   global `feature-memory/rules.md`, and hands the relevant files to downstream agents.
   Developers and QA do not refetch guideline text.

2. Route work through the agent system.
   Start feature work with `orchestrator`. It sequences the plan/challenge loop: `planner` writes
   the plan, `challenger` scores it as a gang, and the loop repeats until the challenger accepts at
   **at least 90 percent** (capped at 3 rounds, then the user is asked). Only then does the main
   thread execute the Agent Plan rows, returning to the orchestrator for `ESCALATE`, `BLOCKED`, or
   QA finding fan-out. Incomplete information is always asked back to the user, with planning held
   in plan mode until the answer arrives.

3. Keep Claude and Codex guidance mirrored.
   `CLAUDE.md` and `AGENTS.md` must stay structurally aligned. `.claude/` and `.codex/` support
   files must stay mirrored by role, hook, template, and guideline-routing purpose, except for
   runtime-specific names and tool syntax.

4. Block subagent reads of agent infrastructure.
   Only the main thread and the coordination tier (`orchestrator`, `planner`, `challenger`) may read
   root guidance, agent config, hooks, workflow scripts, settings, templates, or cross-runtime
   support files. Implementer/QA subagents may read those files only when the orchestrator handoff
   names the exact path. QA may read `.claude/skills/playwright-cli/**` for Playwright spec work.

## Agent Roles

| Agent | Responsibility |
|---|---|
| `orchestrator` | Coordinates the plan/challenge loop and routes only the required implementer/QA agents; no planning, no MCP |
| `planner` | Defines the slice, fetches MCP rules, writes feature memory, emits the Agent Plan, and asks the user when info is incomplete |
| `challenger` | Challenges the plan as a gang of adversarial personas and returns an aggregate acceptance percentage (90 percent gate); read-only |
| `backend-developer` | Implements backend code and tests from feature memory; no MCP access |
| `frontend-developer` | Implements frontend code and tests from feature memory; no MCP access |
| `qa` | Reviews the slice, writes/heals Playwright story tests when needed, and returns `APPROVED` or `BLOCKED` |

The orchestrator runs every request through the `planner` -> `challenger` loop before routing
implementation. The challenger scores the plan against a 7-persona panel; all challenges stop only
when acceptance is at least 90 percent. If the loop hits its round cap or the planner/challenger
flags missing information, the orchestrator asks the user and holds planning in plan mode.

Routing is conditional. Backend-only work skips frontend. Frontend-only work skips backend.
Docs/config/copy/minimal changes can route straight to QA review. Foundation work is one
cross-cutting monorepo slice when it touches repo layout, root manifests, bootstrap scripts,
workspace config, or both app roots.

Slice by business feature, not by layer. Write one `slice.md` per business feature (never split a
single feature into scaffold, endpoint, CRUD, page, and test slices). When features depend on each
other, keep them separate and link the ordering through each slice's `## Dependencies`.

## Feature Memory Contract

The planner reads `.claude/templates/template-routing.md`, loads only the needed category
templates, then writes:

- One `feature-memory/<feature>/slice.md` per business feature.
- The single global `feature-memory/rules.md`, one block per guideline slug, reused across every
  feature and never split by category. There is no per-slice `rules.md`.

Each `slice.md` links the rest of the plan through a `## Dependencies` section: `Depends on:` lists
the sibling feature slices it needs first, and `Rules:` lists the guideline slugs it draws on (each
defined as a block in `feature-memory/rules.md`). Every block in `feature-memory/rules.md` must cite
`Source: get_guideline("<slug>")`, and the orchestrator sequences features by their `Depends on:` graph.

Full slices must include `Status`, `Request`, `Slice Boundary`, `Dependencies`, `Do Not Touch`,
`Implementation Plan`, `Acceptance Criteria`, `QA Handoff`, and provenance. User-facing slices also
need `E2E Test Stories`, with each row mapped to one Playwright `test(...)`. Acceptance criteria must
use stable `AC-###` IDs, `Test Coverage` must map every criterion to backend/frontend-unit/E2E/harness
tests, and user-facing slices must include `e2e-coverage.json` mapping initial-prompt user stories
to Playwright tests.

Do not create role-specific feature-memory directories such as `00-shared/`, `backend/`,
`frontend/`, or `qa/`; rules live in the single global `feature-memory/rules.md`, never split by
category. Do not put validator allow-lists in feature memory.

## Deterministic Enforcement

Hooks in `.claude/hooks/` are registered by `.claude/settings.json`. They own formatting,
forbidden edits/reads, MCP scope, commit secret checks, changed-file formatting, and developer stop
gates.

Workflow scripts own mechanical review:

| Check | Command |
|---|---|
| Full workflow doctor | `python scripts/validate/doctor.py --root .` |
| All workflow validators | `python scripts/validate/workflow.py --root .` |
| Root/agent/template guidance | `python scripts/validate/agent-guidance.py --root .` |
| Feature memory contract | `python scripts/validate/feature-memory.py --root .` |
| Feature memory compaction | `python scripts/validate/compaction.py --root .` |
| Hook registration and smoke paths | `python scripts/validate/hook-registration.py --root .` |
| Playwright story contracts | `python scripts/validate/playwright-stories.py --root .` |
| Acceptance/test coverage mapping | `python scripts/validate/test-coverage.py --root .` |
| Initial-prompt E2E coverage mapping | `python scripts/validate/e2e-coverage.py --root .` |
| Backend contract | `python scripts/validate/backend.py --root .` |
| Frontend contract | `python scripts/validate/frontend.py --root .` |
| QA contract | `python scripts/validate/qa.py --root .` |
| Ownership / Do Not Touch | `python scripts/validate/ownership.py --root . --agent <agent> --slice <slice.md>` |
| Deterministic gate evidence | `python scripts/validate/gate.py --root . --slice feature-memory/<slice>/slice.md` |

Hooks run the applicable script checks automatically. `validate-tools` runs inside the developer
stop hook; it is not a QA step. QA evidence must be machine-readable `qa-evidence.json`, generated
by the gate runner, with command/cwd/exit-code/timestamp/output-path records, successful
`docker compose up` evidence when `docker-compose.yml` exists, and backend/frontend unit coverage
at or above 80 percent.

## MCP Budget

- Prefer existing `feature-memory/`, repo files, tests, and prior handoffs.
- The planner may call `get_metadata()` once per slice only when routing does not identify the
  needed slugs. No other agent calls MCP.
- Fetch only specific guidelines required for the slice.
- Never call broad context tools such as `get_all_context` for normal feature work.
- If a downstream agent lacks context, it asks the orchestrator once for a targeted update; the
  orchestrator routes back through the planner. If still blocked, it returns `ESCALATE` or `BLOCKED`.
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
type-check, test, and migration commands in feature memory.

## Environment

Variables go in `.env` files, which are gitignored. Document required keys in `.env.example` when a
slice introduces configuration.
