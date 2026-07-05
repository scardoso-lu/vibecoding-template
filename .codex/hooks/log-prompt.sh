#!/usr/bin/env bash
# UserPromptSubmit hook - durably log every raw user prompt with a timestamp.
#
# The original prompt text otherwise only lives in the session transcript, which is lost once
# a session ends (or is summarized away by compaction). This appends every prompt, verbatim,
# with an ISO-8601 timestamp and session id, to PROMPT-LOG.md at the repo root - the same
# durability model as SESSION-HANDOFF.md (gitignored, survives within a persistent workspace
# across sessions/compaction; in a fresh clone there is no history to recover, same as today).
# Never blocks and never injects context: this is a side-effect-only append, so it always exits 0
# with no stdout. Fails open (no Python, no JSON, no prompt field) rather than ever blocking input.
set -uo pipefail

HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$HOOK_DIR/hook-json.sh"

PY="$(hook_json_python)"
[ -n "$PY" ] || exit 0

INPUT="${HOOK_INPUT_JSON:-}"
[ -n "$INPUT" ] || INPUT="$(cat)"
[ -n "$INPUT" ] || exit 0

ROOT="${CODEX_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"

HOOK_INPUT_JSON="$INPUT" HOOK_LOG_ROOT="$ROOT" "$PY" <<'PYEOF'
import json
import os
from datetime import datetime, timezone

def main() -> int:
    try:
        event = json.loads(os.environ.get("HOOK_INPUT_JSON") or "{}")
    except Exception:
        return 0

    prompt = event.get("prompt")
    if not isinstance(prompt, str) or not prompt.strip():
        return 0

    session_id = event.get("session_id") or "unknown"
    root = os.environ.get("HOOK_LOG_ROOT") or "."
    log_path = os.path.join(root, "PROMPT-LOG.md")
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    is_new = not os.path.exists(log_path)
    try:
        with open(log_path, "a", encoding="utf-8") as fh:
            if is_new:
                fh.write(
                    "# Prompt Log\n\n"
                    "Every user prompt this workspace received, in order, with a timestamp - so "
                    "the original ask survives session end/compaction even when nothing else "
                    "does. Gitignored: durable per-workspace, not per-clone.\n\n"
                )
            fh.write(f"## {timestamp} (session {session_id})\n\n")
            fh.write(prompt.strip() + "\n\n")
    except OSError:
        return 0
    return 0


raise SystemExit(main())
PYEOF

exit 0
