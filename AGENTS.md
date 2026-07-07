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

2. Route work through the agent system directly from the main thread.
   Product or feature work is sequenced by the main thread itself, without a separate orchestrator
   agent: `product-owner` proposes PRD options and writes the selected PRD set, `business-challenger`
   scores the PRDs, `software-architect` writes ADRs and MCP-backed feature slices, and
   `technical-challenger` scores the ADR/slice plan. The loop repeats until both challengers accept
   at **at least 90 percent** (capped at 3 rounds, then the user is asked). Only then does the main
   thread execute the Agent Plan rows directly, handling `ESCALATE`, `BLOCKED`, or QA finding fan-out
   itself instead of returning to a coordinator. See `## Orchestration (Main Thread)` below for the
   full routing graph.
   Incomplete information is always asked back to the user, with planning held in plan mode until
   the answer arrives.

3. Keep Claude and Codex guidance mirrored.
   `CLAUDE.md` and `AGENTS.md` must stay structurally aligned. `.claude/` and `.codex/` support
   files must stay mirrored by role, hook, template, and guideline-routing purpose, except for
   runtime-specific names and tool syntax.

4. Block subagent reads of agent infrastructure.
   Only the main thread and the coordination tier (`product-owner`, `software-architect`,
   `business-challenger`, `technical-challenger`) may read root guidance, agent config, hooks,
   workflow scripts, settings, or cross-runtime support files.
   Implementer/QA subagents may read those files only when the main thread's handoff names the exact
   path. Any subagent may read `.codex/templates/**` and `.codex/skills/**` - reference material,
   not agent infrastructure.

5. Every access-control or trigger validation gets a real backend implementation, never a stub.
   Any authentication, authorization/RBAC, or trigger-condition check named in a PRD, ADR, or slice
   must ship working backend enforcement code - even a deliberately simple first version - before
   the slice is done. "The user will improve this later" is a reason to keep the check minimal, not
   a reason to fake it, `TODO` it, hardcode `True`/allow-all, or defer it to a later slice while the
   feature ships. If the slice's real permission model is not yet decided, that is a product gap:
   `software-architect` returns `NEEDS-INPUT` rather than let a developer ship an unenforced check.

6. Testability gates sequencing; validation gates only cover started work.
   `software-architect` does not sequence a dependent slice's implementation on top of a
   prerequisite that cannot be tested in the current environment (e.g. needs a live external
   system unavailable here). Mark the dependent chain `State: STAGED` in `slice.md`'s `## Staging`
   section instead of building forward on an unverified foundation; the main thread asks the
   user once, at the next MVP checkpoint (not per-slice), whether it is time to include staged work
   - it does not ask silently or repeatedly. Deterministic validators and QA evidence requirements
   apply only to `Test Coverage`/`E2E Test Stories` rows marked `in-progress` or `done`; a row
   explicitly marked `not-started` is not a failure and must not be reported as one.

## Agent Roles

| Agent | Responsibility |
|---|---|
| `product-owner` | Offers opinionated PRD options, writes complete PRDs, defines users/use cases/outcomes/requirements, and asks product questions; no MCP |
| `business-challenger` | Challenges PRD problem clarity, target users, use cases, scope, outcomes, requirements, and business risk; read-only |
| `software-architect` | Converts accepted PRDs into ADRs and MCP-backed feature slices, writes `memory/rules.md`, and emits the Agent Plan |
| `technical-challenger` | Challenges ADRs, provenance, architecture, contracts, feasibility, coverage, operations, and security; read-only |
| `backend-developer` | Implements backend code and tests from memory; no MCP access |
| `frontend-developer` | Implements frontend code and tests from memory; no MCP access |
| `qa-checker` | Writes/heals Playwright story tests when needed, runs them, and produces qa-evidence.json/e2e-coverage.json; no MCP access |
| `qa-challenger` | Reviews qa-checker's evidence and the slice, and returns the final `APPROVED` or `BLOCKED` merge verdict; read-only |

The main thread runs product or feature work through
`product-owner` -> `business-challenger` -> `software-architect` -> `technical-challenger` before
routing implementation, directly - there is no separate orchestrator agent. The product-owner
starts with 2-3 concrete PRD direction options when the request allows different product shapes;
the user picks before full PRDs are written. `business-challenger` scores its 6-persona panel and
`technical-challenger` scores its 8-persona panel; all challenges stop only when both acceptance
scores are at least 90 percent. If the loop hits its round cap or any coordination agent flags
missing information, the main thread asks the user and holds planning in plan mode.

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

