#!/usr/bin/env bash
# Shared JSON helpers for hooks. Prefer Python because some Windows shells expose
# a jq.exe that cannot run when hook stdin is redirected.

hook_json_python() {
  if command -v python >/dev/null 2>&1; then
    printf '%s' python
  elif command -v python3 >/dev/null 2>&1; then
    printf '%s' python3
  fi
}

hook_json_can_parse() {
  [ -n "$(hook_json_python)" ] && return 0
  command -v jq >/dev/null 2>&1 || return 1
  printf '{}' | jq -e . >/dev/null 2>&1
}

hook_json_get() {
  local input="$1" path="$2" default="${3:-}"
  local py
  py="$(hook_json_python)"

  if [ -n "$py" ]; then
    HOOK_JSON_INPUT="$input" HOOK_JSON_PATH="$path" HOOK_JSON_DEFAULT="$default" "$py" -c '
import json
import os

try:
    value = json.loads(os.environ.get("HOOK_JSON_INPUT", "") or "{}")
except Exception:
    value = {}

for part in os.environ["HOOK_JSON_PATH"].split("."):
    if isinstance(value, dict) and part in value:
        value = value[part]
    else:
        value = os.environ.get("HOOK_JSON_DEFAULT", "")
        break

if value is None:
    value = os.environ.get("HOOK_JSON_DEFAULT", "")
if isinstance(value, bool):
    print("true" if value else "false")
else:
    print(value)
'
    return
  fi

  if printf '{}' | jq -e . >/dev/null 2>&1; then
    printf '%s' "$input" | jq -r ".$path // \"$default\""
  else
    printf '%s\n' "$default"
  fi
}

hook_json_get_many() {
  # usage: eval "$(hook_json_get_many "$INPUT" CMD=tool_input.command AGENT=agent_type)"
  # Extracts every VAR=json.dotted.path pair from ONE JSON parse (one interpreter spawn
  # instead of one per field - hook_json_get spawns a Python per call, which adds up on
  # hot PreToolUse paths) and emits shell-safe VAR='value' assignments. Missing paths
  # become ''. Values are shlex-quoted, so multiline command text is eval-safe.
  local input="$1"
  shift
  local py
  py="$(hook_json_python)"

  if [ -z "$py" ]; then
    # No Python: fall back to one hook_json_get per field (jq path), same results.
    local pair
    for pair in "$@"; do
      printf '%s=%q\n' "${pair%%=*}" "$(hook_json_get "$input" "${pair#*=}")"
    done
    return
  fi

  HOOK_JSON_INPUT="$input" HOOK_JSON_SPECS="$*" "$py" -c '
import json
import os
import shlex

try:
    data = json.loads(os.environ.get("HOOK_JSON_INPUT", "") or "{}")
except Exception:
    data = {}

for spec in os.environ["HOOK_JSON_SPECS"].split():
    name, _, path = spec.partition("=")
    value = data
    for part in path.split("."):
        if isinstance(value, dict) and part in value:
            value = value[part]
        else:
            value = ""
            break
    if value is None:
        value = ""
    if isinstance(value, bool):
        value = "true" if value else "false"
    if not isinstance(value, str):
        value = str(value)
    print(f"{name}={shlex.quote(value)}")
'
}

hook_json_normalize_path() {
  # Windows tool_input.file_path values use backslash separators (e.g.
  # C:\Users\...\slice.md). Every path glob in these hooks is written with forward
  # slashes, so normalize before matching or a Windows path silently fails to match
  # a case pattern (either a false-deny of an allowed write, or worse, a false-allow
  # of a path a guard is supposed to block).
  printf '%s' "$1" | tr '\\' '/'
}

hook_json_pretool_deny() {
  local reason="$1"
  local py
  py="$(hook_json_python)"

  if [ -n "$py" ]; then
    HOOK_REASON="$reason" "$py" -c '
import json
import os

print(json.dumps({
    "hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": os.environ["HOOK_REASON"],
    }
}, separators=(",", ":")))
'
  elif printf '{}' | jq -e . >/dev/null 2>&1; then
    jq -n --arg r "$reason" \
      '{hookSpecificOutput:{hookEventName:"PreToolUse",permissionDecision:"deny",permissionDecisionReason:$r}}'
  fi
}

hook_json_is_coordination_tier() {
  # Coordination tier: product-owner, software-architect, business-challenger, and
  # technical-challenger, plus the main thread (empty agent_type - passed as ""). These may read
  # agent infrastructure directly; every other subagent must go through the main thread instead.
  # Shared by guard-infra-read.sh and guard-bash.sh so the two guards enforce the exact same set
  # and can't independently drift (they used to each hardcode this case pattern separately).
  case "$1" in
    ""|product-owner|software-architect|business-challenger|technical-challenger)
      return 0 ;;
    *)
      return 1 ;;
  esac
}

hook_json_is_builtin_utility_agent() {
  # Built-in utility subagents (Explore, Plan, general-purpose, and the CLI helper agents) are
  # spawned by the main thread and act on its behalf, so for infrastructure READS they count as
  # the main thread (rule 4). They are NOT workflow roles: guard-edits.sh separately denies them
  # memory/** writes so planning artifacts stay with their owning agents.
  case "$1" in
    Explore|Plan|general-purpose|claude|claude-code-guide|statusline-setup)
      return 0 ;;
    *)
      return 1 ;;
  esac
}

hook_json_is_reference_material_path() {
  # True when $1 is a normalized path under .claude/templates, .claude/skills, .codex/templates,
  # or .codex/skills - reference material every subagent may read, not agent infrastructure.
  # Shared by guard-infra-read.sh (exact-path case match); guard-bash.sh matches the same four
  # directories against free command text via HOOK_JSON_REFERENCE_PATH_TEXT_REGEX below so both
  # checks name the same paths in one place.
  case "$1" in
    .claude/templates/*|*/.claude/templates/*|\
    .claude/skills/*|*/.claude/skills/*|\
    .codex/templates/*|*/.codex/templates/*|\
    .codex/skills/*|*/.codex/skills/*)
      return 0 ;;
    *)
      return 1 ;;
  esac
}

# Same four reference-material directories as hook_json_is_reference_material_path, as a regex
# fragment for guard-bash.sh's free-text command matching (it can't use the case-glob above since
# it isn't checking a single extracted path).
HOOK_JSON_REFERENCE_PATH_TEXT_REGEX='\.(claude|codex)[/\\](templates|skills)[/\\]'

hook_json_stop_block() {
  local reason="$1"
  local py
  py="$(hook_json_python)"

  if [ -n "$py" ]; then
    HOOK_REASON="$reason" "$py" -c '
import json
import os

print(json.dumps({"decision": "block", "reason": os.environ["HOOK_REASON"]}, separators=(",", ":")))
'
  elif printf '{}' | jq -e . >/dev/null 2>&1; then
    jq -n --arg r "$reason" '{decision:"block", reason:$r}'
  fi
}
