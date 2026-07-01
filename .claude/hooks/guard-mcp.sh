#!/usr/bin/env bash
# PreToolUse guard for the guidelines MCP server - enforces the project's core MCP
# budget rule: only the orchestrator may call the fullstack-guidelines server.
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
AGENT="$(hook_json_get "$INPUT" "agent_type")"

deny() {
  hook_json_pretool_deny "$1"
  exit 0
}

# The orchestrator owns guideline discovery; every other role must ask it for context.
case "$AGENT" in
  backend-developer|frontend-developer|qa)
    deny "Only the orchestrator may call the guidelines MCP server. Stop and request targeted context from the orchestrator (see the MCP budget rules in CLAUDE.md) - do not resolve slugs or browse MCP from a '$AGENT' subagent." ;;
esac

exit 0
