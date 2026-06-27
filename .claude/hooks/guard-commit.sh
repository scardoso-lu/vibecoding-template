#!/usr/bin/env bash
# PreToolUse guard (Bash, if: Bash(git commit *)) — defense-in-depth secrets gate on commits.
#
# The SubagentStop gate only covers developer subagents; a `git commit` from the main thread runs
# no check. Before a commit, scan the *staged diff* (only what is about to be committed) for
# high-signal secret material and deny with the documented PreToolUse decision on a finding.
#
# Patterns are structural (private keys, AWS keys) and matched only on added lines, to stay
# near-zero false-positive — a generic password/token regex (or a whole-repo `validate-tools
# secrets` scan) would flag this repo's own security tooling and block its commits. Broad,
# whole-tree secret scanning already runs in the SubagentStop gate via `validate-tools run`.
# Fails open (exit 0) without jq/git.
set -uo pipefail

command -v jq >/dev/null 2>&1 || exit 0
command -v git >/dev/null 2>&1 || exit 0

INPUT="$(cat)"
CMD="$(printf '%s' "$INPUT" | jq -r '.tool_input.command // ""')"

# Only act on git commits (the `if` field pre-filters, but it fails open, so re-check here).
printf '%s' "$CMD" | grep -Eq '(^|[^[:alnum:]])git[[:space:]]+commit([[:space:]]|$)' || exit 0

ROOT="${CLAUDE_PROJECT_DIR:-$(pwd)}"
cd "$ROOT" 2>/dev/null || exit 0
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || exit 0

deny() {
  jq -n --arg r "$1" \
    '{hookSpecificOutput:{hookEventName:"PreToolUse",permissionDecision:"deny",permissionDecisionReason:$r}}'
  exit 0
}

# Collect the added lines this commit would introduce: staged always, plus tracked-unstaged when
# the command uses -a / --all (git commit -a bypasses the index).
added="$(git diff --cached -U0 --no-color 2>/dev/null | grep '^+' || true)"
if printf '%s' "$CMD" | grep -Eq 'git[[:space:]]+commit[[:space:]].*(-[a-zA-Z]*a|--all)'; then
  added="${added}"$'\n'"$(git diff -U0 --no-color 2>/dev/null | grep '^+' || true)"
fi

scan() { printf '%s' "$added" | grep -Eq -e "$1"; }

if scan '-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----'; then
  deny "Blocked commit: the staged diff contains a private key block. Remove it; keep secrets in .env (gitignored)."
fi
if scan 'AKIA[0-9A-Z]{16}'; then
  deny "Blocked commit: the staged diff contains an AWS access key id (AKIA…). Remove it and rotate the key."
fi
if scan 'aws_secret_access_key[[:space:]]*[=:][[:space:]]*.?[A-Za-z0-9/+]{30,}'; then
  deny "Blocked commit: the staged diff contains an AWS secret access key. Remove it and rotate the key."
fi

exit 0
