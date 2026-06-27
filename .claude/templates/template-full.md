# Feature Memory — Directory Template

The orchestrator reads this file at the start of Plan Mode and follows every section's format and content rules exactly.

> **No implementation code in feature memory.** Task files are specifications: entity field lists, endpoint signatures, directory trees, business rules, and prose descriptions. Sub-agents own all implementation. The orchestrator fills in domain-specific content; sub-agents derive implementation patterns from their `rules.md`.

```
.claude/feature-memory/<slice>/
  00-shared/                   # fullstack only — omit for backend-only or frontend-only
    api-contract.md            # every endpoint both stacks must agree on
    cross-stack.md             # error envelope, pagination shape, TypeScript↔Python type mappings

  backend/
    rules.md                   # all backend MCP rules — written once, read by every backend invocation
    task-foundation.md         # base infrastructure: Base, IdMixin, session, exceptions, migration scaffold
    task-<domain>.md           # one file per domain: entity + repo + use cases + routes

  frontend/
    rules.md                   # all frontend MCP rules
    task.md                    # pages, services, server actions
    components.md              # only when the feature has more than three components

  tests/
    rules.md                   # testing MCP rules
    task.md                    # test file list, case descriptions, fixture notes

  e2e/                         # user-facing slices only — omit for backend-only or non-behavior changes
    rules.md                   # exploratory E2E MCP rules
    task.md                    # flows to explore, acceptance criteria, app launch + seed/credential notes
    report.md                  # written by e2e-explorer — structured bug findings (not authored by orchestrator)
    artifacts/                 # written by e2e-explorer — screenshots, console/network captures

  qa/
    rules.md                   # QA MCP rules
    checklist.md               # review focus, blocking risks, E2E coverage, allowed validators
```

---

## `00-shared/`

> Only for fullstack features. Contains only content multiple agents must agree on — if one agent gets it wrong, another's work breaks. Never put guidelines here (those go in role `rules.md`). Never put domain model details here (those go in `backend/task-<domain>.md`); the frontend only needs the TypeScript shapes from `cross-stack.md`.

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

---

## `backend/`

> `rules.md` is written once per feature and read by every backend invocation. It contains only backend MCP slugs — never frontend or testing rules. Each task file covers exactly one implementation scope; the backend-developer is invoked once per task file.

### `backend/rules.md`

```md
# <slice> — Backend Rules

All rules extracted from `get_guideline()` MCP calls. Every backend invocation reads this file.

## `<slug>`

- Always …
- Never …
- Must …
```

### `backend/task-foundation.md`

> Always the first backend task. Covers shared base infrastructure only — no domain entities.

```md
# <slice> — Backend Foundation

## What to build
Base infrastructure shared by all domains.

## Directory tree
<describe the file and directory structure>

## Commands
<see CLAUDE.md — lint, type-check, migration>

## Stop condition
<what "done" looks like for the foundation>
```

### `backend/task-<domain>.md`

> One file per domain. Split whenever a single invocation would cover more than one full domain (entity + repo + use cases + routes).

```md
# <slice> — Backend: <Domain>

## What to build
<Entity> entity + repository + use cases + routes.

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

## Commands
<see CLAUDE.md — lint, type-check, test>

## Stop condition
<what "done" looks like>
```

---

## `frontend/`

> `rules.md` contains only frontend MCP slugs. `task.md` lists pages, services, and server actions by name and behavior — not by implementation. `components.md` is only created when the feature has more than three components. No JSX or TypeScript implementation bodies anywhere.

### `frontend/rules.md`

```md
# <slice> — Frontend Rules

All rules extracted from `get_guideline()` MCP calls.

## `<slug>`

- Always …
- Never …
- Must …
```

### `frontend/task.md`

```md
# <slice> — Frontend Task

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

## Commands
<see CLAUDE.md — type-check>

## Stop condition
<what "done" looks like>
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

## `tests/`

> `rules.md` contains testing MCP slugs only. `task.md` lists test cases by description — no implementation code.

### `tests/rules.md`

```md
# <slice> — Testing Rules

All rules extracted from `get_guideline()` MCP calls.

## `<slug>`

- Always …
- Never …
- Must …
```

### `tests/task.md`

```md
# <slice> — Tests

## Unit tests
`tests/unit/use_cases/test_<usecase>.py`
- happy path: <what the use case returns on success>
- <error case>: <which exception is raised and why>

## Integration tests
`tests/integration/routes/test_<resource>_routes.py`
- <HTTP method> → <status code>: <scenario>

## Commands
<see CLAUDE.md — test>

## Stop condition
<what "done" looks like>
```

---

## `e2e/`

> Only for slices that change user-facing behavior — the explorer needs a UI to drive. `rules.md` contains exploratory-E2E MCP slugs only (e.g. `frontend/13-e2e-playwright`, `frontend/14-loading-error-empty-states`, `frontend/19-rbac-permissions`). `task.md` tells the explorer which flows to walk, what "correct" looks like, and exactly how to launch the app and reach a usable state. The explorer writes `report.md` and `artifacts/` itself — the orchestrator does not author them.

### `e2e/rules.md`

```md
# <slice> — E2E Exploration Rules

All rules extracted from `get_guideline()` MCP calls.

## `<slug>`

- Always …
- Never …
- Must …
```

### `e2e/task.md`

```md
# <slice> — E2E Exploration

## Status
- State: active | E2E CLEAN | E2E BUGS FOUND
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
<see CLAUDE.md — run backend, run frontend>

## Do Not Touch
- <files or behaviors the explorer must not change>

## Stop condition
Every listed flow exercised; findings logged to `report.md` with reproducible steps and evidence.
```

---

## `qa/`

> `rules.md` contains QA MCP slugs. `checklist.md` must list every allowed validator by exact `validate-tools` CLI command. QA is the final gate — nothing merges without `State: QA APPROVED`.

### `qa/rules.md`

```md
# <slice> — QA Rules

All rules extracted from `get_guideline()` MCP calls relevant to QA review.

## `<slug>`

- Always …
- Never …
- Must …
```

### `qa/checklist.md`

```md
# <slice> — QA Checklist

## Status
- State: active | QA APPROVED | QA BLOCKED
- Verdict date: —
- Approved by: —

## Review focus
- <what to check — layer boundaries, response_model, migration safety, actor re-verification, etc.>

## Blocking risks
- <risk: what breaks if this is wrong>

## E2E coverage required
- [ ] <flow>

## Acceptance criteria
- [ ] <observable outcome from feature scope>

## Allowed validators
- `validate-tools <command>` — <why it applies>
- Empty means QA runs no validators.

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
