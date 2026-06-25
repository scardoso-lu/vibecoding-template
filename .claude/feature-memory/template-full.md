# Feature Memory — Directory Template

The orchestrator creates a directory per feature, not a single file. This template shows the expected structure and the format for each file inside it.

> **No implementation code in feature memory.** Task files are specifications: entity field lists, endpoint signatures, directory trees, business rules, and prose descriptions. Sub-agents own all implementation. Code is allowed only as a minimal base example (≤10 lines) when a structural pattern is non-obvious, followed by an `Anti-patterns` block listing what NOT to do.

```
.claude/feature-memory/<slice>/
  00-shared/           # fullstack features only — omit for backend-only or frontend-only
  backend/
  frontend/            # omit for backend-only features
  tests/
  qa/
```

---

## `00-shared/api-contract.md`

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

---

## `00-shared/cross-stack.md`

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

## `backend/rules.md`

```md
# <slice> — Backend Rules

All rules extracted from `get_guideline()` MCP calls. Every backend invocation reads this file.

## `<slug>`

- Always …
- Never …
- Must …

## `<slug>`

- Always …
- Never …
- Must …
```

---

## `backend/task-foundation.md`

```md
# <slice> — Backend Foundation

## What to build
Base infrastructure shared by all domains.

## Directory tree
src/
  domain/
    entities/
      base.py          # Base, IdMixin, TimestampMixin
      __init__.py      # re-exports all entity modules
    exceptions.py      # domain exception hierarchy
  shared/
    dto/
      paginated.py     # Page[T] generic dataclass
  infrastructure/
    db/
      base.py          # shared SQLAlchemy declarative Base
      session.py       # async engine factory + get_session dependency
alembic/
  env.py               # must import entity __init__ so all models register
  versions/
    <timestamp>_initial_schema.py

## Key decisions
- ID strategy: Snowflake IDs generated in Python, stored as BIGINT
- Session: async, expire_on_commit=False, pool_pre_ping=True
- Alembic: env.py imports `src.domain.entities` to auto-detect all models

## Anti-patterns
- Do not generate IDs in SQL (no SERIAL / AUTO_INCREMENT)
- Do not import individual entity files in env.py — import the package __init__
- Do not use sync SQLAlchemy session

## Commands
ruff check . && ruff format . && mypy src/ && alembic upgrade head

## Stop condition
All base imports resolve; `alembic upgrade head` applies cleanly; `alembic downgrade base` works.
```

---

## `backend/task-<domain>.md`

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
src/
  domain/entities/<entity>.py
  application/
    dto/<entity>_dto.py
    use_cases/<domain>/
      create_<entity>.py
      get_<entity>.py
      list_<entities>.py
      update_<entity>.py
      delete_<entity>.py
  infrastructure/repositories/
    contract.py              # add abstract repo interface for this entity
    <entity>_repository.py
  presentation/routes/<entity>.py

## Use cases
- `Create<Entity>`: validates uniqueness, raises `<DomainError>` if …
- `Get<Entity>`: raises `NotFoundError` if not found
- `List<Entities>`: cursor-paginated, default page_size 20
- `Update<Entity>`: partial update, only provided fields change
- `Delete<Entity>`: hard delete, returns nothing

## API endpoints owned by this task
(copy only the relevant rows from `00-shared/api-contract.md`)

## Anti-patterns
- Do not put business logic in the repository
- Do not raise HTTP exceptions from use cases — use domain exceptions only
- Do not return ORM objects from use cases — always map to DTOs

## Commands
ruff check . && ruff format . && mypy src/ && pytest tests/ -v --cov=src

## Stop condition
All endpoints return correct status codes; unit tests pass for all use cases.
```

---

## `frontend/rules.md`

```md
# <slice> — Frontend Rules

All rules extracted from `get_guideline()` MCP calls.

## `<slug>`

- Always …
- Never …
- Must …
```

---

## `frontend/task.md`

```md
# <slice> — Frontend Task

## Depends on
Backend complete. API contract: `00-shared/api-contract.md`. Types: `00-shared/cross-stack.md`.

