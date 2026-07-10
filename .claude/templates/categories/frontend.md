# Frontend Sections

Include these sections in `slice.md` only when frontend work is routed.

```md
## Frontend Contract
- Routes:
- Components:
- Server actions/services:
- Loading/error/empty states:
- Accessibility/RBAC notes:

## Verification additions
- Map component/server-action/page-behavior cases in `## Test Coverage`, and name the frontend
  test command that runs them as a `## Verification` `- Run:` row covering their `AC-###` ids.
- When user-visible behavior changes, add the focused Playwright command as a `- Run:` row too -
  it must match the QA Handoff `Focused Playwright command:` value.
```
