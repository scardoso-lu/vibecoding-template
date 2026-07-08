#!/usr/bin/env bash
# PostCompact hook - records that a context compaction happened.
#
# PostCompact fires after compaction completes, but (unlike SessionStart) its stdout is never fed
# back into Claude's context - it is side-effects-only (logging/cleanup). The actual context
# reinjection stays on SessionStart (matcher: compact); see reinject-context.sh. This hook exists
# only to leave a durable, out-of-transcript record of when compactions happen, for later review.
# Fails open (exit 0) if Python is unavailable so it never bricks a session.
set -uo pipefail

HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$HOOK_DIR/hook-json.sh"

PY="$(hook_json_python)"
[ -n "$PY" ] || exit 0

INPUT="${HOOK_INPUT_JSON:-}"
[ -n "$INPUT" ] || INPUT="$(cat)"

HOOK_INPUT_JSON="$INPUT" "$PY" -c '
import json
import os
import tempfile
import time

try:
    event = json.loads(os.environ.get("HOOK_INPUT_JSON") or "{}")
except Exception:
    event = {"parse_error": True}

record = {"logged_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
record.update({k: v for k, v in event.items() if k != "transcript_path"})

log_path = os.path.join(tempfile.gettempdir(), "vibecoding-compact-log.jsonl")
try:
    with open(log_path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, sort_keys=True) + "\n")
except OSError:
    pass
' 2>/dev/null || true

exit 0
