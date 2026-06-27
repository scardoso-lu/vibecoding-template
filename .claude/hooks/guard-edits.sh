#!/usr/bin/env bash
# PreToolUse guard for Edit / Write / MultiEdit — protects files that must not be
# hand-edited, and enforces the e2e-explorer's write scope using the subagent
# identity (agent_type) the hook receives. Emits the PreToolUse deny decision as
# JSON. Fails open (exit 0) if jq is unavailable.
set -uo pipefail

command -v jq >/dev/null 2>&1 || exit 0

INPUT="$(cat)"
FP="$(printf '%s' "$INPUT" | jq -r '.tool_input.file_path // ""')"
AGENT="$(printf '%s' "$INPUT" | jq -r '.agent_type // ""')"
[ -z "$FP" ] && exit 0

deny() {
  jq -n --arg r "$1" \
    '{hookSpecificOutput:{hookEventName:"PreToolUse",permissionDecision:"deny",permissionDecisionReason:$r}}'
  exit 0
}

# Compacted, QA-approved historical slices are review-only — never edited as active
# handoffs (see orchestrator compaction rules in CLAUDE.md).
case "$FP" in
  */.claude/feature-memory/history/*|.claude/feature-memory/history/*)
    deny "'.claude/feature-memory/history/' is review-only (compacted QA-approved slices). Do not edit historical summaries." ;;
esac

# Secrets files. .env.example is the tracked template and stays editable.
base="$(basename "$FP")"
case "$base" in
  .env.example)
    : ;;  # allowed
  .env|.env.*)
    deny "editing a secrets file ('$base') is blocked. Put real values in .env by hand; document required keys in .env.example." ;;
esac

# Role scope: the e2e-explorer may write only under .claude/feature-memory/<slice>/e2e/
# (its report and artifacts). Code/test/config fixes route through the orchestrator.
if [ "$AGENT" = "e2e-explorer" ]; then
  case "$FP" in
    */.claude/feature-memory/*/e2e/*|.claude/feature-memory/*/e2e/*)
      : ;;  # allowed
    *)
      deny "the e2e-explorer may write only under .claude/feature-memory/<slice>/e2e/. Log the defect and route the fix through the orchestrator instead of editing '$FP'." ;;
  esac
fi

exit 0
