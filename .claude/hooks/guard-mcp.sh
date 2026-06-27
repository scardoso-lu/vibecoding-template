#!/usr/bin/env bash
# PreToolUse guard for the guidelines MCP server — enforces the project's core MCP
# budget rule: only the orchestrator may call the fullstack-guidelines server.
# Registered against the matcher `mcp__fullstack-guidelines__.*`.
#
# Downstream agents already lack MCP tools in their frontmatter; this hook is
# defense-in-depth that survives tool-config drift and uses the subagent identity
# (agent_type) the PreToolUse event carries. Emits the PreToolUse deny decision as
# JSON. Fails open (exit 0) if jq is unavailable.
set -uo pipefail

command -v jq >/dev/null 2>&1 || exit 0

INPUT="$(cat)"
AGENT="$(printf '%s' "$INPUT" | jq -r '.agent_type // ""')"

deny() {
  jq -n --arg r "$1" \
    '{hookSpecificOutput:{hookEventName:"PreToolUse",permissionDecision:"deny",permissionDecisionReason:$r}}'
  exit 0
}

# The orchestrator owns guideline discovery; every other role must ask it for context.
case "$AGENT" in
  backend-developer|frontend-developer|tester|e2e-explorer|qa)
    deny "Only the orchestrator may call the guidelines MCP server. Stop and request targeted context from the orchestrator (see the MCP budget rules in CLAUDE.md) — do not resolve slugs or browse MCP from a '$AGENT' subagent." ;;
esac

exit 0
