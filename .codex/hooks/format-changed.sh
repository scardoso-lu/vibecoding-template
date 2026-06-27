#!/usr/bin/env bash
# Stop hook — format files created/modified via Bash that the PostToolUse formatter never saw.
#
# auto-format.sh only fires on Edit/Write, so files written through Bash (Alembic
# --autogenerate migrations, codegen, scaffolding) skip formatting. Once per turn this scans the
# working tree and routes each changed/untracked file through auto-format.sh, keeping a single
# source of truth for the ruff/prettier mapping. Never blocks; a no-op when no formatter exists.
set -uo pipefail

HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$HOOK_DIR/hook-json.sh"
hook_json_can_parse || exit 0
command -v git >/dev/null 2>&1 || exit 0

INPUT="${HOOK_INPUT_JSON:-}"
[ -n "$INPUT" ] || INPUT="$(cat)"
# If this stop was already triggered by a previous block, do nothing.
if [ "$(hook_json_get "$INPUT" "stop_hook_active" "false")" = "true" ]; then
  exit 0
fi

ROOT="${CODEX_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
cd "$ROOT" || exit 0
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || exit 0

AUTO_FORMAT="$ROOT/.codex/hooks/auto-format.sh"
[ -x "$AUTO_FORMAT" ] || [ -f "$AUTO_FORMAT" ] || exit 0

# Changed (tracked) + untracked files, NUL-delimited so paths with spaces survive.
while IFS= read -r -d '' entry; do
  # Porcelain lines are "XY <path>"; strip the 3-char status prefix.
  path="${entry:3}"
  [ -n "$path" ] || continue
  [ -f "$path" ] || continue
  printf '{"tool_input":{"file_path":"%s"}}' "$ROOT/$path" | bash "$AUTO_FORMAT" >/dev/null 2>&1 || true
done < <(git status --porcelain -z 2>/dev/null)

exit 0
