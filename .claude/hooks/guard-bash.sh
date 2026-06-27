#!/usr/bin/env bash
# PreToolUse guard for Bash — blocks operations this project forbids or that are
# plainly destructive. Exit code 2 blocks the tool call and feeds the reason on
# stderr back to the agent. Fails open (exit 0) if jq is unavailable so the guard
# can never brick a session.
set -uo pipefail

command -v jq >/dev/null 2>&1 || exit 0

INPUT="$(cat)"
CMD="$(printf '%s' "$INPUT" | jq -r '.tool_input.command // ""')"
[ -z "$CMD" ] && exit 0

deny() {
  printf 'Blocked by .claude/hooks/guard-bash.sh: %s\n' "$1" >&2
  exit 2
}

# Project rule: Chromium + Playwright are pre-installed at $PLAYWRIGHT_BROWSERS_PATH.
# Never re-fetch the browser bundle.
if printf '%s' "$CMD" | grep -Eq '(^|[^[:alnum:]])playwright[[:space:]]+install'; then
  deny "'playwright install' is forbidden — Chromium is pre-installed at \$PLAYWRIGHT_BROWSERS_PATH; drive the existing browser."
fi

# Catastrophic recursive force-deletes of a root / home / cwd target.
has_rmrf() {
  printf '%s' "$1" | grep -Eq 'rm[[:space:]]+-[a-zA-Z]*r[a-zA-Z]*f|rm[[:space:]]+-[a-zA-Z]*f[a-zA-Z]*r|rm[[:space:]]+-[rf][[:space:]]+-[rf]'
}
hits_root() {
  printf '%s' "$1" | grep -Eq '[[:space:]](/|~|\$HOME|/\*)([[:space:]]|$)'
}
if has_rmrf "$CMD" && hits_root "$CMD"; then
  deny "refusing a recursive force-delete targeting a root/home/cwd path."
fi

# Force-push can rewrite shared history.
if printf '%s' "$CMD" | grep -Eq 'git[[:space:]]+push' \
   && printf '%s' "$CMD" | grep -Eq '(--force|(^|[[:space:]])-f([[:space:]]|$))'; then
  deny "force-push is blocked. Push normally, or rebase onto a fresh branch and open a new PR."
fi

exit 0
