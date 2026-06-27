# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Stack

- **Backend**: Python / FastAPI - Clean Architecture / DDD
- **Frontend**: Next.js 15 - App Router, Server Components, Server Actions, daisyUI
- **Migrations**: Alembic
- **Python package manager**: uv

## Two rules, no exceptions

**1. Use guidelines through feature-slice memory.**
The `fullstack-guidelines` MCP server is the source of truth for what code should look like, but MCP results are expensive because they stay in context. The orchestrator owns guideline discovery for each feature slice: fetch the complete set of specific slugs needed for the slice once, write the applicable rules into `.claude/feature-memory/<slice>/` (per-role files), and pass the relevant file to each downstream agent. Developer, tester, and QA agents read the feature memory first and must not refetch guideline text themselves.

**2. Route every request through the agent system.**
Do not implement features directly. Invoke the right agent for the work.

## Agents

| Agent | Responsibility |
|---|---|
| `orchestrator` | Scopes the request, resolves guideline slugs, writes feature memory, routes to the right agent |
| `backend-developer` | FastAPI / Python / DB / migrations / async / config; no MCP access |
| `frontend-developer` | Next.js / components / forms / Server Actions / RBAC UI; no MCP access |
| `tester` | Writes and runs focused backend/frontend tests for the feature slice |
| `e2e-explorer` | Drives the running app in a real browser, explores user-facing flows, logs bugs as structured findings; never edits code |
| `qa` | Code review, E2E coverage audit, `validate-tools` CLI validators, merge decision |

**Routing is conditional**: `orchestrator` invokes only the agents needed for the slice. Backend-only work skips frontend. Frontend-only work skips backend. The `e2e-explorer` runs only on user-facing slices (it needs a UI to drive). Docs/config-only and trivial non-behavior changes can go straight to QA.

The orchestrator has two modes and must use exactly one per response:

- Plan Mode: create/update feature memory and Agent Plan.
- Route Mode: emit one tiny role-specific handoff from an existing plan.

Start every feature by invoking the `orchestrator`. Agents never communicate directly with each other; the main thread is the hub.

## MCP budget rules

- Prefer existing local context: `.claude/feature-memory/<slice>/`, repository files, tests, and prior agent handoffs.
- The orchestrator may call `get_metadata()` once per feature slice only when the needed slugs are not already known from existing feature memory or `.claude/guideline-routing.md`.
- Fetch only the specific guidelines required by the current slice. Never call broad context tools such as `get_all_context` for normal feature work.
- When downstream agents lack guideline context, they must ask the orchestrator for more context instead of independently browsing the MCP server. The orchestrator then does one targeted MCP update for the existing slice, covering all related missing rule categories, and either updates `.claude/feature-memory/<slice>/` or sends a richer handoff to the subagent.
- If a downstream agent would need to guess, infer from general knowledge, or proceed best-effort, it must stop and ask the orchestrator for targeted context for the existing slice.
- Each subagent may request targeted orchestrator context once per slice. If still blocked after one update, it returns `ESCALATE` or `BLOCKED`; the orchestrator must improve the plan instead of starting repeated context loops.
- Validators are QA-only final-gate tools, run via `validate-tools <command>`. QA may run only validators explicitly allowed in the feature memory `QA Handoff` or orchestrator `Agent Plan`; do not run the full validator suite by default. Allowed validators must be exact CLI commands, such as `validate-tools secrets` or `validate-tools run`.
- Keep feature memory compact: active slice memory under 150 lines, each role handoff under 25 lines, guideline summaries as rules only.
- Keep only three detailed QA-approved active slice memories. Before QA-approved slice 4, 7, 10, and so on, the orchestrator compacts the previous three QA-approved slices into one review-only historical summary under `.claude/feature-memory/history/`. Blocked, in-progress, unreviewed, and QA-rejected slices stay active and detailed.
- Use conditional routing. Invoke only the agents needed for the slice; do not run the full backend -> frontend -> tester -> e2e-explorer -> qa flow unless the slice is fullstack and user-facing.
- The `e2e-explorer` never browses MCP and never edits application code. When it returns `E2E_BUGS_FOUND`, the orchestrator routes each fix to the suspected owner, then re-invokes the explorer to confirm. A user-facing slice is not done while `block:` findings remain in `e2e/report.md`.
- Plan before routing. The orchestrator must not mix Plan Mode and Route Mode in the same response.
- Handoffs must be tiny: feature memory path, role-specific section, changed file list, and exact task.
- Every slice memory must include `Status`, `Do Not Touch`, and `QA Handoff -> Allowed validators`. Empty allowed validators means QA runs no MCP validators.
- Commit messages may cite only slugs already present in feature memory. Agents must not expand commit slugs with fresh guideline work.
- If QA wants an unlisted validator, it must ask the orchestrator to update `Allowed validators` before running it.
- Minimal Slice Mode is mandatory for docs, config-only, copy, one-file non-behavior changes, and dependency-free fixes.

## Development commands

> Update once the project scaffold is in place.

| Task | Command |
|---|---|
| Bootstrap full toolchain (macOS/Linux) | `bash scripts/bootstrap.sh` |
| Bootstrap full toolchain (Windows) | `powershell -ExecutionPolicy Bypass -File scripts\bootstrap.ps1` |
| Install deps (backend) | `uv sync` |
| Install validators (QA) | `uv tool install validate-tools` |
| Install deps (frontend) | `pnpm install` |
| Run backend | `uvicorn app.main:app --reload` |
| Run frontend | `pnpm dev` |
| Lint / format | `ruff check . && ruff format .` |
| Type-check (backend) | `mypy src/` |
| Type-check (frontend) | `pnpm tsc --noEmit` |
| Tests (backend) | `pytest` / `pytest tests/path/test_file.py::test_name` |
| Tests (frontend) | `pnpm test` |
| Migrations | `alembic upgrade head` / `alembic revision --autogenerate -m "..."` |

## Environment

Variables go in `.env` (gitignored). Document required keys in `.env.example`. For config changes, the orchestrator should add the relevant MCP-backed configuration rule to feature memory before routing.
