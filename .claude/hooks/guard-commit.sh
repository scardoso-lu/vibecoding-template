#!/usr/bin/env bash
# PreToolUse guard (Bash, if: Bash(git commit *)) — defense-in-depth secrets gate on commits.
#
# The SubagentStop gate only covers developer subagents; a `git commit` from the main thread runs
# no check. Before a commit, scan the *staged diff* (only what is about to be committed) for
# high-signal secret material and deny with the documented PreToolUse decision on a finding.
#
# Patterns are structural (private keys, vendor-prefixed API keys, Azure connection
# strings/SAS tokens, DB-URI credentials, JWTs) and matched only on added lines, to stay
# near-zero false-positive — a bare, unstructured `password|secret|token` regex (or a whole-repo
# `validate-tools secrets` scan) would flag this repo's own security tooling and block its
# commits. The one exception is the credential-logging check: it matches on *variable name*
# next to a print/log call (e.g. logging a variable named like a user's login secret), because logging a
# credential-shaped variable is a developer mistake worth catching regardless of its value.
# Broad, whole-tree secret scanning already runs in the SubagentStop gate via `validate-tools run`.
# Fails open (exit 0) without JSON parsing/git.
set -uo pipefail

HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$HOOK_DIR/hook-json.sh"
hook_json_can_parse || exit 0
command -v git >/dev/null 2>&1 || exit 0

INPUT="${HOOK_INPUT_JSON:-}"
[ -n "$INPUT" ] || INPUT="$(cat)"
CMD="$(hook_json_get "$INPUT" "tool_input.command")"

# Only act on git commits (the `if` field pre-filters, but it fails open, so re-check here).
printf '%s' "$CMD" | grep -Eq '(^|[^[:alnum:]])git[[:space:]]+commit([[:space:]]|$)' || exit 0

ROOT="${CLAUDE_PROJECT_DIR:-$(pwd)}"
cd "$ROOT" 2>/dev/null || exit 0
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || exit 0

deny() {
  hook_json_pretool_deny "$1"
  exit 0
}

# Collect the added lines this commit would introduce: staged always, plus tracked-unstaged when
# the command uses -a / --all (git commit -a bypasses the index).
added="$(git diff --cached -U0 --no-color 2>/dev/null | grep '^+' || true)"
if printf '%s' "$CMD" | grep -Eq 'git[[:space:]]+commit[[:space:]].*(-[a-zA-Z]*a|--all)'; then
  added="${added}"$'\n'"$(git diff -U0 --no-color 2>/dev/null | grep '^+' || true)"
fi

scan() { printf '%s' "$added" | grep -Eq -e "$1"; }
scani() { printf '%s' "$added" | grep -Eiq -e "$1"; }

if scan '-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----'; then
  deny "Blocked commit: the staged diff contains a private key block. Remove it; keep secrets in .env (gitignored)."
fi
if scan 'AKIA[0-9A-Z]{16}'; then
  deny "Blocked commit: the staged diff contains an AWS access key id (AKIA…). Remove it and rotate the key."
fi
if scan 'aws_secret_access_key[[:space:]]*[=:][[:space:]]*.?[A-Za-z0-9/+]{30,}'; then
  deny "Blocked commit: the staged diff contains an AWS secret access key. Remove it and rotate the key."
fi

# Vendor-prefixed API keys - each prefix is specific enough to a real provider format that a
# false positive is effectively impossible (same structural-match philosophy as the AWS checks
# above).
if scan '(sk|pk)_(live|test)_[0-9A-Za-z]{16,}'; then
  deny "Blocked commit: the staged diff contains a Stripe-shaped API key (sk_live_/pk_live_/sk_test_/pk_test_...). Remove it and rotate the key."
fi
if scan 'gh[pousr]_[0-9A-Za-z]{36,}|github_pat_[0-9A-Za-z_]{22,}'; then
  deny "Blocked commit: the staged diff contains a GitHub token (ghp_/gho_/ghu_/ghs_/ghr_/github_pat_...). Remove it and rotate the token."
fi
if scan 'xox[baprs]-[0-9A-Za-z-]{10,}'; then
  deny "Blocked commit: the staged diff contains a Slack token (xoxb-/xoxp-/xoxa-/xoxr-/xoxs-...). Remove it and rotate the token."
fi
if scan 'AIza[0-9A-Za-z_-]{35}'; then
  deny "Blocked commit: the staged diff contains a Google API key (AIza...). Remove it and rotate the key."
fi
if scan 'sk-[A-Za-z0-9]{20,}'; then
  deny "Blocked commit: the staged diff contains an OpenAI-shaped API key (sk-...). Remove it and rotate the key."
fi
if scan 'npm_[0-9A-Za-z]{36}'; then
  deny "Blocked commit: the staged diff contains an npm access token (npm_...). Remove it and rotate the token."
fi

# Azure secrets - connection-string and SAS-token shapes are structural, not a bare
# password/secret regex.
if scani 'DefaultEndpointsProtocol=https?;AccountName=[^;]+;AccountKey='; then
  deny "Blocked commit: the staged diff contains an Azure Storage connection string (AccountKey=...). Remove it and rotate the key."
fi
if scan '[?&]sig=[A-Za-z0-9%]{20,}'; then
  deny "Blocked commit: the staged diff contains what looks like an Azure SAS token (sig=...). Remove it and regenerate the signature."
fi

# Database connection strings with credentials embedded in the URI userinfo - any vendor, same
# structural shape (scheme://user:password@host).
if scani '(postgres(ql)?|mysql|mongodb(\+srv)?|redis|amqp|mssql):\/\/[^/[:space:]:@]+:[^/[:space:]@]{3,}@'; then
  deny "Blocked commit: the staged diff contains a database connection string with an embedded password. Remove it; keep secrets in .env (gitignored)."
fi

# JWTs - structural: an eyJ (base64 of '{"') header, then two more dot-separated base64url
# segments.
if scan 'eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}'; then
  deny "Blocked commit: the staged diff contains what looks like a JWT (eyJ...). Remove it; tokens belong in .env or a secret store, not source/config."
fi

# Logging a credential-shaped variable is a developer mistake worth catching by name, not by
# value - printing/logging a variable literally named ...password/...secret/...token/...api_key
# leaks it regardless of what the value happens to be at runtime.
if scani '(print|console\.(log|debug|info|warn|error)|logg?er\.[a-z]+|logging\.[a-z]+|Write-Host|Write-Output)\([^)]*[A-Za-z0-9_]*(password|passwd|secret|api_?key|access_?token)\b'; then
  deny "Blocked commit: the staged diff logs/prints a variable whose name looks like a password, secret, API key, or access token. Never log credential values, even in debug code - remove the log statement instead."
fi

exit 0
