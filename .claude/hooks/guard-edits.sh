#!/usr/bin/env bash
# PreToolUse guard for Edit / Write / MultiEdit - protects files that must not be
# hand-edited, and enforces QA's write scope using the subagent
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

# Compacted, QA-approved historical slices are review-only - never edited as active
# handoffs (see orchestrator compaction rules in CLAUDE.md).
case "$FP" in
  */feature-memory/history/*|feature-memory/history/*)
    deny "'feature-memory/history/' is review-only (compacted QA-approved slices). Do not edit historical summaries." ;;
esac

# Secrets files. .env.example is the tracked template and stays editable.
base="$(basename "$FP")"
case "$base" in
  .env.example)
    : ;;  # allowed
  .env|.env.*)
    deny "editing a secrets file ('$base') is blocked. Put real values in .env by hand; document required keys in .env.example." ;;
esac

# Role scope: QA may write only deterministic Playwright E2E specs/helpers and the terminal
# slice verdict. Application code, unit tests, config, and non-E2E fixes route through the
# orchestrator.
if [ "$AGENT" = "qa" ]; then
  case "$FP" in
    */frontend/e2e/*|frontend/e2e/*|*/feature-memory/*/slice.md|feature-memory/*/slice.md)
      : ;;  # allowed
    *)
      deny "QA may write only frontend/e2e/** Playwright specs/helpers or the slice.md verdict. Route app code, unit-test, config, and non-E2E fixes through the orchestrator instead of editing '$FP'." ;;
  esac
fi

exit 0

