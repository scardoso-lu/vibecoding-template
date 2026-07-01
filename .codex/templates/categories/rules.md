# Rules Template

Write one `feature-memory/<slice>/rules.md`. Group fetched MCP rules by role. Every rule
block must cite the source slug.

```md
# <slice> - Rules

All rules come from `get_guideline()` MCP calls made during this planning session.

## Backend
### `<slug>`
Source: get_guideline("<slug>")
- Always ...

## Frontend
### `<slug>`
Source: get_guideline("<slug>")
- Always ...

## QA
### `<slug>`
Source: get_guideline("<slug>")
- Always ...

### `<user-facing/testing slug>`
Source: get_guideline("<slug>")
- Playwright spec generation, story coverage, and runner-output expectations ...
```

