# Base Slice Template

Use for every non-minimal feature. Write one `slice.md` per business feature under
`memory/feature/<feature-slice>/`, and link the sibling features and global rule files it needs in
`## Dependencies`.

```md
# <feature>

## Status
- State: active | NEEDS-INPUT | BLOCKED | E2E CLEAN | E2E BUGS FOUND | QA APPROVED | QA BLOCKED
- Current owner: product-owner | software-architect | business-challenger | technical-challenger | backend-developer | frontend-developer | qa
- Last updated:

## Request
<Original user request or precise summary of this business feature.>

## Slice Boundary
- User outcome:
- In scope:
- Out of scope:

## Dependencies
- PRD: memory/PRD/<purpose>/prd.md
- ADR: memory/ADR/<purpose>/adr.md
- Depends on: memory/feature/<other-feature>, ... | none
- Rules: <slug>, <slug>, ... | none   # guideline slugs defined in the global memory/rules.md

Each field is a bare, comma-separated list of refs (wrapping onto indented
continuation lines is fine). Do not append explanatory parentheticals to a ref on
these lines (e.g. `adr.md (ADR-002 ...)`, `none (because ...)`) — put that context in
`## Request`, an ADR row, or `## Provenance` instead, since these lines are parsed by
the deterministic memory validator.

## Do Not Touch
- Files/directories:
- Behaviors:
- Data/contracts:

## Implementation Plan
| Step | Agent | Work | Reads | Do Not Touch | Stop Condition |
|---|---|---|---|---|---|

## Acceptance Criteria
- [ ] AC-001: <observable behavior>
- [ ] AC-002: <observable behavior>

## Test Coverage
| Criteria | Test Type | Test Location |
|---|---|---|
| AC-001 | backend | `backend/test/<test_file>.py` |
| AC-002 | frontend-unit | `frontend/src/<feature>/<test_file>.test.tsx` |

## Tests
- Backend:
- Frontend:
- Scripted E2E:
- Deterministic gate: `python scripts/validate/cli.py gate --root . --slice memory/feature/<feature-slice>/slice.md`

## Provenance
| Decision | Slug |
|---|---|
```
