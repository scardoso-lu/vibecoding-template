#!/usr/bin/env bash
# PostToolUse hook (Edit|Write) — deterministically format/lint the file Codex just
# wrote, so consistent style no longer depends on each agent remembering to run it.
#
# Only uses formatters that are already installed locally — never triggers a network
# install (no `npx` auto-fetch). A no-op when no formatter is present (e.g. the current
# scaffold). PostToolUse cannot block (the edit already happened); this just tidies up.
set -uo pipefail

HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$HOOK_DIR/hook-json.sh"
hook_json_can_parse || exit 0

INPUT="${HOOK_INPUT_JSON:-}"
[ -n "$INPUT" ] || INPUT="$(cat)"
FP="$(hook_json_get "$INPUT" "tool_input.file_path")"
[ -z "$FP" ] && exit 0
[ -f "$FP" ] || exit 0

ROOT="${CODEX_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"

# Resolve a locally-installed prettier without invoking npx (which would fetch it).
prettier_bin() {
  if   [ -x "$ROOT/node_modules/.bin/prettier" ]; then printf '%s' "$ROOT/node_modules/.bin/prettier"
  elif command -v prettier >/dev/null 2>&1;       then command -v prettier
  fi
}

case "$FP" in
  *.py)
    if command -v ruff >/dev/null 2>&1; then
      ruff format "$FP"        >/dev/null 2>&1 || true
      ruff check --fix "$FP"   >/dev/null 2>&1 || true
    fi
    ;;
  *.ts|*.tsx|*.js|*.jsx|*.mjs|*.cjs|*.json|*.jsonc|*.css|*.scss|*.yaml|*.yml)
    P="$(prettier_bin)"
    [ -n "$P" ] && "$P" --write "$FP" >/dev/null 2>&1 || true
    ;;
esac

exit 0
