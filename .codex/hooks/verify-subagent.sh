#!/usr/bin/env bash
# SubagentStop gate (matcher: backend-developer|frontend-developer) — the deterministic
# verification that used to be spread across the tester and the QA validator budget.
#
# When a developer subagent tries to finish, run every deterministic check that applies
# and is installed, then block the stop with the aggregated failures so the subagent fixes
# them before returning. This is the single source of "is the mechanical work correct":
#   backend:  ruff (lint+format) · mypy (types) · validate-tools run (validators) · pytest
#   frontend: tsc --noEmit (types) · validate-tools run · pnpm test
#
# Fail-safe: a missing manifest or missing tool is skipped (no-op on the scaffold).
# Loop-safe: honors stop_hook_active, and Codex caps consecutive Stop-blocks at 8.
set -uo pipefail

HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$HOOK_DIR/hook-json.sh"
hook_json_can_parse || exit 0

INPUT="${HOOK_INPUT_JSON:-}"
[ -n "$INPUT" ] || INPUT="$(cat)"

# If this stop was already triggered by a previous block, let the subagent finish.
if [ "$(hook_json_get "$INPUT" "stop_hook_active" "false")" = "true" ]; then
  exit 0
fi

AGENT="$(hook_json_get "$INPUT" "agent_type")"
ROOT="${CODEX_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
cd "$ROOT" || exit 0

fails=""
add_fail() { fails="${fails}- ${1}"$'\n'; }

have() { command -v "$1" >/dev/null 2>&1; }

# pytest exit 5 = "no tests collected" — not a failure for our gate.
run_pytest() {
  local out code
  out="$("$@" 2>&1)"; code=$?
  [ "$code" = "0" ] || [ "$code" = "5" ]
}

run_validators() {
  # validate-tools run = full batch compliance (secrets, imports, migration, env, …).
  # Non-zero exit or a "fail" status is a blocking finding.
  have validate-tools || return 0
  validate-tools run >/dev/null 2>&1
}

case "$AGENT" in
  backend-developer)
    if [ -f pyproject.toml ]; then
      have ruff && ! ruff check . >/dev/null 2>&1 && add_fail "ruff check . reported lint errors"
      have mypy && [ -d src ] && ! mypy src >/dev/null 2>&1 && add_fail "mypy src reported type errors"
      ! run_validators && add_fail "validate-tools run reported a compliance failure"
      if have pytest; then
        run_pytest pytest -q || add_fail "pytest reported failing tests"
      elif have uv; then
        run_pytest uv run pytest -q || add_fail "pytest (uv run) reported failing tests"
      fi
    fi
    ;;
  frontend-developer)
    if [ -f package.json ]; then
      [ -x node_modules/.bin/tsc ] && ! node_modules/.bin/tsc --noEmit >/dev/null 2>&1 && add_fail "tsc --noEmit reported type errors"
      ! run_validators && add_fail "validate-tools run reported a compliance failure"
      if [ -x node_modules/.bin/vitest ] || grep -q '"test"' package.json 2>/dev/null; then
        if have pnpm && ! pnpm test >/dev/null 2>&1; then add_fail "pnpm test reported failing tests"; fi
      fi
    fi
    ;;
  *)
    exit 0
    ;;
esac

if [ -n "$fails" ]; then
  reason="Deterministic gate failed before returning. Fix these, then finish:"$'\n'"${fails}These run automatically on finish — you do not need to ask anyone to run them."
  hook_json_stop_block "$reason"
fi

exit 0