## Orchestration (Main Thread)

There is no separate orchestrator agent. The main thread coordinates and routes directly: it does
not scope requests, fetch guidelines, write PRDs, write ADRs, write memory, challenge plans, or
write application code itself - those stay owned by `product-owner`, `software-architect`,
`business-challenger`/`technical-challenger`, the developers, and QA. The main thread's job is to
sequence which of those agents runs next, gate on the same 90 percent/3-round rules that always
applied, and invoke each agent directly (subagents cannot invoke each other).

The main thread operates in one of two modes at a time, and does not mix them in the same step:

- **Coordinate Mode**: sequence the PRD/ADR/slice challenge loop and, once both challenge gates
  pass, execute the implementation routing.
- **Route Mode**: resolve an `ESCALATE`/`BLOCKED` return, or fan out a `qa-challenger`
  `block:`/`question:` finding to the suspected owner and re-queue QA for confirmation.

### Plan-Loop Routing

Every request starts here, before any implementer/QA agent is ever invoked. This is the full
planning graph, including where each feedback path goes:

| Step | Agent | Reads | On success/PASS -> | On REVISE / NEEDS-INPUT / BLOCKED -> |
|---|---|---|---|---|
| 1. Product options | `product-owner` | the user's request | (user picks a direction) -> step 2 | `NEEDS-INPUT` -> ask the user, stay in plan mode |
| 2. PRD | `product-owner` | selected direction | `business-challenger` (step 3) | `NEEDS-INPUT` -> ask the user, stay in plan mode |
| 3. Business challenge | `business-challenger` | PRDs under `memory/PRD/<purpose>/prd.md` | `software-architect` (step 4) if PASS | `REVISE` -> back to `product-owner` (step 2), then `software-architect` too if technical sections must be reconciled, then re-run both challengers; `NEEDS-INPUT` -> ask the user |
| 4. Architecture | `software-architect` | accepted PRDs | `technical-challenger` (step 5) | `NEEDS-INPUT` -> ask the user; `BLOCKED` (no guideline can support it) -> ask the user |
| 5. Technical challenge | `technical-challenger` | ADRs, slices, Agent Plan | Execution Routing (below) once **both** gates are PASS | `REVISE` -> back to `software-architect` (step 4), re-run at least `technical-challenger`, and re-run `business-challenger` too if product-owned sections changed; `NEEDS-INPUT` -> ask the user |

Gating rules:

- Proceed to Execution Routing only when **both** `business-challenger` and `technical-challenger`
  score `PASS` (each acceptance >= 90 percent) in the same round.
- `NEEDS-INPUT` from any planning or challenge agent stops the loop immediately: surface the open
  questions to the user and stay in plan mode until answered, then restart at the step the answer
  unblocks - do not keep advancing other steps around it.
- **Round cap**: at most **3** full PRD/ADR/slice challenge rounds. If both gates have not passed
  after the third round, stop and ask the user to resolve the outstanding findings; do not keep
  looping or route implementation.
- Record both final acceptance percentages and the round count in a `## Coordinate Handoff` block
  (below) each time a business-challenge or technical-challenge step runs; a hook uses this block to
  verify the round count deterministically.

### Coordinate Handoff

Before invoking the next Plan-Loop step, state it in this format, then invoke that agent directly:

```md
## Coordinate Handoff

- Step: product-options | prd | business-challenge | architecture | technical-challenge | needs-input | route
- Agent: product-owner | software-architect | business-challenger | technical-challenger | (user) | <implementer/qa-checker/qa-challenger>
- Artifacts: `memory/PRD/<purpose>/prd.md`, `memory/ADR/<purpose>/adr.md`, `memory/feature/<feature-slice>/slice.md`
- Round: <n> of 3
- Reads: linked PRDs/ADRs/slices/rules where available (+ challenge findings when revising)
- Stop condition: <what "done" looks like for this step>
```

### Execution Routing

Once both Plan-Loop gates pass, route implementation feature by feature. Sequence the features by
their `## Dependencies` -> `Depends on:` graph, and within each feature invoke the implementer/QA
rows from the software-architect's `## Agent Plan` in order, honoring the request-shape table
below. The software-architect's plan defines the rows; the main thread sequences and gates them.

