# AGENTS.md

This file provides guidance to Codex when working with code in this repository.

## Stack

- **Backend**: Python / FastAPI - Clean Architecture / DDD
- **Frontend**: Next.js 15 - App Router, Server Components, Server Actions, daisyUI
- **Migrations**: Alembic
- **Python package manager**: uv

## Four rules, no exceptions

**1. Use guidelines through feature-slice memory.**
The `fullstack-guidelines` MCP server is the source of truth for what code should look like, but MCP results are expensive because they stay in context. The orchestrator owns guideline discovery for each feature slice: fetch the complete set of specific slugs needed for the slice once, write the applicable rules into `.codex/feature-memory/<slice>/` (per-role files), and pass the relevant file to each downstream agent. Developer and QA agents read the feature memory first and must not refetch guideline text themselves.

**2. Route every request through the agent system.**
Do not implement features directly. Invoke the right agent for the work.

**3. Keep Claude and Codex guidance aligned.**
`CLAUDE.md` and `AGENTS.md` are paired root entrypoints and must stay at least 90% similar in structure and operational guidance. When one file changes, update the other in the same change unless the difference is strictly runtime-specific (`.claude/` versus `.codex/`, Claude naming versus Codex naming, or tool availability). Keep `.claude/` and `.codex/` support files mirrored by role, hook, template, and guideline-routing purpose.

**4. Block subagent reads of agent infrastructure.**
Only the main thread and `orchestrator` may read root guidance, agent configuration, hooks, workflow scripts, or cross-runtime support files. Non-orchestrator subagents must not open, search, or inspect `CLAUDE.md`, `AGENTS.md`, `.claude/`, `.codex/`, `scripts/`, hook files, settings files, or agent templates unless the orchestrator handoff names the exact file path as required task input. If a subagent needs that context, it must stop and return `ESCALATE` for orchestrator-owned context instead of reading the file directly.

## Agents

| Agent | Responsibility |
|---|---|
| `orchestrator` | Scopes the request, resolves guideline slugs, writes feature memory, routes to the right agent |
| `backend-developer` | FastAPI / Python / DB / migrations / async / config **and the slice's tests**; no MCP access |
| `frontend-developer` | Next.js / components / forms / Server Actions / RBAC UI **and the slice's tests**; no MCP access |
| `e2e-explorer` | Drives the running app in a real browser, explores user-facing flows, logs bugs as structured findings; never edits code |
| `qa` | Judgment-only merge review: architecture/contract compliance, Do-Not-Touch, E2E adequacy, merge decision |

**Routing is conditional**: `orchestrator` invokes only the agents needed for the slice. Backend-only work skips frontend. Frontend-only work skips backend. The `e2e-explorer` runs only on user-facing slices (it needs a UI to drive). Docs/config-only and trivial non-behavior changes can go straight to QA.

**Foundation is cross-cutting**: repo folders, root manifests, bootstrap scripts, workspace config,
and app-root scaffolds are monorepo foundation work, not backend-only work. The orchestrator must
plan these as one fullstack foundation slice with shared repo-structure memory, then route backend
and frontend foundation tasks from the same structure contract so both agents know the expected
monorepo shape.

## Deterministic gates (hooks + `validate-tools`)

The mechanical checks are enforced by hooks in `.codex/hooks/` (registered in `.codex/hooks.json`, with hooks enabled in `.codex/config.toml`), so they always run regardless of what an agent remembers:

- **`auto-format.sh`** (`PostToolUse`) formats every edited file (`ruff` / `prettier`).
- **`verify-subagent.sh`** (`SubagentStop` for `backend-developer` / `frontend-developer`) runs lint, type-checks, `validate-tools run`, and the test suite when a developer finishes, and **blocks its return until they pass**. This is where compliance and tests are enforced — not in QA.
- **`guard-*.sh`** (`PreToolUse`) block forbidden commands, edits, and infrastructure reads; enforce that only the orchestrator calls MCP; and keep the e2e-explorer write scope under `e2e/`.

Because of this, QA reviews judgment only (does the design hold, do the tests cover the right behavior, is E2E adequate, can it merge) and never reproduces the mechanical gate. See `.codex/hooks/README.md`.

The orchestrator has two modes and must use exactly one per response:

