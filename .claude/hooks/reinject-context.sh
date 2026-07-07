#!/usr/bin/env bash
# SessionStart hook (matcher: compact) - re-inject the workflow rules after compaction.
#
# Compaction summarizes the conversation and can drop the project's operating rules. Anything this
# prints to stdout is added back into Claude's context, so we restate the essentials and the live
# state (which memory slices are active) rather than dumping all of CLAUDE.md.
#
# This stays wired to SessionStart (not PostCompact) deliberately: PostCompact fires after
# compaction too, but its stdout is never fed back into Claude's context (side-effects only), so it
# cannot do this file's job. track-compact.sh is the PostCompact hook - it only logs that a
# compaction happened, for out-of-band review.
set -uo pipefail

ROOT="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
cd "$ROOT" 2>/dev/null || true

cat <<'EOF'
[context refresh after compaction - vibecoding-template operating rules]
1. Keep product intent, architecture decisions, and implementation slices separate:
   product-owner writes selectable PRD options and accepted PRDs under memory/PRD/<purpose>/prd.md;
   software-architect writes ADRs under memory/ADR/<purpose>/adr.md, then
   memory/feature/<feature>/slice.md plus the single global memory/rules.md. Only the
   software-architect calls fullstack-guidelines MCP.
2. Route every request through the agent system directly from the main thread. It sequences the
   product-owner -> business-challenger -> software-architect -> technical-challenger loop (both
   challengers must accept at >=90% or the user is asked), then routes developers/QA. Do not
   implement features directly on the main thread.
3. Deterministic work is a hook, not an agent step: formatting, lint, type-checks, validate-tools,
   and the test suite run automatically via .claude/hooks/ (PostToolUse, SubagentStart,
   SubagentStop, and Stop gates). Prompt hooks review developer handoffs, business PRDs, architect
   ADR/slices, main-thread coordination, and QA judgment; command hooks own developer and QA
   mechanical validators.
   QA owns code-first Playwright specs/output and final judgment; there is no tester or separate E2E agent.
4. Implementer/QA subagents may not read AGENTS.md, CLAUDE.md, .codex/, .claude/, scripts/, hooks,
   settings, or agent templates directly. Only product-owner, software-architect,
   business-challenger, and technical-challenger may (plus the main thread); others request context
   through the main thread.
EOF

# Live state: active PRDs, ADRs, and feature slices with their State lines, so the
# refreshed context keeps the references implementers/QA need after compaction.
list_states() {
  # $1 label, $2 dir glob, $3 artifact file name inside each dir
  local label="$1" glob="$2" file="$3" d state found=0
  compgen -G "$glob" >/dev/null 2>&1 || return 0
  for d in $glob; do
    [ -d "$d" ] || continue
    if [ "$found" -eq 0 ]; then
      echo "$label"
      found=1
    fi
    state="$(grep -h -m1 'State:' "$d$file" 2>/dev/null | sed 's/^[[:space:]-]*//')"
    printf '  - %s - %s\n' "$(basename "$d")" "${state:-no $file yet}"
  done
}

if compgen -G "memory/PRD/*/" >/dev/null 2>&1 \
  || compgen -G "memory/ADR/*/" >/dev/null 2>&1 \
  || compgen -G "memory/feature/*/" >/dev/null 2>&1; then
  list_states "Active PRDs (memory/PRD/<purpose>/prd.md):" "memory/PRD/*/" "prd.md"
  list_states "Active ADRs (memory/ADR/<purpose>/adr.md):" "memory/ADR/*/" "adr.md"
  list_states "Active feature slices (memory/feature/<feature>/slice.md):" "memory/feature/*/" "slice.md"
else
  echo "No active memory PRDs/ADRs/slices (scaffold / none in progress)."
fi

# A session handoff written before compaction outlives the summarized conversation.
if [ -f "SESSION-HANDOFF.md" ]; then
  echo "A session handoff exists at SESSION-HANDOFF.md - re-read it now if the compacted summary lost the completed / missing work state; it links the parent PRDs, ADRs, and feature slices."
fi

exit 0