If a feature's `## Status` is `STAGED` (a dependency can't be tested in this environment - see rule
6), do not route it or anything depending on it. Ask the user once, at the next MVP checkpoint (all
other routable work finished), whether to include staged work now - not per-slice and not silently.

```md
## Agent Plan

| Invocation | Agent | Reads |
|---|---|---|
| 1 | backend-developer | `slice.md` + linked `rules.md` slugs |
| 2 | frontend-developer | `slice.md` + linked `rules.md` slugs |
| 3 | qa-checker | `slice.md` + linked `rules.md` slugs + `frontend/e2e/**` |
| 4 | qa-challenger | `slice.md` + linked `rules.md` slugs + `frontend/e2e/**` + Playwright output |
```

For each row, state the `Do not touch` scope and `Stop condition`. `qa-challenger` decides the
verdict; `qa-checker` persists the terminal `QA APPROVED` / `QA BLOCKED` state in `slice.md` once
the main thread relays that confirmed verdict back to it.

Which rows apply depends on what the request touches - this is the feedback graph for execution,
not just the forward path:

| Request touches | Route to | On escalation/BLOCKED -> |
|---|---|---|
| Monorepo foundation / repo layout / root tooling spanning both app roots | backend-developer foundation -> frontend-developer foundation -> qa-checker -> qa-challenger | developer `ESCALATE` -> `product-owner` (product gap) or `software-architect` (technical gap); `qa-challenger` `BLOCKED` -> suspected owner, then re-confirm |
| Backend behavior only | backend-developer(s) -> qa-checker -> qa-challenger | same as above |
| Frontend behavior only | frontend-developer -> qa-checker -> qa-challenger | same as above |
| Backend + frontend | backend-developer(s) -> frontend-developer -> qa-checker -> qa-challenger | same as above |
| Review / security / PR hygiene | qa-challenger | `BLOCKED` -> suspected owner, then re-confirm |
| Docs / config-only / no behavior change | qa-challenger (no Playwright work for qa-checker to do) | `BLOCKED` -> suspected owner, then re-confirm |

Every request still starts with Plan-Loop Routing before these rows are routed.

### Route Mode

Use this to resolve an `ESCALATE`/`BLOCKED` return, or to fan out a `qa-challenger`
`block:`/`question:` finding. Handle one at a time. A developer that escalates for missing product
context is routed back through `product-owner`; a developer that escalates for missing technical
guideline context is routed back through `software-architect`.

```md
## Route Handoff

- Agent: <role>
- Memory: `memory/feature/<feature-slice>/slice.md`
- Rules: the slugs the slice links under `## Dependencies` -> `Rules:`, in `memory/rules.md`
- Playwright specs/output: `frontend/e2e/**` and the focused Playwright command/output (qa-checker/qa-challenger follow-up only)
- Depends on: <prior invocation output or "none">
- Do not touch: <files/behaviors out of scope>
- Stop condition: <what "done" looks like>
```

### Orchestration Rules

- Do not plan, challenge, or write memory in place of a specialized agent - invoke the owning
  agent instead of doing its work directly.
- Do not call the guidelines MCP server. Only the `software-architect` may.
- Enforce both 90 percent challenge gates and the 3-round cap. Never route implementation unless
  both challenge gates pass.
- When `NEEDS-INPUT` surfaces or the round cap is hit, ask the user and stay in plan mode; do not
  guess the missing decision.
- Sequence features by their `Depends on:` graph, then invoke each feature's `## Agent Plan` rows in
  order; honor the Execution Routing table.
- If a developer escalates for missing context, route product questions through `product-owner` and
  technical guideline gaps through `software-architect`, then continue. Each agent gets one
  escalation per feature.
- Deterministic checks are hooks, not agent steps. Do not write an allowed-validators list, do not
  route a tester, and do not ask qa-checker/qa-challenger to run validators.
- When `qa-challenger` returns `BLOCKED`, route each `block:`/`question:` finding to the suspected
  owner (`backend-developer`/`frontend-developer` for app bugs, `qa-checker` for stale/weak test
  code), then re-invoke `qa-checker` to update evidence and `qa-challenger` to confirm the fix and
  make the final merge decision.
- Nothing merges without a green deterministic gate and `State: QA APPROVED` in `slice.md`.

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
block in `memory/rules.md` must cite `Source: get_guideline("<slug>")`, and the main thread
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
- If a downstream agent lacks context, it asks the main thread once for a targeted update; the
  main thread routes back through the product-owner for product gaps or the software-architect for
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