- Plan Mode (primary): create/update feature memory and the Agent Plan. The Agent Plan table is the full execution sequence — each row names the agent, files to read, do-not-touch scope, and stop condition.
- Route Mode (exception): emit one tiny role-specific handoff. Used only when the orchestrator is re-invoked to resolve an `ESCALATE`/`BLOCKED` return or to fan out an E2E `block:`/`question:` fix — not for normal happy-path steps.

Start every feature by invoking the `orchestrator`. The main thread is the hub: it drives the Agent Plan table row by row, invoking each agent directly, and returns to the orchestrator only for escalations and E2E-bug fan-out. Agents never communicate directly with each other.

## MCP budget rules

- Prefer existing local context: `.codex/feature-memory/<slice>/`, repository files, tests, and prior agent handoffs.
- The orchestrator may call `get_metadata()` once per feature slice only when the needed slugs are not already known from existing feature memory or `.codex/guideline-routing.md`.
- Fetch only the specific guidelines required by the current slice. Never call broad context tools such as `get_all_context` for normal feature work.
- When downstream agents lack guideline context, they must ask the orchestrator for more context instead of independently browsing the MCP server. The orchestrator then does one targeted MCP update for the existing slice, covering all related missing rule categories, and either updates `.codex/feature-memory/<slice>/` or sends a richer handoff to the subagent.
- If a downstream agent would need to guess, infer from general knowledge, or proceed best-effort, it must stop and ask the orchestrator for targeted context for the existing slice.
- Each subagent may request targeted orchestrator context once per slice. If still blocked after one update, it returns `ESCALATE` or `BLOCKED`; the orchestrator must improve the plan instead of starting repeated context loops.
- `validate-tools` validators are **not an agent step**. They run inside the `verify-subagent.sh` hook when a developer finishes. Do not write an allowed-validators list in feature memory, do not ask QA to run validators.
- Correctness beats compactness. Do not omit provenance, required rules, or blocking uncertainty to satisfy a token budget. Keep handoffs concise, but full feature memory may exceed 150 lines when needed to preserve MCP-backed decisions.
- Keep only three detailed QA-approved active slice memories. Before QA-approved slice 4, 7, 10, and so on, the orchestrator compacts the previous three QA-approved slices into one review-only historical summary under `.codex/feature-memory/history/`. Blocked, in-progress, unreviewed, and QA-rejected slices stay active and detailed.
- Use conditional routing. Invoke only the agents needed for the slice; do not run the full backend -> frontend -> e2e-explorer -> qa flow unless the slice is fullstack and user-facing.
- The `e2e-explorer` never browses MCP and never edits application code. When it returns `E2E_BUGS_FOUND`, the orchestrator routes each fix to the suspected owner, then re-invokes the explorer to confirm. A user-facing slice is not done while `block:` findings remain in `e2e/report.md`.
- Plan before routing. The orchestrator must not mix Plan Mode and Route Mode in the same response.
- Handoffs must be tiny: feature memory path, role-specific section, changed file list, and exact task.
- Handoffs must also list every agent-infrastructure file a non-orchestrator subagent may read. If a file is not listed, the subagent treats it as blocked.
- Every task file must include task provenance: each concrete file path, directory-tree choice, dependency, command, acceptance criterion, and test case must map to a rule in that role's `rules.md` by slug. If the orchestrator cannot cite the slug, it must mark the task `BLOCKED` and ask for targeted MCP context instead of routing it.
- Every slice memory must include `Status` and `Do Not Touch`. The QA Handoff carries review focus and blocking risks only — no validator list.
- Commit messages may cite only slugs already present in feature memory. Agents must not expand commit slugs with fresh guideline work.
- Minimal Slice Mode is mandatory for docs, config-only, copy, one-file non-behavior changes, and dependency-free fixes.

## Development commands

> Update once the project scaffold is in place.

| Task | Command |
|---|---|
| Bootstrap full toolchain (macOS) | `bash scripts/bootstrap.sh` |
| Bootstrap full toolchain (Windows) | `powershell -ExecutionPolicy Bypass -File scripts\bootstrap.ps1` |
| Connect clone to your own repo (macOS) | `bash scripts/init-project.sh` |
| Connect clone to your own repo (Windows) | `powershell -ExecutionPolicy Bypass -File scripts\init-project.ps1` |
| Install deps (backend) | `uv sync` |
| Install validators (run by the gate hook) | `uv tool install validate-tools` |
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
