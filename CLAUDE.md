# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Stack

- **Backend**: Python / FastAPI — Clean Architecture / DDD
- **Frontend**: Next.js 15 — App Router, Server Components, Server Actions, daisyUI
- **Migrations**: Alembic
- **Python package manager**: uv

## Two rules, no exceptions

**1. Consult the guidelines before writing any code.**
The `fullstack-guidelines` MCP server is connected and is the authoritative source for every architectural pattern. Call `get_metadata()` first, fetch the relevant guideline, read its "Use when" line, then write code. Cite the slugs in every commit.

**2. Route every request through the agent system.**
Do not implement features directly. Invoke the right agent for the work.

## Agents

| Agent | Responsibility |
|---|---|
| `orchestrator` | Scopes the request, resolves guideline slugs, routes to the right agent |
| `backend-developer` | FastAPI / Python / DB / migrations / async / config |
| `frontend-developer` | Next.js / components / forms / Server Actions / RBAC UI |
| `tester` | DoD compliance, automated test execution, structure validation |
| `qa` | Code review, E2E coverage audit, MCP validators, merge decision |

**Default flow**: `orchestrator` → `backend-developer` and/or `frontend-developer` → `tester` → `qa`

Start every feature by invoking the `orchestrator`. Agents never communicate directly with each other — the main thread is the hub.

## Development commands

> Update once the project scaffold is in place.

| Task | Command |
|---|---|
| Install deps (backend) | `uv sync` |
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

Variables go in `.env` (gitignored). Document required keys in `.env.example`. See guideline `backend/24-configuration-layers`.
