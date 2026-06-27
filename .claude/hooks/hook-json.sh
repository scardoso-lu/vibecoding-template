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