## Routes
All under `src/app/[lang]/(private)/`:
- `<route>/page.tsx` — Server Component; fetches <what> from service, renders <ComponentName>
- `<route>/new/page.tsx` — Server Component shell wrapping <FormComponent>
- `<route>/[id]/page.tsx` — Server Component; fetches single record, renders <DetailComponent>
- Each segment requires: `loading.tsx`, `error.tsx`, `not-found.tsx`

## Services
`src/services/<domain>.ts`
- `get<Resource>(id)` → `<ResourceDto>` — cache tag: `<resource>-<id>`
- `list<Resources>(cursor?)` → `Page<ResourceDto>` — cache tag: `<resource>-list`

## Server Actions
`src/actions/<domain>.ts`
- `create<Resource>(formData)`: re-verify actor from cookie → Zod validate → call service → revalidateTag → return `{ status, error? }`
- `update<Resource>(id, formData)`: same pattern
- `delete<Resource>(id)`: same pattern

## Anti-patterns
- Do not call fetch() directly from components — use services
- Do not put auth logic in components — re-verify in every Server Action
- Do not skip loading/error/not-found segments

## Commands
pnpm tsc --noEmit

## Stop condition
Zero TypeScript errors; all four UI states (loading, error, empty, success) implemented per route.
```

---

## `frontend/components.md`

```md
# <slice> — Frontend Components

## `<ComponentName>`
- File: `src/components/app/<component>.tsx`
- Type: Server Component | Client Component (reason: <why it needs client>)
- Props: `{ prop: type, … }`
- daisyUI variant: card | table | stat | badge — describe layout intent
- States required: loading | error | empty | success
- Accessibility: list required aria attributes and label requirements

## `<FormComponentName>`
- File: `src/components/app/<form>.tsx`
- Type: Client Component (needs useForm / useTransition)
- Zod schema: `<schema name from lib/schemas.ts>`
- Fields: field name → input type (text | select | textarea) + validation rule
- Error display: per-field inline error + root server error alert
- Submit state: button disabled while pending, spinner visible

## Anti-patterns
- Do not fetch data inside Client Components — pass as props from Server Component parent
- Do not use useState for server-derived data
- Do not skip aria-invalid / aria-describedby on form fields with errors
```

---

## `tests/rules.md`

```md
# <slice> — Testing Rules

All rules extracted from `get_guideline()` MCP calls.

## `<slug>`

- Always …
- Never …
- Must …
```

---

## `tests/task.md`

```md
# <slice> — Tests

## Unit tests
`tests/unit/use_cases/test_<usecase>.py`
- happy path: <what the use case returns on success>
- <error case 1>: <which domain exception is raised and why>
- <error case 2>: <which domain exception is raised and why>

Use `MagicMock` + `AsyncMock` for repos. Construct entities via `Entity._mock()` — never call `__init__` directly.

## Integration tests
`tests/integration/routes/test_<resource>_routes.py`
- POST → 201 with valid body
- GET → 200 for existing record
- GET → 404 for missing record
- POST → 422 for invalid body

## Anti-patterns
- Do not hit a real database in unit tests
- Do not call entity `__init__` directly — always use `_mock()` factory
- Do not import from `presentation` layer in unit tests

## Commands
pytest tests/ -v --cov=src --cov-omit="src/presentation/routes/*,src/application/dto/*,app/main.py" --cov-report=term-missing

## Stop condition
All green. Use-case unit coverage > 80%.
```

---

## `qa/rules.md`

```md
# <slice> — QA Rules

All rules extracted from `get_guideline()` MCP calls relevant to QA review.

## `<slug>`

- Always …
- Never …
- Must …
```

---

## `qa/checklist.md`

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
- [ ] <flow 1>
- [ ] <flow 2>

## Acceptance criteria
- [ ] <observable outcome from feature scope>

## Allowed validators
- `<exact_mcp_tool_name>` — <why it applies>
- Empty means QA runs no MCP validators.

## Do Not Touch
- <files or behaviors that must not change>
```
