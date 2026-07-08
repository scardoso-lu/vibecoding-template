#!/usr/bin/env bash
# Stop gate (main thread) - deterministic round-cap check.
#
# The 90%-threshold persona-vote math is deterministically re-derived and hard-blocked on by
# verify-challenge.sh; the round count and the 3-round cap were the one Plan-Loop invariant left to
# an LLM-judged prompt gate (the coordination gate) checking the main thread's own self-reported
# "Round: N of 3" line. A model can miscount rounds and that gate has no ground truth to compare
# against - unlike the vote tally, a round count is a cross-message historical fact, so no single
# message can self-verify it.
#
# This hook gives the round count a real, hook-owned source of truth: a small per-PRD-purpose
# counter file (not memory, not something the main thread writes or can see) that this script
# alone increments, once per occurrence of each challenge step the main thread's own
# "## Coordinate Handoff" declares. The Nth business-challenge (or technical-challenge) for a
# purpose IS round N of that step, whatever the handoff claims - so it hard-blocks when the
# declared "Round: N of 3" lags the hook's own occurrence count (the "stuck at Round 1 forever"
# loop an earlier version of this hook could not see - it only stored the max declared round,
# which a repeated under-declaration never moves), when the hook's own count exceeds 3
# regardless of the declaration, or when the declaration itself exceeds the cap. A declaration
# AHEAD of the count is trusted upward, not blocked: the counter lives in the temp dir, so a
# cleaned temp dir or container restart must degrade to the old fail-open behavior instead of
# false-blocking a legitimate later round.
#
# Assumes transcript_path in the Stop event points at the main session transcript (same assumption
# verify-challenge.sh and context-usage-watch.sh make for their own subagent transcripts). Fails
# open (exit 0) if the transcript can't be read, no Coordinate Handoff is found, or anything
# unexpected happens - it only ever hard-blocks on a round mismatch it could actually compute.
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

    counts = {}
    try:
        with open(state_path, "r", encoding="utf-8") as fh:
            state = json.load(fh)
        raw = state.get("counts", {})
        if isinstance(raw, dict):
            counts = {k: int(v) for k, v in raw.items()}
    except (OSError, ValueError, TypeError):
        counts = {}

    # This declaration IS the next occurrence of this step for this purpose - the hooks own
    # count, independent of what the handoff claims.
    count = counts.get(step, 0) + 1

    if count > 3:
        print(
            f"This is occurrence {count} of the {step} step for purpose \"{purpose}\" "
            f"(declared Round: {declared_round} of 3) - the 3-round cap is exhausted "
            "regardless of the declared number; stop and ask the user instead of "
            "continuing the loop."
        )
        return 1
    if declared_round > 3:
        print(
            f"Coordinate Handoff declares Round: {declared_round} of 3 for purpose "
            f"\"{purpose}\" - the round cap is 3; stop and ask the user instead of "
            "continuing the loop."
        )
        return 1
    if declared_round < count:
        print(
            f"Coordinate Handoff declares Round: {declared_round} of 3 for purpose "
            f"\"{purpose}\", but this is already occurrence {count} of the {step} step "
            "in this loop - the round count regressed or was miscounted; recount before "
            "continuing (the cap is 3 real rounds, not 3 declared ones)."
        )
        return 1

    # Declared ahead of the count means the counter state was lost (temp dir cleaned,
    # container restart) - trust the declaration upward rather than false-block.
    counts[step] = max(count, declared_round)

    try:
        with open(state_path, "w", encoding="utf-8") as fh:
            json.dump({"counts": counts}, fh)
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
  hook_json_stop_block "Round-cap gate failed - the Plan-Loop round count does not match what this hook has independently tracked for this PRD, or exceeds the 3-round cap. The main thread must ask the user rather than continue the loop:"$'\n'"${RESULT}"
fi

exit 0
