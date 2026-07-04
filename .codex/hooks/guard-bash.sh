#!/usr/bin/env bash
# PreToolUse guard for Bash - blocks operations this project forbids or that are
# plainly destructive. Emits the documented PreToolUse deny decision as JSON.
# Fails open (exit 0, no decision) if JSON parsing is unavailable so it never bricks a session.
#
# microsoft/agent-governance-toolkit was evaluated as a replacement for this guard: it is a
# real, maintained policy-enforcement layer (YAML/OPA Rego/Cedar rules, sub-ms interception),
# but it targets framework callback hooks (LangChain, CrewAI, Google ADK, etc.) and has no
# documented Codex/Claude Code PreToolUse integration. Adopting it would mean replacing this
# hook-script model with an external policy engine - a much larger architecture change than
# this task, so it was not adopted here. Revisit if a native integration ships.
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

# Quotes are stripped once up front so quoted spellings ("$HOME", "$PWD", "/", "cat" ".env")
# match the same as unquoted ones across every check below.
CMD_NOQUOTE="$(printf '%s' "$CMD" | tr -d "\"'")"

# Project rule: Chromium + Playwright are pre-installed at $PLAYWRIGHT_BROWSERS_PATH.
# Never re-fetch the browser bundle.
if printf '%s' "$CMD" | grep -Eq '(^|[^[:alnum:]])playwright[[:space:]]+install'; then
  deny "'playwright install' is forbidden - Chromium is pre-installed at \$PLAYWRIGHT_BROWSERS_PATH; drive the existing browser."
fi

# Never echo/print/log environment variable values into the transcript, whether they come
# from a dotenv file or the live process environment. Applies to every agent and the main
# thread; there is no script/wrapper bypass because these checks match the literal command
# text regardless of how deeply it is nested in `bash -c '...'`, a helper script invocation,
# or a one-liner. (A guard can't see inside an *external* script file's contents - that is a
# real limitation - but it still catches the command line that invokes it.)
# .env.example is the tracked, secret-free template (same carve-out as guard-edits.sh) - strip
# it out before checking so reading it stays allowed; a real .env/.env.<name> read still denies.
CMD_ENV_CHECK="$(printf '%s' "$CMD_NOQUOTE" | sed 's/\.env\.example//g')"
if printf '%s' "$CMD_ENV_CHECK" | grep -Eiq '(^|[[:space:];|&])(cat|type|more|less|head|tail|Get-Content)([[:space:]][^|;&]*)?[[:space:]]\.env(\.[A-Za-z0-9_.-]+)?([[:space:]]|$)'; then
  deny "reading a secrets file (.env / .env.*) via shell is blocked - never dump env-file contents into the transcript. Read only the specific key you need from .env.example or documentation, or ask the user."
fi
if printf '%s' "$CMD_NOQUOTE" | grep -Eq '(^|[[:space:];|&])(env|printenv)([[:space:]]*($|[|;&]))' \
   || printf '%s' "$CMD_NOQUOTE" | grep -Eq '(^|[[:space:];|&])set([[:space:]]*($|[|;&]))' \
   || printf '%s' "$CMD_NOQUOTE" | grep -Eiq '(Get-ChildItem|gci|dir|ls)[[:space:]]+(-Path[[:space:]]+)?[Ee]nv:'; then
  deny "dumping the full process environment (env / printenv / set / Get-ChildItem Env:) is blocked - it can leak secrets into the transcript. Check one specific non-secret variable, or ask the user."
