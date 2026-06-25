# Feature Memory

Each feature slice gets one compact memory file in this directory. The orchestrator creates or updates it before routing work to developer, tester, or QA agents.

## Templates

- Full slice template: `.claude/feature-memory/template-full.md`
- Minimal slice template: `.claude/feature-memory/template-minimal.md`

The orchestrator reads templates only in Plan Mode when creating or updating a slice. Do not pass templates to backend, frontend, tester, or QA agents.

## Purpose

The memory file is a compact source of MCP-backed implementation rules and role handoffs, not a notes dump. The orchestrator should pass only the relevant role section to each downstream agent; agents may read the full active memory only if the tiny handoff is insufficient.

Do not paste full MCP guideline text here. Summarize only the slice-specific rules. Developer agents must treat `Guideline Context` as the source of truth for architecture, security, UI, testing, and implementation rules.

## Budget

- Active slice memory must stay under 150 lines.
- Each role handoff must stay under 25 lines.
- Guideline summaries must be rules only, never prose copies.
- The orchestrator should fetch the complete set of specific MCP guidelines needed for the slice once before routing, then write one compact rule bundle.
- If more context is needed, add links or file paths, not pasted content.

## Minimal Slice Mode

Minimal Slice Mode is mandatory for docs, config-only, copy, one-file non-behavior changes, and dependency-free fixes.

Required sections only:

- `Status`
- `Request`
- `Agent Plan`
- `Do Not Touch`
- `Acceptance Criteria`
- `QA Handoff`

Minimal slices still require `QA Handoff -> Allowed validators`. Values must be exact MCP tool names, without the `mcp__fullstack-guidelines__` prefix. Empty means QA runs no MCP validators.

Do not include backend, frontend, tester, cross-stack, or guideline sections in Minimal Slice Mode unless the request has a behavior change that makes the full template necessary.

## Retention

Keep at most three detailed QA-approved active slice files in `.claude/feature-memory/`.

Before creating QA-approved slice 4, 7, 10, and so on, the orchestrator must compact only the previous three detailed slices that have a QA `APPROVED` verdict into one historical summary under `.claude/feature-memory/history/`.

Do not compact blocked, in-progress, unreviewed, or QA-rejected slices. Keep them active and detailed until QA approves them or the user explicitly closes/supersedes them.

Historical summaries are review-only context. They must not be used as active implementation handoffs for backend, frontend, tester, or QA agents.

## Historical Summary Template

```md
# Historical Slices <start>-<end>

Review-only summary. Do not use as an active implementation handoff.

## Slice Index
| Slice | File | Outcome | Risk areas |
|---|---|---|---|
| 001 | `<old-file>` | QA APPROVED | <auth/RBAC/etc> |

## Contracts Established
- API:
- Data:
- UI:
- Permissions:

## QA Review Notes
- Known residual risks:
- Test coverage already added:
- Validators previously relevant:

## Do Not Reopen Unless
- <condition>
```

## Rules

- Use Minimal Slice Mode whenever eligible. Full slice memory for an eligible minimal slice is a workflow error.
- Every detailed slice memory must include `Status`, `Do Not Touch`, and `QA Handoff` with `Allowed validators`.
- `Guideline Context` is the MCP-backed source of truth for code-shape rules. Do not duplicate those rules in developer-agent prompts.
- `Allowed validators` must contain exact MCP tool names, such as `validate_hardcoded_secrets` or `verify_compliance`. Empty means QA runs no MCP validators.
- Commit messages may cite only slugs already present in feature memory. Agents must not expand commit slugs by doing fresh guideline work.
- QA must ask the orchestrator to update `Allowed validators` before running an unlisted validator.
- Prefer file paths, contracts, and commands over general advice.
- If a subagent asks for more context, update the relevant handoff section or send a richer handoff after a targeted MCP fetch.
- If a subagent would otherwise guess or continue best-effort, it must request targeted orchestrator context for the existing slice. Update the relevant section instead of creating a new slice.
- Each subagent may request targeted orchestrator context once per slice. If still blocked after one update, it returns `ESCALATE` or `BLOCKED`; improve future planning instead of looping.
- Keep the file compact enough that an agent can read it when a tiny handoff is insufficient.
- Keep only the latest three QA-approved detailed slice memories active; compact older QA-approved slices into review-only history.
- Never compact blocked, in-progress, unreviewed, or QA-rejected slices into historical summaries.
- Historical summaries are short review indexes, not retrospectives. Do not include long decision logs.
