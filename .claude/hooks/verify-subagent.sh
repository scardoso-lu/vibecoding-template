#!/usr/bin/env bash
# SubagentStop hook (matcher: backend-developer|frontend-developer) — a deterministic
# verification gate. When a developer subagent tries to finish, run the fast static
# checks its agent file already asks for. If they fail, block the stop with the errors
# so the subagent fixes them before returning, instead of relying on it to remember.
#
# Fail-safe: no manifest or no tool installed → allow the stop (no-op on the scaffold).
# Loop-safe: honors stop_hook_active so it can't trap the subagent.
set -uo pipefail

command -v jq >/dev/null 2>&1 || exit 0

INPUT="$(cat)"

# If this stop was already triggered by a previous block, let the subagent finish.
if [ "$(printf '%s' "$INPUT" | jq -r '.stop_hook_active // false')" = "true" ]; then
  exit 0
fi

AGENT="$(printf '%s' "$INPUT" | jq -r '.agent_type // empty')"
ROOT="${CLAUDE_PROJECT_DIR:-$(pwd)}"
cd "$ROOT" || exit 0

fails=""
add_fail() { fails="${fails}- ${1}"$'\n'; }

case "$AGENT" in
  backend-developer)
    if [ -f pyproject.toml ]; then
      if command -v ruff >/dev/null 2>&1 && ! ruff check . >/dev/null 2>&1; then
        add_fail "ruff check . reported lint errors"
      fi
      if command -v mypy >/dev/null 2>&1 && [ -d src ] && ! mypy src >/dev/null 2>&1; then
        add_fail "mypy src reported type errors"
      fi
    fi
    ;;
  frontend-developer)
    if [ -f package.json ] && [ -x node_modules/.bin/tsc ]; then
      if ! node_modules/.bin/tsc --noEmit >/dev/null 2>&1; then
        add_fail "tsc --noEmit reported type errors"
      fi
    fi
    ;;
  *)
    exit 0
    ;;
esac

if [ -n "$fails" ]; then
  reason="Static checks failed before returning. Fix these, then finish:"$'\n'"${fails}Re-run the commands in your task file's Commands section to confirm."
  jq -n --arg r "$reason" '{decision:"block", reason:$r}'
fi

exit 0