fi
SECRET_NAME='[A-Za-z_][A-Za-z0-9_]*(KEY|SECRET|TOKEN|PASSWORD|PASSWD|CREDENTIAL|AUTH|PRIVATE)[A-Za-z0-9_]*'
if printf '%s' "$CMD_NOQUOTE" | grep -Eiq "(echo|printf|Write-Output|Write-Host)[^|;&]*(\\\$\\{?${SECRET_NAME}\\}?|%${SECRET_NAME}%|\\\$env:${SECRET_NAME})" \
   || printf '%s' "$CMD_NOQUOTE" | grep -Eiq "(printenv|Get-Item[[:space:]]+[Ee]nv:)[[:space:]:]*${SECRET_NAME}"; then
  deny "printing a secret-shaped environment variable is blocked - never echo/log KEY/SECRET/TOKEN/PASSWORD/CREDENTIAL/AUTH values, from a file or the system environment."
fi
if printf '%s' "$CMD" | grep -Eiq '(print|console\.log|Write-Output)[[:space:]]*\([^)]*(os\.environ|process\.env)'; then
  deny "printing the process environment via an interpreter one-liner (os.environ / process.env) is blocked - it can leak secrets into the transcript."
fi

# Broad filesystem scans hunting for an installed tool/executable are blocked - they are slow,
# noisy, and this project prefers asking over guessing a tool's location.
if printf '%s' "$CMD_NOQUOTE" | grep -Eq '(^|[[:space:];|&])find[[:space:]]+(/|\\\\|~|\$HOME|\$\{HOME\}|[A-Za-z]:[\\\\/]?)([[:space:]]|$)' \
   && printf '%s' "$CMD" | grep -Eiq '\-i?name[[:space:]]'; then
  deny "a broad recursive filesystem scan to locate a tool/executable is blocked. Ask the user for the exact executable name or path instead of scanning the filesystem."
fi
if printf '%s' "$CMD_NOQUOTE" | grep -Eiq '(^|[[:space:];|&])where[[:space:]]+/r([[:space:]]|$)' \
   || printf '%s' "$CMD_NOQUOTE" | grep -Eiq '(^|[[:space:];|&])(dir|Get-ChildItem|gci)[^|;&]*(-[Rr]ecurse|/s)[^|;&]*([A-Za-z]:[\\\\/]|/|~)([[:space:]]|$|["'"'"'])' \
   || printf '%s' "$CMD_NOQUOTE" | grep -Eq '(^|[[:space:];|&])locate([[:space:]]|$)'; then
  deny "a broad recursive filesystem scan to locate a tool/executable is blocked. Ask the user for the exact executable name or path instead of scanning the filesystem."
fi

# Catastrophic recursive force-deletes of a root / home / cwd target.
has_rmrf() {
  printf '%s' "$1" | grep -Eq 'rm[[:space:]]+-[a-zA-Z]*r[a-zA-Z]*f|rm[[:space:]]+-[a-zA-Z]*f[a-zA-Z]*r|rm[[:space:]]+-[rf][[:space:]]+-[rf]'
}
hits_root() {
  # A target that is the whole root, home, or cwd - bare, with an optional single
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

# Implementer/QA subagents may not read agent infrastructure through shell commands
# either. Main thread has no agent_type; the coordination tier is allowed.
case "$AGENT" in
  ""|orchestrator|product-owner|software-architect|business-challenger|technical-challenger)
    : ;;
  *)
    # Same templates/skills carve-out as guard-infra-read.sh: reference material, not
    # agent infrastructure.
    if printf '%s' "$CMD" | grep -Eiq '(^|[[:space:];|&])(cat|less|more|head|tail|grep|rg|find|ls|dir|Get-Content|Select-String|Get-ChildItem)([[:space:]]|$)' \
       && printf '%s' "$CMD" | grep -Eiq '(^|[[:space:]"'"'"'./\\])(CLAUDE\.md|AGENTS\.md|\.claude|\.codex|scripts)([[:space:]"'"'"'/\\]|$)' \
       && ! printf '%s' "$CMD" | grep -Eiq '\.(claude|codex)[/\\](templates|skills)[/\\]'; then
      deny "A '$AGENT' subagent may not inspect agent infrastructure through shell commands. Stop and return ESCALATE so the orchestrator can provide targeted context."
    fi ;;
esac

exit 0
