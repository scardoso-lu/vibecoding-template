#!/usr/bin/env bash
# PreToolUse guard for Edit / Write / MultiEdit — protects files that must not be
# hand-edited. Exit code 2 blocks the tool call and returns the reason to the agent.
# Fails open (exit 0) if jq is unavailable.
set -uo pipefail

command -v jq >/dev/null 2>&1 || exit 0

INPUT="$(cat)"
FP="$(printf '%s' "$INPUT" | jq -r '.tool_input.file_path // ""')"
[ -z "$FP" ] && exit 0

deny() {
  printf 'Blocked by .claude/hooks/guard-edits.sh: %s\n' "$1" >&2
  exit 2
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

exit 0
