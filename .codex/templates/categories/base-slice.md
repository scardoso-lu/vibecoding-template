# Base Slice Template

Use for every non-minimal feature.

```md
# <slice>

## Status
- State: active | BLOCKED | E2E CLEAN | E2E BUGS FOUND | QA APPROVED | QA BLOCKED
- Current owner: orchestrator | backend-developer | frontend-developer | qa
- Last updated:

## Request
<Original user request or precise summary.>

## Slice Boundary
- User outcome:
- In scope:
- Out of scope:
- Split decision: one feature memory | split required because <reason>

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
- Deterministic gate: `python scripts/validate/gate.py --root . --slice feature-memory/<slice>/slice.md`

## Provenance
| Decision | Slug |
|---|---|
```
