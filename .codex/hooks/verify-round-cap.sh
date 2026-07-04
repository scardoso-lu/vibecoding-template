#!/usr/bin/env bash
# SubagentStop gate (matcher: orchestrator) - deterministic round-cap check.
#
# The 90%-threshold persona-vote math is deterministically re-derived and hard-blocked on by
# verify-challenge.sh; the round count and the 3-round cap were the one Plan-Loop invariant left to
# an LLM-judged prompt gate (the coordination gate) checking the orchestrator's own self-reported
# "Round: N of 3" line. A model can miscount rounds and that gate has no ground truth to compare
# against - unlike the vote tally, a round count is a cross-message historical fact, so no single
# message can self-verify it.
#
# This hook gives the round count a real, hook-owned source of truth: a small per-PRD-purpose
# counter file (not memory, not something the orchestrator writes or can see) that this script
# alone increments, each time the orchestrator's own "## Coordinate Handoff" declares a
# business-challenge or technical-challenge step. It hard-blocks if the orchestrator's declared
# "Round: N of 3" doesn't match what the hook itself has tracked, or exceeds the cap.
#
# Assumes transcript_path in the SubagentStop event points at this subagent's own transcript (same
# assumption verify-challenge.sh and context-usage-watch.sh already make). Fails open (exit 0) if
# the transcript can't be read, no Coordinate Handoff is found, or anything unexpected happens - it
# only ever hard-blocks on a round mismatch it could actually compute.
#
# Known limitation: the counter is keyed by the PRD purpose slug and has no expiry, so if a
# purpose slug is ever reused for unrelated future work after the original loop finished, a false
# "regressed" block is possible. Purpose slugs are meant to be unique per initiative, so this is an
# acceptable trade-off rather than a reason to add cross-session bookkeeping.
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
[ "$AGENT" = "orchestrator" ] || exit 0

TRANSCRIPT="$(hook_json_get "$INPUT" "transcript_path")"
[ -n "$TRANSCRIPT" ] && [ -f "$TRANSCRIPT" ] || exit 0

PY="$(hook_json_python)"
[ -n "$PY" ] || exit 0

RESULT="$(HOOK_TRANSCRIPT="$TRANSCRIPT" "$PY" -c '
import hashlib
import json
import os
import re
import sys
import tempfile


def main() -> int:
    path = os.environ.get("HOOK_TRANSCRIPT", "")
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            lines = fh.readlines()
    except OSError:
        return 0

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

    if not text.strip():
        return 0

    handoff = re.search(r"##\s*Coordinate Handoff(.*?)(?:\n##\s|\Z)", text, re.S)
    if not handoff:
        return 0
    block_text = handoff.group(1)

    step_m = re.search(r"-\s*Step:\s*([A-Za-z-]+)", block_text)
    round_m = re.search(r"-\s*Round:\s*(\d+)\s*of\s*3", block_text)
    step = step_m.group(1).strip().lower() if step_m else ""
    if step not in ("business-challenge", "technical-challenge"):
        return 0
    if not round_m:
        print(
            "Coordinate Handoff declares Step: " + step + " but has no parseable "
            "\"Round: <n> of 3\" line."
        )
        return 1
    declared_round = int(round_m.group(1))

    artifacts_m = re.search(r"-\s*Artifacts:.*?memory/PRD/([^/`\s]+)/prd\.md", block_text)
    purpose = artifacts_m.group(1) if artifacts_m else "default"
    key = hashlib.sha1(purpose.encode("utf-8")).hexdigest()[:16]
    state_path = os.path.join(tempfile.gettempdir(), f"vibecoding-round-state-{key}.json")

    max_seen = 0
    try:
        with open(state_path, "r", encoding="utf-8") as fh:
            state = json.load(fh)
        max_seen = int(state.get("max_round_seen", 0))
    except (OSError, ValueError, TypeError):
        max_seen = 0

    if declared_round > 3:
        print(
            f"Coordinate Handoff declares Round: {declared_round} of 3 for purpose "
            f"\"{purpose}\" - the round cap is 3; stop and ask the user instead of "
            "continuing the loop."
        )
        return 1
    if declared_round < max_seen:
        print(
            f"Coordinate Handoff declares Round: {declared_round} of 3 for purpose "
            f"\"{purpose}\", but round {max_seen} was already reached earlier in this "
            "loop - the round count regressed or was miscounted."
        )
        return 1

    try:
        with open(state_path, "w", encoding="utf-8") as fh:
            json.dump({"max_round_seen": max(max_seen, declared_round)}, fh)
    except OSError:
        pass
    return 0


try:
    sys.exit(main())
except SystemExit:
    raise
except Exception:
    sys.exit(0)
' 2>&1)"
CODE=$?

if [ "$CODE" != "0" ]; then
  hook_json_stop_block "Round-cap gate failed - the Plan-Loop round count does not match what this hook has independently tracked for this PRD, or exceeds the 3-round cap:"$'\n'"${RESULT}"
fi

exit 0
