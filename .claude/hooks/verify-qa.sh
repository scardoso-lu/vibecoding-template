#!/usr/bin/env bash
# SubagentStop gate (matcher: qa-checker) - deterministic QA artifact checks.
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
[ "$AGENT" = "qa-checker" ] || exit 0

ROOT="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
cd "$ROOT" 2>/dev/null || exit 0
[ -f "scripts/validate/cli.py" ] || exit 0

fails=""
add_fail() { fails="${fails}- ${1}"$'\n'; }

run_validator() {
  local label="$1"
  shift
  local out code
  out="$("$@" 2>&1)"; code=$?
  if [ "$code" != "0" ]; then
    add_fail "${label} failed:"$'\n'"${out}"
  fi
}

run_validator "qa" python scripts/validate/cli.py qa --root .
run_validator "agent-evidence" python scripts/validate/cli.py agent-evidence --root .
run_validator "playwright-stories" python scripts/validate/cli.py playwright-stories --root .
run_validator "test-coverage" python scripts/validate/cli.py test-coverage --root .
run_validator "e2e-coverage" python scripts/validate/cli.py e2e-coverage --root .
run_validator "qa-evidence" python scripts/validate/cli.py qa-evidence --root .

if [ -n "$fails" ]; then
  hook_json_stop_block "QA deterministic gate failed before returning. Only fix findings inside qa-checker's write scope (frontend/e2e/** specs/helpers, e2e-coverage.json, qa-evidence.json via the real gate command, or the slice.md verdict). A finding about a missing backend/frontend implementation file, unit test, or agent-evidence.json is not yours to fix: return BLOCKED naming it and route it through the main thread to the responsible agent instead. Never hand-author qa-evidence.json or a spec that can't actually run just to silence this gate. Findings:"$'\n'"${fails}"
fi

exit 0
