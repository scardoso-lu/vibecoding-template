# Feature Memory — Directory Template

The orchestrator reads this file at the start of Plan Mode and follows every section's format and content rules exactly.

> **No implementation code in feature memory.** Task files are specifications: entity field lists, endpoint signatures, directory trees, business rules, and prose descriptions. Sub-agents own all implementation. The orchestrator fills in domain-specific content; sub-agents derive implementation patterns from their `rules.md`.

```
.codex/feature-memory/<slice>/
  00-shared/                   # fullstack only — omit for backend-only or frontend-only
    api-contract.md            # every endpoint both stacks must agree on
    cross-stack.md             # error envelope, pagination shape, TypeScript↔Python type mappings
    repo-structure.md          # monorepo foundation only: root layout and path ownership

  backend/
    rules.md                   # all backend MCP rules (incl. testing) — read by every backend invocation
    task-foundation.md         # backend root/package/tooling plus base infrastructure
    task-<domain>.md           # one file per domain: entity + repo + use cases + routes + Tests

  frontend/
    rules.md                   # all frontend MCP rules (incl. testing)
    task-foundation.md         # monorepo foundation only: frontend root/package/tooling
    task.md                    # pages, services, server actions + Tests
    components.md              # only when the feature has more than three components

  # No tests/ directory and no tester role. Each developer authors the tests for its slice
  # (see the Tests section in each task file). Lint, types, validate-tools, and the suite run
  # automatically as the SubagentStop gate hook, not as memory-driven agent steps.

  e2e/                         # user-facing slices only — omit for backend-only or non-behavior changes
    rules.md                   # exploratory E2E MCP rules
    task.md                    # flows to explore, acceptance criteria, app launch + seed/credential notes
    report.md                  # written by e2e-explorer — structured bug findings (not authored by orchestrator)
    artifacts/                 # written by e2e-explorer — screenshots, console/network captures

  qa/
    rules.md                   # QA MCP rules
    checklist.md               # review focus, blocking risks, E2E coverage (no validator list — hooks run them)
```

---

## `00-shared/`

> Only for fullstack features. Contains only content multiple agents must agree on — if one agent gets it wrong, another's work breaks. Never put guidelines here (those go in role `rules.md`). Never put domain model details here (those go in `backend/task-<domain>.md`); the frontend only needs the TypeScript shapes from `cross-stack.md`. For monorepo foundation slices, `repo-structure.md` is mandatory and is the shared source of truth for root layout decisions.

### `00-shared/api-contract.md`

```md
# <slice> — API Contract

## <Resource>

### POST /<path>
- Request: `{ field: type, … }`
- Response 201: `{ field: type, … }`
- Response 422: `{ detail: string }`

### GET /<path>
- Query params: `cursor`, `page_size`, `sort`
- Response 200: `{ items: T[], next_cursor: string | null, prev_cursor: string | null, page_size: number }`
- Response 404: `{ detail: string }`

### PATCH /<path>/{id}
- Request: `{ field?: type, … }`
- Response 200: `{ field: type, … }`

### DELETE /<path>/{id}
- Response 204: (no body)
```

### `00-shared/cross-stack.md`

```md
# <slice> — Cross-Stack Contracts

## Error envelope
Both stacks use: `{ detail: string }`
- 404 Not Found
- 422 Validation Error
- 500 Internal Server Error

## Pagination envelope
`Page[T]` shape: `{ items: T[], next_cursor: string | null, prev_cursor: string | null, page_size: number }`

## TypeScript types
Exact TypeScript interfaces the frontend uses, mirroring backend DTOs:

type <ResourceStatus> = "<value1>" | "<value2>" | "<value3>"

interface <ResourceDto> {
  id: string
  field: type
  created_at: string
  updated_at: string
}
```

### `00-shared/repo-structure.md`

> Required for monorepo foundation slices. Omit for normal feature slices unless root layout changes.

