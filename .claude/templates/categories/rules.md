# Rules Template

Rules are **global** and shared across every slice. Write them under
`feature-memory/rules/<category>.md` - one file per category concern - and reference the files a
slice needs from that slice's `## Dependencies` section. Do not write a per-slice `rules.md`.

Add or extend a category file only when the slice in front of you needs that concern. Reuse the
existing category files across slices instead of duplicating rules. Every rule block must cite its
source slug.

Split categories by concern, e.g. `backend.md`, `frontend.md`, `qa.md`, `security.md`,
`foundation.md`.

```md
# <Category> Rules

All rules come from `get_guideline()` MCP calls. Slices reference this file from their
`## Dependencies` -> `Rules:` line.

## `<slug>`
Source: get_guideline("<slug>")
- Always ...

## `<slug>`
Source: get_guideline("<slug>")
- Always ...
```
