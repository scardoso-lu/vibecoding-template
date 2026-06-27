#!/usr/bin/env bash
# SessionStart hook (matcher: compact) — re-inject the workflow rules after compaction.
#
# Compaction summarizes the conversation and can drop the project's operating rules. Anything this
# prints to stdout is added back into Codex's context, so we restate the essentials and the live
# state (which feature-memory slices are active) rather than dumping all of AGENTS.md.
set -uo pipefail

ROOT="${CODEX_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
cd "$ROOT" 2>/dev/null || true

cat <<'EOF'
[context refresh after compaction — vibecoding-template operating rules]
1. Use guidelines through feature-slice memory: only the orchestrator calls the
   fullstack-guidelines MCP; it writes rules into .codex/feature-memory/<slice>/ for each role.
2. Route every request through the agent system (start with the orchestrator); do not implement
   features directly on the main thread.
3. Deterministic work is a hook, not an agent step: formatting, lint, type-checks, validate-tools,
   and the test suite run automatically via .codex/hooks/ (PostToolUse + the SubagentStop gate).
   QA is judgment-only; there is no tester agent.
4. Non-orchestrator subagents may not read AGENTS.md, CLAUDE.md, .codex/, .claude/, scripts/,
   hooks, settings, or agent templates directly. They must request orchestrator context.
EOF

# Live state: active feature-memory slices and their QA state, when the runtime dir exists.
if compgen -G ".codex/feature-memory/*/" >/dev/null 2>&1; then
  echo "Active feature-memory slices:"
  for d in .codex/feature-memory/*/; do
    [ -d "$d" ] || continue
    slice="$(basename "$d")"
    state="$(grep -h -m1 'State:' "$d/qa/checklist.md" 2>/dev/null | sed 's/^[[:space:]-]*//')"
    printf '  - %s — %s\n' "$slice" "${state:-no qa/checklist yet}"
  done
else
  echo "No active feature-memory slices (scaffold / none in progress)."
fi

exit 0