```md
# <slice> — Monorepo Structure

## Status
- State: active | DONE

## Root layout
- `<backend-root>/` — backend app root and package boundary
- `<frontend-root>/` — frontend app root and package boundary
- `<shared-path>/` — shared scripts/config/docs, if any

## Ownership
- Backend-developer owns: <backend directories, backend manifests, backend tests/tooling>
- Frontend-developer owns: <frontend directories, frontend manifests, frontend tests/tooling>
- Shared/root files: <exact files, owner for creation, and which later agents may read or edit>

## Workspace contracts
- Package manager boundaries: <uv / pnpm workspace expectations>
- Bootstrap commands: <root and per-app commands>
- Environment files: <which `.env.example` keys belong to which app>
- Do Not Touch: <repo paths or behaviors outside the foundation slice>

## Provenance
- <each root-level layout decision> → `<slug>`
```

---

## `backend/`

> `rules.md` is written once per feature and read by every backend invocation. It contains only backend MCP slugs — never frontend or testing rules. Each task file covers exactly one implementation scope; the backend-developer is invoked once per task file.

### `backend/rules.md`

```md
# <slice> — Backend Rules

All rules extracted from `get_guideline()` MCP calls. Every backend invocation reads this file.

## `<slug>`
Source: get_guideline("<slug>") — fetched this session

- Always …
- Never …
- Must …
```

### `backend/task-foundation.md`

> First backend task when backend work exists. For monorepo foundation slices, covers backend root,
> package/tooling setup, shared base infrastructure, and backend tests. No domain entities.

```md
# <slice> — Backend Foundation

## Status
- State: active | DONE   # orchestrator owns this field

## What to build
Backend foundation inside the monorepo structure defined by `00-shared/repo-structure.md`.

## Do Not Touch
- <files / behaviors / contracts out of scope for this task>

## Directory tree
<describe the file and directory structure>

## Depends on
`00-shared/repo-structure.md` for root layout, ownership, package boundaries, and shared config.

## Acceptance Criteria
- [ ] <observable outcome that proves the foundation is in place>

## Commands
<see AGENTS.md — lint, type-check, migration>

## Stop condition
<what "done" looks like for the foundation>
```

### `backend/task-<domain>.md`

> One file per domain. Split whenever a single invocation would cover more than one full domain (entity + repo + use cases + routes).

```md
# <slice> — Backend: <Domain>

## Status
- State: active | DONE   # orchestrator owns this field

## What to build
<Entity> entity + repository + use cases + routes.

## Do Not Touch
- <files / behaviors / contracts out of scope for this task>

## Depends on
`task-foundation.md` complete.

## Domain model
- Entity: `<ClassName>`
- Fields: `field_name: type (nullable / not null)`, …
- Enums: `<EnumName>: value1 | value2 | value3`
- FK: `<field>` → `<table>` CASCADE
- Business rules: <prose description of invariants and constraints>

## Directory tree
<describe the file and directory structure for this domain>

## Use cases
- `<UseCaseName>`: <preconditions, errors raised, return value>

## API endpoints owned by this task
(copy only the relevant rows from `00-shared/api-contract.md`)

## Acceptance Criteria
- [ ] <observable outcome from this domain's scope>

## Tests
> The developer authors these (no tester role). Describe cases only — no test code.
- `tests/unit/use_cases/test_<usecase>.py` — happy path + each error case
- `tests/integration/routes/test_<resource>_routes.py` — each method → status code + scenario

## Commands
<see AGENTS.md — lint, type-check, test>

## Stop condition
<what "done" looks like. The SubagentStop gate runs ruff/mypy/validate-tools/pytest and blocks
the return until green — so "done" means all of those pass.>
```

---

## `frontend/`

> `rules.md` contains only frontend MCP slugs. `task-foundation.md` is created for monorepo foundation slices so the frontend-developer receives the same repo structure context as the backend-developer. `task.md` lists pages, services, and server actions by name and behavior — not by implementation. `components.md` is only created when the feature has more than three components. No JSX or TypeScript implementation bodies anywhere.

