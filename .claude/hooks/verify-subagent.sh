#!/usr/bin/env bash
# SubagentStop gate (matcher: backend-developer|frontend-developer) - deterministic developer checks.
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
ROOT="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
cd "$ROOT" || exit 0

fails=""
add_fail() { fails="${fails}- ${1}"$'\n'; }

have() { command -v "$1" >/dev/null 2>&1; }

run_ok_or_no_tests() {
  local out code
  out="$("$@" 2>&1)"; code=$?
  [ "$code" = "0" ] || [ "$code" = "5" ]
}

run_validate_tools_project_layout() {
  have validate-tools || return 0
  validate-tools project-layout . >/dev/null 2>&1
}

package_has_script() {
  local script="$1"
  grep -Eq "\"${script}\"[[:space:]]*:" frontend/package.json 2>/dev/null
}

case "$AGENT" in
  backend-developer)
    python scripts/validate/backend.py --root . >/dev/null 2>&1 || add_fail "backend contract validator reported findings"
    if [ -f backend/pyproject.toml ]; then
      have ruff && ! (cd backend && ruff check . >/dev/null 2>&1) && add_fail "backend ruff check reported lint errors"
      have mypy && [ -d backend/src ] && ! (cd backend && mypy src >/dev/null 2>&1) && add_fail "backend mypy src reported type errors"
      python scripts/validate/project-layout.py --root . >/dev/null 2>&1 || add_fail "project layout validator reported findings"
      python scripts/validate/database.py --root . >/dev/null 2>&1 || add_fail "database policy validator reported findings"
      python scripts/validate/migrations.py --root . >/dev/null 2>&1 || add_fail "migration validator reported findings"
      ! run_validate_tools_project_layout && add_fail "validate-tools project-layout reported a compliance failure"
      if have uv; then
        (cd backend && run_ok_or_no_tests uv run pytest test -q) || add_fail "backend pytest (uv run) reported failing tests"
      elif have pytest; then
        (cd backend && run_ok_or_no_tests pytest test -q) || add_fail "backend pytest reported failing tests"
      fi
    fi
    ;;
  frontend-developer)
    python scripts/validate/frontend.py --root . >/dev/null 2>&1 || add_fail "frontend contract validator reported findings"
    if [ -f frontend/package.json ]; then
      [ -x frontend/node_modules/.bin/tsc ] && ! (cd frontend && node_modules/.bin/tsc --noEmit >/dev/null 2>&1) && add_fail "frontend tsc --noEmit reported type errors"
      python scripts/validate/project-layout.py --root . >/dev/null 2>&1 || add_fail "project layout validator reported findings"
      ! run_validate_tools_project_layout && add_fail "validate-tools project-layout reported a compliance failure"
      if have pnpm; then
        if package_has_script "test:coverage"; then
          pnpm --dir frontend test:coverage >/dev/null 2>&1 || add_fail "frontend pnpm test:coverage reported failing tests"
        elif package_has_script "test"; then
          pnpm --dir frontend test >/dev/null 2>&1 || add_fail "frontend pnpm test reported failing tests"
        fi
      fi
    fi
    ;;
  *)
    exit 0
    ;;
esac

if [ -n "$fails" ]; then
  reason="Deterministic gate failed before returning. Fix these, then finish:"$'\n'"${fails}These run automatically on finish - you do not need to ask anyone to run them."
  hook_json_stop_block "$reason"
fi

exit 0
