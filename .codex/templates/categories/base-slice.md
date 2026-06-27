# Base Slice Template

Use for every non-minimal feature.

```md
# <slice>

## Status
- State: active | BLOCKED | E2E CLEAN | E2E BUGS FOUND | QA APPROVED | QA BLOCKED
- Current owner: orchestrator | backend-developer | frontend-developer | e2e-explorer | qa
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
- [ ] <observable behavior>

## Tests
- Backend:
- Frontend:
- Scripted E2E:

## Provenance
| Decision | Slug |
|---|---|
```
