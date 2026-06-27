# Feature Memory Templates

Feature memory lives under `.codex/feature-memory/<slice>/` (gitignored — runtime only). The orchestrator writes it in Plan Mode; sub-agents read it, never write it — the one exception is `e2e-explorer`, which writes its own findings to `e2e/report.md` and `e2e/artifacts/`.

## Templates

- **Full slice**: `.codex/templates/template-full.md` — directory layout, per-file format, content rules, anti-patterns, and the historical summary template
- **Minimal slice**: `.codex/templates/template-minimal.md` — for docs, config-only, copy, one-file non-behavior changes

The orchestrator reads the relevant template at the start of Plan Mode. Templates are never passed to backend, frontend, or QA agents.

## Workflow rules

See `.codex/agents/orchestrator.md` for Plan Mode steps, Minimal Slice Mode eligibility, compaction schedule, and all routing rules.
