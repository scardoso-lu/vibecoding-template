# Template Routing

The orchestrator reads this file first in Plan Mode. Load only the category templates needed for
the current slice. Do not load every template by default.

| Slice need | Template file |
|---|---|
| Every non-minimal feature | `.claude/templates/categories/base-slice.md` |
| MCP rule bundle | `.claude/templates/categories/rules.md` |
| Repo layout, root tooling, bootstrap, app roots | `.claude/templates/categories/foundation.md` |
| FastAPI/domain/API/migrations/backend tests | `.claude/templates/categories/backend.md` |
| Next.js routes/components/actions/frontend tests | `.claude/templates/categories/frontend.md` |
| User-facing browser exploration | `.claude/templates/categories/e2e.md` |
| Final merge judgment | `.claude/templates/categories/qa.md` |
| Historical compaction | `.claude/templates/categories/history.md` |
| Docs/config/copy/one-file non-behavior change | `.claude/templates/template-minimal.md` |

Rules:
- Always write one `slice.md` and one `rules.md` for non-minimal feature work.
- Never create role-specific markdown files or `00-shared/`.
- The selected category templates provide sections to include in `slice.md`; they are not separate
  output files.
