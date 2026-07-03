# Feature Memory Templates

Feature memory lives under `feature-memory/` (gitignored, runtime only). Each business feature is one `feature-memory/<feature>/slice.md`, and rules are a single global `feature-memory/rules.md` (one block per guideline slug) shared across features - never split by category. A slice links the sibling features and the rule slugs it depends on in its `## Dependencies` section. The planner writes all of this in Plan Mode; sub-agents read it, never write it. The exception is QA, which may set the terminal verdict in `slice.md`. User-facing E2E evidence is deterministic Playwright code under `frontend/e2e/**` plus Playwright runner output, not a separate prose E2E report artifact.

## Templates

- **Routing table**: `.codex/templates/template-routing.md` maps slice needs to focused category templates.
- **Category templates**: `.codex/templates/categories/` contains small section templates for base slice, rules, foundation, backend, frontend, E2E, QA, and history.
- **Full slice index**: `.codex/templates/template-full.md` is intentionally small and points to the routing table.
- **Minimal slice**: `.codex/templates/template-minimal.md` is for docs, config-only, copy, and one-file non-behavior changes.

The planner reads `template-routing.md` first, then only the category templates needed for the slice. Templates are never passed to backend, frontend, or QA agents.

## Workflow rules

See `.codex/agents/planner.toml` for Plan Mode steps, Minimal Slice Mode eligibility, and compaction schedule; `.codex/agents/challenger.toml` for the 90 percent challenge gate; and `.codex/agents/orchestrator.toml` for the plan/challenge loop and routing rules.

