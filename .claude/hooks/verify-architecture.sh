#!/usr/bin/env bash
# SubagentStop gate (matcher: software-architect) - deterministic memory/provenance check.
#
# The architecture planning prompt gate is model-judged; a slice.md `Rules:` slug with no matching
# `## <slug>` block in memory/rules.md is a mechanical fact, not a judgment call, and previously was
# only ever caught by guard-harness.sh's Stop hook - which can fire *after* the orchestrator has
# already routed backend-developer/frontend-developer on the same turn, so an implementer without
# MCP access could hit a slug it cannot resolve. This runs the same check right after
# software-architect returns, before technical-challenger or any implementer ever sees the slice.
set -uo pipefail

HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$HOOK_DIR/hook-json.sh"
hook_json_can_parse || exit 0

INPUT="${HOOK_INPUT_JSON:-}"
[ -n "$INPUT" ] || INPUT="$(cat)"

if [ "$(hook_json_get "$INPUT" "stop_hook_active" "false")" = "true" ]; then
  exit 0
fi

AGENT="$(hook_json_get "$INPUT" "agent_type")"
[ "$AGENT" = "software-architect" ] || exit 0

ROOT="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
cd "$ROOT" 2>/dev/null || exit 0
[ -f "scripts/validate/cli.py" ] || exit 0

fails=""
add_fail() { fails="${fails}- ${1}"$'\n'; }

run_validator() {
  local label="$1"
  shift
  local out code
  out="$("$@" 2>&1)"; code=$?
  if [ "$code" != "0" ]; then
    add_fail "${label} failed:"$'\n'"${out}"
  fi
}

# Scoped to "memory" only: this gate owns the architect's own job (slug/PRD/ADR linkage and
# provenance in memory/rules.md and slice.md), not downstream QA artifacts (test-coverage,
# agent-evidence for qa-challenger, etc.) that legitimately don't exist yet at this stage of the
# loop and would otherwise false-block every architecture revision.
run_validator "memory" python scripts/validate/cli.py memory --root .

if [ -n "$fails" ]; then
  hook_json_stop_block "Architecture deterministic gate failed before returning. A slice must never reference (Dependencies -> Rules:) a guideline slug that has no matching, fully-authored ## <slug> block in memory/rules.md - implementer subagents cannot call MCP themselves, so an unresolved slug leaves them stuck. Fetch the missing guideline(s) via get_guideline() and write the block into memory/rules.md before returning. Findings:"$'\n'"${fails}"
fi

exit 0
