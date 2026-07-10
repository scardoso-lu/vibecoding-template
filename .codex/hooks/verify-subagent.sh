#!/usr/bin/env bash
# SubagentStop gate (matcher: backend-developer|frontend-developer) - deterministic developer checks.
#
# Two distinct failure stances, on purpose - do not unify them:
# - Parser/launcher tier (hook_json_can_parse, run-hook.py) fails OPEN: a broken hook
#   toolchain must never brick a session.
# - Toolchain/dependency tier fails CLOSED: once a stack manifest exists
#   (backend/pyproject.toml, frontend/package.json), a missing ruff/mypy/uv+pytest/
#   validate-tools/pnpm/tsc is a blocking finding, not a silent skip - otherwise the
#   deterministic gate quietly degrades to a no-op on an underprovisioned machine and
#   "the tests passed" means "the tests never ran".
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
ROOT="${CODEX_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
cd "$ROOT" || exit 0

fails=""
add_fail() { fails="${fails}- ${1}"$'\n'; }

have() { command -v "$1" >/dev/null 2>&1; }

run_ok_or_no_tests() {
  local out code
  out="$("$@" 2>&1)"; code=$?
  [ "$code" = "0" ] || [ "$code" = "5" ]
}

check_validate_tools_project_layout() {
  # Fail-closed: a missing validate-tools blocks instead of silently skipping.
  if ! have validate-tools; then
    add_fail "validate-tools is not installed - the compliance gate cannot run (fail-closed toolchain policy; see session-start bootstrap)"
    return
  fi
  validate-tools project-layout . >/dev/null 2>&1 || add_fail "validate-tools project-layout reported a compliance failure"
}

package_has_script() {
  local script="$1"
  grep -Eq "\"${script}\"[[:space:]]*:" frontend/package.json 2>/dev/null
}

case "$AGENT" in
  backend-developer)
    python scripts/validate/cli.py backend --root . >/dev/null 2>&1 || add_fail "backend contract validator reported findings"
    if [ -f backend/pyproject.toml ]; then
      if have ruff; then
        (cd backend && ruff check . >/dev/null 2>&1) || add_fail "backend ruff check reported lint errors"
      else
        add_fail "ruff is not installed - the backend lint gate cannot run (fail-closed toolchain policy)"
      fi
      if [ -d backend/src ]; then
        if have mypy; then
          (cd backend && mypy src >/dev/null 2>&1) || add_fail "backend mypy src reported type errors"
        else
          add_fail "mypy is not installed - the backend type gate cannot run (fail-closed toolchain policy)"
        fi
      fi
      python scripts/validate/cli.py project-layout --root . >/dev/null 2>&1 || add_fail "project layout validator reported findings"
      python scripts/validate/cli.py database --root . >/dev/null 2>&1 || add_fail "database policy validator reported findings"
      python scripts/validate/cli.py migrations --root . >/dev/null 2>&1 || add_fail "migration validator reported findings"
      check_validate_tools_project_layout
      if have uv; then
        (cd backend && run_ok_or_no_tests uv run pytest test -q) || add_fail "backend pytest (uv run) reported failing tests"
      elif have pytest; then
        (cd backend && run_ok_or_no_tests pytest test -q) || add_fail "backend pytest reported failing tests"
      else
        add_fail "neither uv nor pytest is installed - the backend test gate cannot run (fail-closed toolchain policy)"
      fi
    fi
    ;;
  frontend-developer)
    python scripts/validate/cli.py frontend --root . >/dev/null 2>&1 || add_fail "frontend contract validator reported findings"
    if [ -f frontend/package.json ]; then
      if [ -x frontend/node_modules/.bin/tsc ]; then
        (cd frontend && node_modules/.bin/tsc --noEmit >/dev/null 2>&1) || add_fail "frontend tsc --noEmit reported type errors"
      else
        add_fail "frontend/node_modules/.bin/tsc is missing - the frontend type gate cannot run; install dependencies (fail-closed toolchain policy)"
      fi
      python scripts/validate/cli.py project-layout --root . >/dev/null 2>&1 || add_fail "project layout validator reported findings"
      check_validate_tools_project_layout
      if have pnpm; then
        if package_has_script "test:coverage"; then
          pnpm --dir frontend test:coverage >/dev/null 2>&1 || add_fail "frontend pnpm test:coverage reported failing tests"
        elif package_has_script "test"; then
          pnpm --dir frontend test >/dev/null 2>&1 || add_fail "frontend pnpm test reported failing tests"
        fi
      else
        add_fail "pnpm is not installed - the frontend test gate cannot run (fail-closed toolchain policy)"
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
