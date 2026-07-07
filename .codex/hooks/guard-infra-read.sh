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
AGENT="$(hook_json_get "$INPUT" "agent_type")"

hook_json_is_coordination_tier "$AGENT" && exit 0

PATH_VALUE="$(hook_json_get "$INPUT" "tool_input.file_path")"
[ -n "$PATH_VALUE" ] || PATH_VALUE="$(hook_json_get "$INPUT" "tool_input.path")"
[ -n "$PATH_VALUE" ] || exit 0
PATH_VALUE="$(hook_json_normalize_path "$PATH_VALUE")"

deny() {
  hook_json_pretool_deny "$1"
  exit 0
}

# Templates and skills are reference material, not agent infrastructure: they carry no hook/
# settings/prompt logic, so every implementer/QA subagent may read them (e.g. QA's own prompt
# points at .codex/templates/categories/e2e.md's worked example, and any subagent may need a
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
