#!/usr/bin/env bash
# PreToolUse guard for Read / Grep / Glob / LS. Implementer/QA subagents may not
# inspect agent infrastructure directly; they must work from main-thread handoffs
# and memory. The coordination tier is allowed, as is the main thread (no agent_type).
set -uo pipefail

HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$HOOK_DIR/hook-json.sh"
hook_json_can_parse || exit 0

INPUT="${HOOK_INPUT_JSON:-}"
[ -n "$INPUT" ] || INPUT="$(cat)"
eval "$(hook_json_get_many "$INPUT" AGENT=agent_type TOOL=tool_name FP=tool_input.file_path DIR=tool_input.path)"

hook_json_is_coordination_tier "$AGENT" && exit 0
# Built-in utility subagents (Explore, Plan, general-purpose, ...) are spawned by the main
# thread and read on its behalf; guard-edits.sh separately keeps them out of memory/** writes.
hook_json_is_builtin_utility_agent "$AGENT" && exit 0

deny() {
  hook_json_pretool_deny "$1"
  exit 0
}

PATH_VALUE="$FP"
[ -n "$PATH_VALUE" ] || PATH_VALUE="$DIR"
if [ -z "$PATH_VALUE" ]; then
  # Grep/Glob default to the repo root when no path is given - a scope that includes the very
  # agent infrastructure this guard exists to protect. Don't let "no path" mean "every path".
  case "$TOOL" in
    Grep|Glob)
      deny "A '$AGENT' subagent may not run a pathless $TOOL - the default scope is the repo root, which includes agent infrastructure (.claude/, .codex/, scripts/, CLAUDE.md, AGENTS.md). Pass an explicit path inside your slice scope, or return ESCALATE for targeted context." ;;
  esac
  exit 0
fi
PATH_VALUE="$(hook_json_normalize_path "$PATH_VALUE")"

# Templates and skills are reference material, not agent infrastructure: they carry no hook/
# settings/prompt logic, so every implementer/QA subagent may read them (e.g. QA's own prompt
# points at .claude/templates/categories/e2e.md's worked example, and any subagent may need a
# skill's docs). Everything else under .claude/.codex stays blocked below.
hook_json_is_reference_material_path "$PATH_VALUE" && exit 0

case "$PATH_VALUE" in
  CLAUDE.md|AGENTS.md|*/CLAUDE.md|*/AGENTS.md|\
  .claude|.claude/*|*/.claude|*/.claude/*|\
  .codex|.codex/*|*/.codex|*/.codex/*|\
  scripts|scripts/*|*/scripts|*/scripts/*)
    deny "A '$AGENT' subagent may not read agent infrastructure ('$PATH_VALUE'). Stop and return ESCALATE so the main thread can provide targeted context." ;;
esac

exit 0
