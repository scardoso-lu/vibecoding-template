# Backend Sections

Include these sections in `slice.md` only when backend work is routed.

```md
## Domain And Data
- Entities:
- Fields:
- Relationships:
- Business rules:
- Migrations:

## API Contract
- Endpoint:
  - Request:
  - Response:
  - Errors:
  - Pagination/cache/auth notes:

## Verification additions
- Map backend unit/integration/API/migration cases in `## Test Coverage`, and name the
  backend test command that runs them as a `## Verification` `- Run:` row covering their
  `AC-###` ids (e.g. `- Run: cd backend && uv run pytest test/test_<feature>.py -q | covers: AC-001`).
```
