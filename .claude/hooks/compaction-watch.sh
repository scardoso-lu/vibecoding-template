#!/usr/bin/env bash
# Stop hook - block when feature-memory compaction is due.
set -uo pipefail

HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$HOOK_DIR/hook-json.sh"
hook_json_can_parse || exit 0

INPUT="${HOOK_INPUT_JSON:-}"
[ -n "$INPUT" ] || INPUT="$(cat)"

if [ "$(hook_json_get "$INPUT" "stop_hook_active" "false")" = "true" ]; then
  exit 0
fi

ROOT="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
cd "$ROOT" 2>/dev/null || exit 0

if [ ! -d "feature-memory" ] || [ ! -f "scripts/validate/compaction.py" ]; then
  exit 0
fi

out="$(python scripts/validate/compaction.py --root . --enforce 2>&1)"
code=$?
if [ "$code" != "0" ]; then
  hook_json_stop_block "Feature-memory compaction is due. Write the review-only historical summary, move the listed QA-approved slice directories under feature-memory/history/, then finish again.\n${out}"
fi

exit 0
