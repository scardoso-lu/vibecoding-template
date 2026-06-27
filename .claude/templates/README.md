# Feature Memory Templates

Feature memory lives under `.claude/feature-memory/<slice>/` (gitignored — runtime only). The orchestrator writes it in Plan Mode; sub-agents read it, never write it — the one exception is `e2e-explorer`, which writes its own findings to `e2e/report.md` and `e2e/artifacts/`.

## Templates

- **Full slice**: `.claude/templates/template-full.md` — directory layout, per-file format, content rules, anti-patterns, and the historical summary template
- **Minimal slice**: `.claude/templates/template-minimal.md` — for docs, config-only, copy, one-file non-behavior changes

The orchestrator reads the relevant template at the start of Plan Mode. Templates are never passed to backend, frontend, tester, or QA agents.

## Workflow rules

See `.claude/agents/orchestrator.md` for Plan Mode steps, Minimal Slice Mode eligibility, compaction schedule, and all routing rules.
