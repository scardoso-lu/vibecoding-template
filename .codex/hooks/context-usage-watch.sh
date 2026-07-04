#!/usr/bin/env bash
# PostToolUse watch - session handoff trigger at high context usage.
#
# Reads the newest assistant usage record from the session transcript and, once the
# context window crosses CONTEXT_HANDOFF_THRESHOLD_PCT (default 90%), injects an
# instruction (PostToolUse additionalContext) telling Codex to write the repo-root
# SESSION-HANDOFF.md - what was completed, what is missing, and the PRD/ADR/feature
# slice references - before auto-compaction can eat the working state. Fires once per
# session (temp-dir sentinel keyed by session_id). Fails open: no Python, no
# transcript, or unparseable input means no output and exit 0.
set -uo pipefail

HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$HOOK_DIR/hook-json.sh"

PY="$(hook_json_python)"
[ -n "$PY" ] || exit 0

INPUT="${HOOK_INPUT_JSON:-}"
[ -n "$INPUT" ] || INPUT="$(cat)"
[ -n "$INPUT" ] || exit 0

HOOK_INPUT_JSON="$INPUT" "$PY" <<'PYEOF'
import json
import os
import sys
import tempfile


def main() -> int:
    try:
        event = json.loads(os.environ.get("HOOK_INPUT_JSON") or "{}")
    except Exception:
        return 0

    transcript = event.get("transcript_path") or ""
    session_id = event.get("session_id") or "unknown"
    if not transcript or not os.path.isfile(transcript):
        return 0

    try:
        threshold = float(os.environ.get("CONTEXT_HANDOFF_THRESHOLD_PCT", "90"))
        window = int(os.environ.get("CONTEXT_WINDOW_TOKENS", "200000"))
    except ValueError:
        threshold, window = 90.0, 200000
    if window <= 0:
        return 0

    # Fire once per session: auto-compaction resets usage anyway, and SessionStart
    # (matcher: compact) re-injects the rules afterwards.
    sentinel = os.path.join(tempfile.gettempdir(), f"codex-handoff-notified-{session_id}")
    if os.path.exists(sentinel):
        return 0

    # Tail-read the transcript (it can grow to tens of MB); the newest assistant
    # message carries the cumulative context usage for the session.
    try:
        size = os.path.getsize(transcript)
        with open(transcript, "rb") as fh:
            fh.seek(max(0, size - 262144))
            tail = fh.read().decode("utf-8", "replace")
    except OSError:
        return 0

    used = 0
    for line in reversed(tail.splitlines()):
        line = line.strip()
        if not line or '"usage"' not in line:
            continue
        try:
            record = json.loads(line)
        except Exception:
            continue
        usage = (record.get("message") or {}).get("usage") or record.get("usage") or {}
        if not isinstance(usage, dict) or "input_tokens" not in usage:
            continue
        used = sum(
            int(usage.get(key) or 0)
            for key in (
                "input_tokens",
                "cache_read_input_tokens",
                "cache_creation_input_tokens",
                "output_tokens",
            )
        )
        break

    if used <= 0:
        return 0
    pct = used * 100.0 / window
    if pct < threshold:
        return 0

    try:
        open(sentinel, "w").close()
    except OSError:
        pass  # notify anyway; a repeat warning is better than a lost handoff

    context = (
        f"[context-usage-watch] Context usage is at {pct:.0f}% of the ~{window}-token window "
        f"(threshold {threshold:.0f}%); auto-compaction is imminent. Before doing anything else, "
        "write the session handoff file SESSION-HANDOFF.md at the repo root so the next session "
        "can resume this work. It must contain: "
        "(1) '## Completed' - what this session finished, with concrete file paths; "
        "(2) '## Missing / Not Completed' - the remaining work as a '- [ ]' checklist; "
        "(3) '## References' - the parent PRDs (memory/PRD/<purpose>/prd.md), ADRs "
        "(memory/ADR/<purpose>/adr.md), feature slices (memory/feature/<feature>/slice.md), and "
        "memory/rules.md slugs this work belongs to, or 'none yet' when memory is empty; "
        "(4) '## Next steps' - the exact resume order for the missing items. "
        "Keep it factual - only work that verifiably happened. Then continue the task."
    )
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PostToolUse",
                    "additionalContext": context,
                }
            },
            separators=(",", ":"),
        )
    )
    return 0


sys.exit(main())
PYEOF

exit 0