### `frontend/rules.md`

```md
# <slice> — Frontend Rules

All rules extracted from `get_guideline()` MCP calls.

## `<slug>`
Source: get_guideline("<slug>") — fetched this session

- Always …
- Never …
- Must …
```

### `frontend/task-foundation.md`

> Required for monorepo foundation slices. Covers frontend scaffold, package/tooling setup, app directory baseline, styling setup, and frontend test setup. It must reference `00-shared/repo-structure.md`; do not let the frontend agent infer the repo layout from backend files.

```md
# <slice> — Frontend Foundation

## Status
- State: active | DONE   # orchestrator owns this field

## What to build
Frontend foundation inside the monorepo structure defined by `00-shared/repo-structure.md`.

## Do Not Touch
- <files / behaviors / contracts out of scope for this task>

## Depends on
`00-shared/repo-structure.md` for root layout, ownership, package boundaries, and shared config.

## Directory tree
<describe the frontend file and directory structure>

## Tooling and app baseline
- Package manager / scripts: <pnpm scripts and expected commands>
- Next.js app root: <routes/layout/loading/error baseline>
- Styling: <Tailwind/daisyUI setup and ownership>
- Tests: <frontend test directories and cases to create>

## Acceptance Criteria
- [ ] <observable outcome that proves the frontend foundation matches the monorepo structure>

## Commands
<see AGENTS.md — type-check, test>

## Stop condition
<what "done" looks like. The SubagentStop gate runs tsc/validate-tools/tests and blocks the
return until green.>
```

### `frontend/task.md`

```md
# <slice> — Frontend Task

## Status
- State: active | DONE   # orchestrator owns this field

## Do Not Touch
- <files / behaviors / contracts out of scope for this task>

## Depends on
Backend complete. API contract: `00-shared/api-contract.md`. Types: `00-shared/cross-stack.md`.

## Routes
- `<route>/page.tsx` — <what it fetches, what it renders>
- `<route>/new/page.tsx` — <shell + form component>
- `<route>/[id]/page.tsx` — <detail page>
- Each segment requires: `loading.tsx`, `error.tsx`, `not-found.tsx`

## Services
`src/services/<domain>.ts`
- `<methodName>(params)` → `<ReturnType>` — cache tag: `<tag>`

## Server Actions
`src/actions/<domain>.ts`
- `<actionName>(params)`: <what it validates, calls, revalidates, and returns>

## Acceptance Criteria
- [ ] <observable outcome in the UI>

## Tests
> The developer authors these (no tester role). Describe cases only — no test code.
- Component / server-action / page-behavior tests for the acceptance criteria
- Scripted Playwright flow(s) when the slice changes user-visible behavior

## Commands
<see AGENTS.md — type-check, test>

## Stop condition
<what "done" looks like. The SubagentStop gate runs tsc/validate-tools/tests and blocks the
return until green.>
```

### `frontend/components.md`

> Only create this file when the feature has more than three components. List component name, props interface, daisyUI variant, and state decisions. No JSX or TypeScript implementation bodies.

```md
# <slice> — Frontend Components

## `<ComponentName>`
- File: `src/components/app/<component>.tsx`
- Type: Server Component | Client Component (reason: <why it needs client>)
- Props: `{ prop: type, … }`
- daisyUI variant: <describe layout intent>
- States required: <which of loading | error | empty | success apply>
- Accessibility: <required aria attributes and label requirements>
```

---

## Tests (no separate role)

There is no `tests/` directory and no tester agent. Testing guideline rules go in each developer's
`rules.md` (e.g. `backend/09-testing`, `frontend/13-e2e-playwright`), and the cases to cover go in
the `Tests` section of each `task.md`. The developer authors and runs them; the SubagentStop gate
hook (`.codex/hooks/verify-subagent.sh`) runs lint, types, `validate-tools`, and the suite on
finish and blocks the return until green.

---

## `e2e/`

