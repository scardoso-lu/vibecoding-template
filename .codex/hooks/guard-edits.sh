#!/usr/bin/env bash
# PreToolUse guard for Edit / Write / apply_patch — protects files that must not be
# hand-edited, and enforces the e2e-explorer's write scope using the subagent
# identity (agent_type) the hook receives. Emits the PreToolUse deny decision as
# JSON. Fails open (exit 0) if JSON parsing is unavailable.
set -uo pipefail

HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$HOOK_DIR/hook-json.sh"
hook_json_can_parse || exit 0

INPUT="${HOOK_INPUT_JSON:-}"
[ -n "$INPUT" ] || INPUT="$(cat)"
FP="$(hook_json_get "$INPUT" "tool_input.file_path")"
AGENT="$(hook_json_get "$INPUT" "agent_type")"
[ -z "$FP" ] && exit 0

deny() {
  hook_json_pretool_deny "$1"
  exit 0
}

# Compacted, QA-approved historical slices are review-only — never edited as active
# handoffs (see orchestrator compaction rules in AGENTS.md).
case "$FP" in
  */.codex/feature-memory/history/*|.codex/feature-memory/history/*)
    deny "'.codex/feature-memory/history/' is review-only (compacted QA-approved slices). Do not edit historical summaries." ;;
esac

# Secrets files. .env.example is the tracked template and stays editable.
base="$(basename "$FP")"
case "$base" in
  .env.example)
    : ;;  # allowed
  .env|.env.*)
    deny "editing a secrets file ('$base') is blocked. Put real values in .env by hand; document required keys in .env.example." ;;
esac

# Role scope: the e2e-explorer may write only under .codex/feature-memory/<slice>/e2e/
# (its report and artifacts). Code/test/config fixes route through the orchestrator.
if [ "$AGENT" = "e2e-explorer" ]; then
  case "$FP" in
    */.codex/feature-memory/*/e2e/*|.codex/feature-memory/*/e2e/*)
      : ;;  # allowed
    *)
      deny "the e2e-explorer may write only under .codex/feature-memory/<slice>/e2e/. Log the defect and route the fix through the orchestrator instead of editing '$FP'." ;;
  esac
fi

exit 0
