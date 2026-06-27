#!/usr/bin/env bash
# PreToolUse guard for Bash — blocks operations this project forbids or that are
# plainly destructive. Emits the documented PreToolUse deny decision as JSON.
# Fails open (exit 0, no decision) if JSON parsing is unavailable so it never bricks a session.
set -uo pipefail

HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$HOOK_DIR/hook-json.sh"
hook_json_can_parse || exit 0

INPUT="${HOOK_INPUT_JSON:-}"
[ -n "$INPUT" ] || INPUT="$(cat)"
CMD="$(hook_json_get "$INPUT" "tool_input.command")"
AGENT="$(hook_json_get "$INPUT" "agent_type")"
[ -z "$CMD" ] && exit 0

deny() {
  hook_json_pretool_deny "$1"
  exit 0
}

# Project rule: Chromium + Playwright are pre-installed at $PLAYWRIGHT_BROWSERS_PATH.
# Never re-fetch the browser bundle.
if printf '%s' "$CMD" | grep -Eq '(^|[^[:alnum:]])playwright[[:space:]]+install'; then
  deny "'playwright install' is forbidden — Chromium is pre-installed at \$PLAYWRIGHT_BROWSERS_PATH; drive the existing browser."
fi

# Catastrophic recursive force-deletes of a root / home / cwd target.
# Quotes are stripped first so quoted spellings ("$HOME", "$PWD", "/") match too.
CMD_NOQUOTE="$(printf '%s' "$CMD" | tr -d "\"'")"
has_rmrf() {
  printf '%s' "$1" | grep -Eq 'rm[[:space:]]+-[a-zA-Z]*r[a-zA-Z]*f|rm[[:space:]]+-[a-zA-Z]*f[a-zA-Z]*r|rm[[:space:]]+-[rf][[:space:]]+-[rf]'
}
hits_root() {
  # A target that is the whole root, home, or cwd — bare, with an optional single
  # trailing slash, at a word boundary. Subdir targets like ./build or ~/x are allowed.
  printf '%s' "$1" | grep -Eq '[[:space:]](/|\.|~|\$HOME|\$\{HOME\}|\$PWD|\$\{PWD\}|/\*)/?([[:space:]]|$)'
}
if has_rmrf "$CMD_NOQUOTE" && hits_root "$CMD_NOQUOTE"; then
  deny "refusing a recursive force-delete targeting a root/home/cwd path."
fi

# Force-push can rewrite shared history.
if printf '%s' "$CMD" | grep -Eq 'git[[:space:]]+push' \
   && printf '%s' "$CMD" | grep -Eq '(--force|(^|[[:space:]])-f([[:space:]]|$))'; then
  deny "force-push is blocked. Push normally, or rebase onto a fresh branch and open a new PR."
fi

# Non-orchestrator subagents may not read agent infrastructure through shell
# commands either. Main thread has no agent_type; orchestrator is allowed.
case "$AGENT" in
  ""|orchestrator)
    : ;;
  *)
    if printf '%s' "$CMD" | grep -Eiq '(^|[[:space:];|&])(cat|less|more|head|tail|grep|rg|find|ls|dir|Get-Content|Select-String|Get-ChildItem)([[:space:]]|$)' \
       && printf '%s' "$CMD" | grep -Eiq '(^|[[:space:]"'"'"'./\\])(CLAUDE\.md|AGENTS\.md|\.claude|\.codex|scripts)([[:space:]"'"'"'/\\]|$)'; then
      deny "A '$AGENT' subagent may not inspect agent infrastructure through shell commands. Stop and return ESCALATE so the orchestrator can provide targeted context."
    fi ;;
esac

exit 0
