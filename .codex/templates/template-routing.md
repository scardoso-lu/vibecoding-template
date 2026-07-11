# Template Routing

The product-owner and software-architect read this file first in Plan Mode. Load only the category templates needed for
the current slice. Do not load every template by default.

| Slice need | Template file |
|---|---|
| Product PRD | `.codex/templates/product-prd.md` |
| Architecture decision record | `.codex/templates/adr.md` |
| Every non-minimal business feature | `.codex/templates/categories/base-slice.md` |
| Global rules file (`memory/rules.md`) | `.codex/templates/categories/rules.md` |
| Repo layout, root tooling, bootstrap, app roots | `.codex/templates/categories/foundation.md` |
| FastAPI/domain/API/migrations/backend tests | `.codex/templates/categories/backend.md` |
| Next.js routes/components/actions/frontend tests | `.codex/templates/categories/frontend.md` |
| User-facing Playwright story tests | `.codex/templates/categories/e2e.md` |
| QA merge judgment | `.codex/templates/categories/qa.md` |
| Docs/config/copy/one-file non-behavior change | `.codex/templates/template-minimal.md` |

Rules:
- PRDs are complete product artifacts under `memory/PRD/<purpose>/prd.md`, not feature
  slices. Avoid over-splitting: keep one cohesive PRD; write parent/component PRDs only when a
  component is genuinely heterogeneous - independently shippable or separately owned - not merely
  because the document is long.
- ADRs are architecture artifacts under `memory/ADR/<purpose>/adr.md`. They translate
  accepted PRDs into technical decisions before feature slices are derived, kept as one cohesive ADR
  per purpose unless decisions are genuinely heterogeneous.
- Write one `slice.md` per business feature under `memory/feature/<feature-slice>/` as one cohesive,
  homogeneous pack, bundling that feature's structure/scaffolding, backend, frontend, and tests into
  the same slice. Split the request into business features (not construction steps) and link them
  through each slice's `## Dependencies`.
- Keep rules global and unsliced: write every rule in the single `memory/rules.md`, one
  block per guideline slug, and link the slugs a feature needs from that feature's `## Dependencies`
  -> `Rules:` line. Do not split rules by category and do not write a per-slice `rules.md`.
- Never create role-specific markdown files or `00-shared/`.
- The selected category templates provide sections to include in `slice.md`; except for the global
  `memory/rules.md`, they are not separate output files.
