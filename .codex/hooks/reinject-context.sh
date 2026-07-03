#!/usr/bin/env bash
# SessionStart hook (matcher: compact) - re-inject the workflow rules after compaction.
#
# Compaction summarizes the conversation and can drop the project's operating rules. Anything this
# prints to stdout is added back into Codex's context, so we restate the essentials and the live
# state (which memory slices are active) rather than dumping all of AGENTS.md.
set -uo pipefail

ROOT="${CODEX_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
cd "$ROOT" 2>/dev/null || true

cat <<'EOF'
[context refresh after compaction - vibecoding-template operating rules]
1. Keep product intent, architecture decisions, and implementation slices separate:
   product-owner writes selectable PRD options and accepted PRDs under memory/PRD/<purpose>/prd.md;
   software-architect writes ADRs under memory/ADR/<purpose>/adr.md, then
   memory/feature/<feature>/slice.md plus the single global memory/rules.md. Only the
   software-architect calls fullstack-guidelines MCP.
2. Route every request through the agent system (start with the orchestrator). It sequences the
   product-owner -> business-challenger -> software-architect -> technical-challenger loop (both
   challengers must accept at >=90% or the user is asked), then routes developers/QA. Do not
   implement features directly on the main thread.
3. Deterministic work is a hook, not an agent step: formatting, lint, type-checks, validate-tools,
   and the test suite run automatically via .codex/hooks/ (PostToolUse, SubagentStart, and
   SubagentStop gates). Prompt hooks review developer handoffs, business PRDs, architect ADR/slices,
   and QA judgment; command hooks own developer and QA mechanical validators.
   QA owns code-first Playwright specs/output and final judgment; there is no tester or separate E2E agent.
4. Implementer/QA subagents may not read AGENTS.md, CLAUDE.md, .codex/, .claude/, scripts/, hooks,
   settings, or agent templates directly. Only orchestrator, product-owner, software-architect,
   business-challenger, and technical-challenger may; others request context through the orchestrator.
EOF

# Live state: active memory slices and their QA state, when the runtime dir exists.
if compgen -G "memory/feature/*/" >/dev/null 2>&1; then
  echo "Active memory slices:"
  for d in memory/feature/*/; do
    [ -d "$d" ] || continue
    slice="$(basename "$d")"
    state="$(grep -h -m1 'State:' "$d/slice.md" 2>/dev/null | sed 's/^[[:space:]-]*//')"
    printf '  - %s - %s
' "$slice" "${state:-no slice.md yet}"
  done
else
  echo "No active memory slices (scaffold / none in progress)."
fi

exit 0
