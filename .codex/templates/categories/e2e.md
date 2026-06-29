# Code-First Playwright QA Sections

Include these sections in `slice.md` only for user-facing slices. QA generates or heals
deterministic Playwright story tests. E2E coverage is tracked in `feature-memory/<slice>/e2e-coverage.json`;
do not create or route a separate prose E2E report artifact.

```md
## E2E Test Stories
| Story ID | User Story | Criteria | Test Location | Seed/Setup | Assertions | Slugs |
|---|---|---|---|---|---|---|
| e2e-001 | As a <user>, I want <capability>, so <outcome>. | AC-001 | `frontend/e2e/<feature>.spec.ts::<test name>` | <fixture/API seed> | <observable assertions> | `<slug>` |

## Playwright Setup
- Launch backend:
- Launch frontend:
- Seed data / credentials:
- Focused command:
- CLI generation/debug procedure: `.codex/skills/playwright-cli/references/spec-driven-testing.md`
```

Also write `feature-memory/<slice>/e2e-coverage.json`:

```json
{
  "schema_version": 1,
  "source": "initial user prompt",
  "user_stories": [
    {"id": "US-001", "prompt_text": "<prompt user story>", "covered_by": ["e2e-001"]}
  ],
  "tests": [
    {"id": "e2e-001", "location": "frontend/e2e/<feature>.spec.ts::<test name>", "covers": ["US-001"]}
  ]
}
```
