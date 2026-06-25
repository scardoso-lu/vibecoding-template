# <feature-slice-name>

## Status
- State: active | QA APPROVED | QA BLOCKED | superseded
- QA verdict date:
- Approved by:

## Request
<Original user request or precise summary.>

## Slice Boundary
- In scope:
- Out of scope:
- User-visible outcome:
- Risk areas: auth | RBAC | migration | PII/logging | dependency | payments | file upload | none

## Guideline Context
MCP-backed source of truth for this slice. Include every relevant rule category before routing; do not paste full guideline prose.

| Slug | Applies to | Local rule summary |
|---|---|---|
| `<slug>` | backend/frontend/tester/qa | <one or two concrete rules for this slice> |

## Existing Local Context
- Files to inspect:
  - `<path>` - <why it matters>
- Existing patterns to follow:
- Contracts already present:
- Related tests:

## Do Not Touch
- Files/directories:
- Behaviors:
- Data/contracts:

## Backend Handoff
Use this section only when backend work is in scope. Otherwise write `Not in scope`.

- Layers touched:
  - Domain:
  - Application:
  - Infrastructure:
  - API:
  - Database/migrations:
- Required files or directories:
  - `<path>` - <expected change>
- API contract:
  - Method/path:
  - Request schema:
  - Response schema:
  - Status codes:
  - Auth/authz:
- Data contract:
  - Tables/models:
  - Migration needed: yes/no
  - Backward compatibility constraints:
- Business rules:
- Error handling:
- Audit/logging requirements:
- Backend tests expected:
- Backend validation commands:

## Frontend Handoff
Use this section only when frontend work is in scope. Otherwise write `Not in scope`.

- Routes/pages touched:
- Components touched or created:
- Server vs client component decision:
  - Default server components:
  - Client components and reason:
- Data source:
  - API endpoint or server action:
  - Request/response types:
- UI states:
  - Loading:
  - Empty:
  - Error:
  - Success:
- Form behavior and validation:
- Permission/RBAC behavior:
- Accessibility requirements:
- Frontend tests expected:
- Frontend validation commands:

## Cross-Stack Contract
Use this section when backend and frontend both change. Otherwise write `Not in scope`.

- Backend must finish before frontend: yes/no
- Shared types or schema source:
- Endpoint contract the frontend must consume:
- Error format the frontend must display:
- Permission contract:
- Mock or fixture data allowed:

## Acceptance Criteria
- [ ] <observable behavior>
- [ ] <testable requirement>

## Tester Handoff
- Tests to write or update:
- Existing tests to inspect:
- Local commands to run:
- Expected test evidence:
- Fixtures or test data:

## QA Handoff
- Review focus:
- Blocking risks:
- E2E coverage required:
- Allowed validators:
  - `<validator tool name>` - <why it applies>
  - Empty means QA runs no MCP validators.

## Open Questions
- None
