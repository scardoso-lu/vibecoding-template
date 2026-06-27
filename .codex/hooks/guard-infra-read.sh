#!/usr/bin/env bash
# PreToolUse guard for Read / Grep / Glob / LS. Non-orchestrator subagents may
# not inspect agent infrastructure directly; they must work from orchestrator
# handoffs and feature memory. Main-thread calls have no agent_type and pass.
set -uo pipefail

HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$HOOK_DIR/hook-json.sh"
hook_json_can_parse || exit 0

INPUT="${HOOK_INPUT_JSON:-}"
[ -n "$INPUT" ] || INPUT="$(cat)"
AGENT="$(hook_json_get "$INPUT" "agent_type")"

case "$AGENT" in
  ""|orchestrator)
    exit 0 ;;
esac

PATH_VALUE="$(hook_json_get "$INPUT" "tool_input.file_path")"
[ -n "$PATH_VALUE" ] || PATH_VALUE="$(hook_json_get "$INPUT" "tool_input.path")"
[ -n "$PATH_VALUE" ] || exit 0

deny() {
  hook_json_pretool_deny "$1"
  exit 0
}

case "$PATH_VALUE" in
  CLAUDE.md|AGENTS.md|*/CLAUDE.md|*/AGENTS.md|\
  .claude|.claude/*|*/.claude|*/.claude/*|\
  .codex|.codex/*|*/.codex|*/.codex/*|\
  scripts|scripts/*|*/scripts|*/scripts/*)
    deny "A '$AGENT' subagent may not read agent infrastructure ('$PATH_VALUE'). Stop and return ESCALATE so the orchestrator can provide targeted context." ;;
esac

exit 0
