#!/usr/bin/env bash
# PreToolUse guard for the guidelines MCP server - enforces the project's core MCP
# budget rule: only the software-architect may call the fullstack-guidelines server.
# Registered against the matcher `mcp__fullstack-guidelines__.*`.
#
# Downstream agents already lack MCP tools in their frontmatter; this hook is
# defense-in-depth that survives tool-config drift and uses the subagent identity
# (agent_type) the PreToolUse event carries. Emits the PreToolUse deny decision as
# JSON. Fails open (exit 0) if JSON parsing is unavailable.
set -uo pipefail

HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$HOOK_DIR/hook-json.sh"
hook_json_can_parse || exit 0

INPUT="${HOOK_INPUT_JSON:-}"
[ -n "$INPUT" ] || INPUT="$(cat)"
eval "$(hook_json_get_many "$INPUT" AGENT=agent_type TOOL=tool_name)"

deny() {
  hook_json_pretool_deny "$1"
  exit 0
}

# The software-architect owns guideline discovery; every other subagent - workflow roles and
# built-in utility agents alike - must ask for context via the main thread, which routes back
# through the software-architect. Matching "anything that isn't the architect or the main
# thread" (instead of naming the eight roles) means a new or built-in agent type can never
# slip through unlisted.
case "$AGENT" in
  ""|software-architect)
    : ;;
  *)
    deny "Only the software-architect may call the guidelines MCP server. Stop and request targeted context through the main thread (see the MCP budget rules in CLAUDE.md) - do not resolve slugs or browse MCP from a '$AGENT' subagent." ;;
esac

# MCP budget: broad context dumps are banned for normal feature work regardless of caller.
case "$TOOL" in
  *get_all_context*)
    deny "Never call broad context tools such as get_all_context for normal feature work (MCP budget, CLAUDE.md). Fetch only the specific guideline slugs the slice needs via get_metadata/search_guidelines/get_guideline." ;;
esac

# The software-architect's budget is targeted discovery + fetch only: get_metadata (at most once
# per slice), search_guidelines, and get_guideline. Compliance/example/browse tools are out of
# budget for feature work.
if [ "$AGENT" = "software-architect" ]; then
  case "$TOOL" in
    *get_metadata|*search_guidelines|*get_guideline)
      : ;;
    *)
      deny "software-architect may call only get_metadata (once per slice when routing does not identify slugs), search_guidelines, and get_guideline. '$TOOL' is outside the MCP budget; derive slice rules from fetched guidelines instead." ;;
  esac
fi

exit 0
