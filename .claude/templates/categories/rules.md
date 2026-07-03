# Rules Template

Rules are **global** and never sliced. Keep every fetched guideline rule in one shared file,
`feature-memory/rules.md`, with one block per guideline slug. Do not split rules by category
(no `backend.md`/`frontend.md`/`qa.md`) and do not write a per-slice `rules.md`.

Each feature links the rules it depends on from its `## Dependencies` -> `Rules:` line, which lists
the slugs it uses. Reuse and extend the existing blocks across features instead of duplicating
rules. Every block must cite its source slug.

```md
# Rules

All rules come from `get_guideline()` MCP calls. Features link the slugs they need from their
`## Dependencies` -> `Rules:` line.

### `<slug>`
Source: get_guideline("<slug>")
- Always ...

### `<slug>`
Source: get_guideline("<slug>")
- Always ...
```
