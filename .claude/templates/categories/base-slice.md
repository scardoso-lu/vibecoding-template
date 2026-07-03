# Base Slice Template

Use for every non-minimal feature. Write one `slice.md` per business feature under
`feature-memory/<feature>/`, and link the sibling features and global rule files it needs in
`## Dependencies`.

```md
# <feature>

## Status
- State: active | NEEDS-INPUT | BLOCKED | E2E CLEAN | E2E BUGS FOUND | QA APPROVED | QA BLOCKED
- Current owner: planner | challenger | backend-developer | frontend-developer | qa
- Last updated:

## Request
<Original user request or precise summary of this business feature.>

## Slice Boundary
- User outcome:
- In scope:
- Out of scope:

## Dependencies
- Depends on: feature-memory/<other-feature>, ... | none
- Rules: <slug>, <slug>, ... | none   # guideline slugs defined in the global feature-memory/rules.md

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
- Deterministic gate: `python scripts/validate/cli.py gate --root . --slice feature-memory/<feature>/slice.md`

## Provenance
| Decision | Slug |
|---|---|
```
