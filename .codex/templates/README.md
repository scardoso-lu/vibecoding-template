# Feature Memory Templates

Feature memory lives under `feature-memory/<slice>/` (gitignored, runtime only). The orchestrator writes it in Plan Mode; sub-agents read it, never write it. The exception is QA, which may set the terminal verdict in `slice.md`. User-facing E2E evidence is deterministic Playwright code under `frontend/e2e/**` plus Playwright runner output, not a separate prose E2E report artifact.

## Templates

- **Routing table**: `.codex/templates/template-routing.md` maps slice needs to focused category templates.
- **Category templates**: `.codex/templates/categories/` contains small section templates for base slice, rules, foundation, backend, frontend, E2E, QA, and history.
- **Full slice index**: `.codex/templates/template-full.md` is intentionally small and points to the routing table.
- **Minimal slice**: `.codex/templates/template-minimal.md` is for docs, config-only, copy, and one-file non-behavior changes.

The orchestrator reads `template-routing.md` first, then only the category templates needed for the slice. Templates are never passed to backend, frontend, or QA agents.

## Workflow rules

See `.codex/agents/orchestrator.toml` for Plan Mode steps, Minimal Slice Mode eligibility, compaction schedule, and routing rules.

