#!/usr/bin/env bash
# Stop hook - run targeted workflow validators for changed areas.
set -uo pipefail

HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$HOOK_DIR/hook-json.sh"
hook_json_can_parse || exit 0
command -v git >/dev/null 2>&1 || exit 0

INPUT="${HOOK_INPUT_JSON:-}"
[ -n "$INPUT" ] || INPUT="$(cat)"

if [ "$(hook_json_get "$INPUT" "stop_hook_active" "false")" = "true" ]; then
  exit 0
fi

ROOT="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
cd "$ROOT" 2>/dev/null || exit 0
[ -f "scripts/validate/workflow.py" ] || exit 0

changed="$(git status --porcelain 2>/dev/null | sed 's/^...//' | sed 's#\\#/#g')"
[ -n "$changed" ] || exit 0

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

matches_any() {
  local pattern
  for pattern in "$@"; do
    printf '%s\n' "$changed" | grep -Eq "$pattern" && return 0
  done
  return 1
}

if matches_any '^(AGENTS\.md|CLAUDE\.md|\.codex/agents/|\.claude/agents/|\.codex/templates/|\.claude/templates/|\.codex/hooks/|\.claude/hooks/|scripts/validate/)'; then
  run_validator "workflow" python scripts/validate/workflow.py --root .
else
  if matches_any '^(feature-memory/|\.codex/templates/|\.claude/templates/)'; then
    run_validator "feature-memory" python scripts/validate/feature-memory.py --root .
    run_validator "test-coverage" python scripts/validate/test-coverage.py --root .
    run_validator "e2e-coverage" python scripts/validate/e2e-coverage.py --root .
    run_validator "qa-evidence" python scripts/validate/qa-evidence.py --root .
  fi

  if matches_any '^(feature-memory/|frontend/e2e/)'; then
    run_validator "playwright-stories" python scripts/validate/playwright-stories.py --root .
    run_validator "qa" python scripts/validate/qa.py --root .
  fi

  if matches_any '^(backend/|docker-compose[^/]*\.ya?ml$)'; then
    run_validator "project-layout" python scripts/validate/project-layout.py --root .
    run_validator "database" python scripts/validate/database.py --root .
    run_validator "migrations" python scripts/validate/migrations.py --root .
    run_validator "backend" python scripts/validate/backend.py --root .
  fi

  if matches_any '^(frontend/|docker-compose[^/]*\.ya?ml$)'; then
    run_validator "project-layout" python scripts/validate/project-layout.py --root .
    run_validator "frontend" python scripts/validate/frontend.py --root .
  fi
fi

if [ -n "$fails" ]; then
  hook_json_stop_block "Workflow validation failed. Fix these deterministic findings, then finish again:"$'\n'"${fails}"
fi

exit 0
