#!/usr/bin/env bash
# SubagentStop gate (matcher: business-challenger|technical-challenger) - deterministic scoring
# check. These two agents are read-only and write no files; their entire output is the
# conversational verdict text. This hook pulls that text out of the subagent's own transcript
# and hard-blocks if the recomputed Persona Votes tally doesn't match the stated Acceptance
# line, or a vote is missing/malformed - see scripts/validate/services/challenge_scoring.py for
# the rationale (an LLM's self-reported percentage is a claim, not evidence).
#
# Assumes transcript_path in the SubagentStop event points at this subagent's own transcript
# (consistent with how it is used elsewhere in this repo, e.g. context-usage-watch.sh). If the
# transcript can't be read or no assistant text is found, this fails open (exit 0) rather than
# risk a false block - it only ever hard-blocks on a verdict it could actually parse and check.
set -uo pipefail

HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$HOOK_DIR/hook-json.sh"
hook_json_can_parse || exit 0

INPUT="${HOOK_INPUT_JSON:-}"
[ -n "$INPUT" ] || INPUT="$(cat)"

if [ "$(hook_json_get "$INPUT" "stop_hook_active" "false")" = "true" ]; then
  exit 0
fi

AGENT="$(hook_json_get "$INPUT" "agent_type")"
case "$AGENT" in
  business-challenger|technical-challenger) : ;;
  *) exit 0 ;;
esac

TRANSCRIPT="$(hook_json_get "$INPUT" "transcript_path")"
[ -n "$TRANSCRIPT" ] && [ -f "$TRANSCRIPT" ] || exit 0

ROOT="${CODEX_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
[ -f "$ROOT/scripts/validate/cli.py" ] || exit 0

PY="$(hook_json_python)"
[ -n "$PY" ] || exit 0

VERDICT_TEXT="$(HOOK_TRANSCRIPT="$TRANSCRIPT" "$PY" -c '
import json
import os

path = os.environ["HOOK_TRANSCRIPT"]
try:
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        lines = fh.readlines()
except OSError:
    lines = []

text = ""
for line in reversed(lines):
    line = line.strip()
    if not line:
        continue
    try:
        record = json.loads(line)
    except Exception:
        continue
    if not isinstance(record, dict):
        continue
    message = record.get("message")
    if not isinstance(message, dict) or message.get("role") != "assistant":
        continue
    content = message.get("content")
    if isinstance(content, str):
        text = content
    elif isinstance(content, list):
        parts = [
            block.get("text", "")
            for block in content
            if isinstance(block, dict) and block.get("type") == "text"
        ]
        text = "\n".join(part for part in parts if part)
    if text.strip():
        break

print(text)
' 2>/dev/null)"

[ -n "$VERDICT_TEXT" ] || exit 0

RESULT="$(cd "$ROOT" 2>/dev/null && printf '%s' "$VERDICT_TEXT" | "$PY" scripts/validate/cli.py challenge-scoring 2>&1)"
CODE=$?

if [ "$CODE" != "0" ]; then
  hook_json_stop_block "Challenge scoring gate failed - the Persona Votes table doesn't match the stated Acceptance line, or is missing/malformed. Fix the vote count/percentage before returning:"$'\n'"${RESULT}"
fi

exit 0
