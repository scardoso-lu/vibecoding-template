# Template Routing

The planner reads this file first in Plan Mode. Load only the category templates needed for
the current slice. Do not load every template by default.

| Slice need | Template file |
|---|---|
| Every non-minimal business feature | `.claude/templates/categories/base-slice.md` |
| Global rules library (`feature-memory/rules/<category>.md`) | `.claude/templates/categories/rules.md` |
| Repo layout, root tooling, bootstrap, app roots | `.claude/templates/categories/foundation.md` |
| FastAPI/domain/API/migrations/backend tests | `.claude/templates/categories/backend.md` |
| Next.js routes/components/actions/frontend tests | `.claude/templates/categories/frontend.md` |
| User-facing Playwright story tests | `.claude/templates/categories/e2e.md` |
| QA merge judgment | `.claude/templates/categories/qa.md` |
| Historical compaction | `.claude/templates/categories/history.md` |
| Docs/config/copy/one-file non-behavior change | `.claude/templates/template-minimal.md` |

Rules:
- Write one `slice.md` per business feature under `feature-memory/<feature>/`. Split the request
  into features and link them through each slice's `## Dependencies`.
- Keep rules global: write them under `feature-memory/rules/<category>.md`, one file per category,
  and reference the ones a feature needs from that feature's `## Dependencies` -> `Rules:` line. Do
  not write a per-slice `rules.md`.
- Never create role-specific markdown files or `00-shared/`. `feature-memory/rules/` is the reserved
  global rules area, not a slice.
- The selected category templates provide sections to include in `slice.md`; except for the global
  rules library, they are not separate output files.
