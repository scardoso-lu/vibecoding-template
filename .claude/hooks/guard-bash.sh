#!/usr/bin/env bash
# PreToolUse guard for Bash — blocks operations this project forbids or that are
# plainly destructive. Emits the documented PreToolUse deny decision as JSON.
# Fails open (exit 0, no decision) if jq is unavailable so it never bricks a session.
set -uo pipefail

command -v jq >/dev/null 2>&1 || exit 0

INPUT="$(cat)"
CMD="$(printf '%s' "$INPUT" | jq -r '.tool_input.command // ""')"
[ -z "$CMD" ] && exit 0

deny() {
  jq -n --arg r "$1" \
    '{hookSpecificOutput:{hookEventName:"PreToolUse",permissionDecision:"deny",permissionDecisionReason:$r}}'
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

exit 0