> Only for slices that change user-facing behavior — the explorer needs a UI to drive. `rules.md` contains exploratory-E2E MCP slugs only (e.g. `frontend/13-e2e-playwright`, `frontend/14-loading-error-empty-states`, `frontend/19-rbac-permissions`). `task.md` tells the explorer which flows to walk, what "correct" looks like, and exactly how to launch the app and reach a usable state. The explorer writes `report.md` and `artifacts/` itself — the orchestrator does not author them.

### `e2e/rules.md`

```md
# <slice> — E2E Exploration Rules

All rules extracted from `get_guideline()` MCP calls.

## `<slug>`
Source: get_guideline("<slug>") — fetched this session

- Always …
- Never …
- Must …
```

### `e2e/task.md`

```md
# <slice> — E2E Exploration

## Status
- State: active | E2E CLEAN | E2E BUGS FOUND   # orchestrator sets this from the explorer verdict: E2E_CLEAN → E2E CLEAN, E2E_BUGS_FOUND → E2E BUGS FOUND
- Last run: —

## Launch
- Backend: <command + health/ready URL to poll>
- Frontend: <command + base URL>
- Seed data / credentials: <how to reach a usable, authenticated state — never invent these>

## Flows to explore
- <flow>: <happy path + which edges to probe — empty, invalid input, double-submit, refresh mid-flow, unauthorized, loading/error/empty rendering, RBAC-hidden UI>

## Acceptance criteria (observable in the browser)
- [ ] <observable outcome>

## Commands
<see AGENTS.md — run backend, run frontend>

## Do Not Touch
- <files or behaviors the explorer must not change>

## Stop condition
Every listed flow exercised; findings logged to `report.md` with reproducible steps and evidence.
```

---

## `qa/`

> `rules.md` contains QA MCP slugs. `checklist.md` carries review focus and blocking risks — **no validator list** (validators run as the SubagentStop gate hook, not as a QA step). QA is the final judgment gate — nothing merges without a green gate and `State: QA APPROVED`.

### `qa/rules.md`

```md
# <slice> — QA Rules

All rules extracted from `get_guideline()` MCP calls relevant to QA review.

## `<slug>`
Source: get_guideline("<slug>") — fetched this session

- Always …
- Never …
- Must …
```

### `qa/checklist.md`

```md
# <slice> — QA Checklist

## Status
- State: active | QA APPROVED | QA BLOCKED   # QA owns this field and sets the terminal verdict
- Verdict date: —
- Approved by: —

## QA Handoff

### Review focus
- <what to check — layer boundaries, response_model, migration safety, actor re-verification, etc.>
- Rule provenance: every block in the role `rules.md` files carries a `Source: get_guideline("<slug>")` line.
- Test adequacy: do the developer's tests actually cover the acceptance criteria? (The hook proves
  they pass; QA judges whether they cover the behavior that matters.)

### Blocking risks
- <risk: what breaks if this is wrong>

> No validator list. Lint, types, `validate-tools`, and the suite run automatically as the
> SubagentStop gate hook before QA ever sees the slice — QA judges design, not mechanical checks.

## E2E coverage required
- [ ] <flow>

## Acceptance criteria
- [ ] <observable outcome from feature scope>

## Do Not Touch
- <files or behaviors that must not change>
```

---

## `history/<summary>.md`

> Created by the orchestrator before every fourth QA-approved slice. Contains only the previous three QA-approved slices. Review-only — never use as an active implementation handoff.

```md
# Historical Slices <start>–<end>

Review-only summary. Do not use as an active implementation handoff.

## Slice Index
| Slice | File | Outcome | Risk areas |
|---|---|---|---|
| 001 | `<old-slice>/` | QA APPROVED | <auth/RBAC/etc> |

## Contracts Established
- API:
- Data:
- UI:
- Permissions:

## QA Review Notes
- Known residual risks:
- Test coverage already added:
- Validators previously relevant:

## Do Not Reopen Unless
- <condition>
```
