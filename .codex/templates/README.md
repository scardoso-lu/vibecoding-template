# Memory Templates

Memory lives under `memory/` (gitignored, runtime only). Product planning uses `memory/PRD/<purpose>/prd.md`, architecture planning uses `memory/ADR/<purpose>/adr.md`, and each business feature is one `memory/feature/<feature-slice>/slice.md`. Rules are a single global `memory/rules.md` (one block per guideline slug) shared across features - never split by category. A slice links sibling features, its PRD/ADR, and the rule slugs it depends on in its `## Dependencies` section. The product-owner writes product-owned PRDs, and the software-architect completes MCP-backed technical planning in Plan Mode; sub-agents read it, never write it. The exception is QA, which may set the terminal verdict in `slice.md`. User-facing E2E evidence is deterministic Playwright code under `frontend/e2e/**` plus Playwright runner output, not a separate prose E2E report artifact.

## Templates

- **Routing table**: `.codex/templates/template-routing.md` maps slice needs to focused category templates.
- **Category templates**: `.codex/templates/categories/` contains small section templates for base slice, rules, foundation, backend, frontend, E2E, QA, and history.
- **Full slice index**: `.codex/templates/template-full.md` is intentionally small and points to the routing table.
- **Minimal slice**: `.codex/templates/template-minimal.md` is for docs, config-only, copy, and one-file non-behavior changes.

The product-owner and software-architect read `template-routing.md` first, then only the category templates needed for the slice. Templates are never passed to backend, frontend, or QA agents.

## Workflow rules

See `.codex/agents/product-owner.toml` and `.codex/agents/software-architect.toml` for Plan Mode steps, Minimal Slice Mode eligibility, and compaction schedule; `.codex/agents/business-challenger.toml` and `.codex/agents/technical-challenger.toml` for the 90 percent challenge gates; and `.codex/agents/orchestrator.toml` for the product/architecture/challenge loop and routing rules.

