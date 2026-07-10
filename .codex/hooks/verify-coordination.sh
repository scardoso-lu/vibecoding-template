#!/usr/bin/env bash
# Stop gate (main thread) - deterministic pre-filter for the coordination review.
#
# This replaces the always-on Stop *prompt* hook that model-reviewed every turn: prompt hooks
# cannot be conditioned on Stop (no matchers; `if` applies only to tool events), so that gate
# paid an LLM call on every turn - including plain Q&A turns with no routing in them. This
# command hook is free on those turns: it scans only the current turn's assistant output, and
# only when the turn actually coordinated (a `## Coordinate Handoff` / `## Route Handoff`
# declaration, or a Task/Agent tool_use spawning one of the eight workflow agents) does it
# block once with the coordination checklist, forcing the main thread to self-review against
# AGENTS.md's Orchestration section before finishing. stop_hook_active makes it once per turn.
#
# The deterministic invariants stay owned by their own hooks (verify-round-cap.sh recounts
# rounds; verify-challenge.sh recomputes scores; guard-edits.sh blocks out-of-role writes) -
# this gate covers the judgment-shaped checks those hooks cannot see.
#
# Fails open (exit 0) if the transcript can't be read or nothing coordination-shaped is found.
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

COORDINATED="$(HOOK_TRANSCRIPT="$TRANSCRIPT" "$PY" -c '
import json
import os
import re
import sys

WORKFLOW_AGENTS = {
    "product-owner",
    "business-challenger",
    "software-architect",
    "technical-challenger",
    "backend-developer",
    "frontend-developer",
    "qa-checker",
    "qa-challenger",
}
HANDOFF_RE = re.compile(r"##\s*(Coordinate|Route)\s+Handoff")


def is_real_user_turn(message) -> bool:
    # A genuine user prompt ends the current turn scan; tool_result records also carry
    # role "user" but are part of the assistant turn and must not stop the walk.
    if message.get("role") != "user":
        return False
    content = message.get("content")
    if isinstance(content, str):
        return bool(content.strip())
    if isinstance(content, list):
        return any(
            isinstance(block, dict) and block.get("type") == "text"
            for block in content
        )
    return False


def main() -> int:
    path = os.environ.get("HOOK_TRANSCRIPT", "")
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            lines = fh.readlines()
    except OSError:
        return 0

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
        if not isinstance(message, dict):
            continue
        if is_real_user_turn(message):
            break
        if message.get("role") != "assistant":
            continue
        content = message.get("content")
        blocks = content if isinstance(content, list) else []
        if isinstance(content, str) and HANDOFF_RE.search(content):
            print("yes")
            return 0
        for block in blocks:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "text" and HANDOFF_RE.search(block.get("text", "")):
                print("yes")
                return 0
            if block.get("type") == "tool_use" and block.get("name") in ("Task", "Agent"):
                subagent = (block.get("input") or {}).get("subagent_type", "")
                if subagent in WORKFLOW_AGENTS:
                    print("yes")
                    return 0
    return 0


try:
    sys.exit(main())
except SystemExit:
    raise
except Exception:
    sys.exit(0)
' 2>/dev/null)"

[ "$COORDINATED" = "yes" ] || exit 0

hook_json_stop_block "Coordination gate: this turn declared a Coordinate/Route Handoff or routed workflow agents. Before finishing, self-review the turn against AGENTS.md's Orchestration section: (1) Coordinate and Route steps were not mixed incoherently; (2) the main thread wrote no PRDs/ADRs/slices/rules/code in place of the owning agent; (3) implementation was routed only after BOTH challenge gates reached at least 90 percent in the same round; (4) each challenge-step Coordinate Handoff records the round count (cap 3, then ask the user) and both acceptance percentages when routing; (5) every implementer/QA invocation carried a Do Not Touch scope and a Stop condition; (6) the conditional routing table and the features' Depends on graph were honored. Fix any violation now, then finish again; if every check passes, finish again without changes - this gate fires once per turn."
exit 0
