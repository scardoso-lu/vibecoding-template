#!/usr/bin/env bash
# Notification hook — desktop alert when Claude is waiting for input or permission, so
# you can step away from the terminal. Cross-platform; a silent no-op where no
# notification backend exists (remote containers, CI).
#
# Registered only for the attention-worthy Notification matchers (permission_prompt,
# idle_prompt, agent_needs_input) - not every subtype (e.g. auth_success, agent_completed)
# fires a desktop popup, since those don't need you to look.
#
# Belt-and-suspenders main-thread scoping: if the event ever carries an agent_type (a
# subagent-attributed notification), skip - you only need the popup for the top-level
# session waiting on you, not for background subagent churn. When agent_type is absent
# (the normal case for this event), this is a no-op and the notification fires as before.
set -uo pipefail

HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$HOOK_DIR/hook-json.sh" 2>/dev/null || true

if command -v hook_json_can_parse >/dev/null 2>&1 && hook_json_can_parse; then
  # The launcher (run-hook.py) delivers the event via HOOK_INPUT_JSON and leaves the child's
  # stdin at EOF, so read the env var first (the same pattern every other input-consuming hook
  # uses) and only fall back to stdin when it is unset. Reading stdin alone made this agent_type
  # skip dead under the launcher — INPUT_PEEK was always empty, so the subagent check never fired.
  INPUT_PEEK="${HOOK_INPUT_JSON:-}"
  [ -n "$INPUT_PEEK" ] || INPUT_PEEK="$(cat)"
  AGENT_PEEK="$(hook_json_get "$INPUT_PEEK" "agent_type")"
  [ -z "$AGENT_PEEK" ] || exit 0
fi

MSG="${1:-Claude Code needs your attention}"

case "$(uname -s 2>/dev/null || echo unknown)" in
  Darwin)
    command -v osascript >/dev/null 2>&1 && \
      NOTIFY_MSG="$MSG" osascript -e 'display notification system attribute "NOTIFY_MSG" with title "Claude Code"' >/dev/null 2>&1 || true
    ;;
  Linux)
    command -v notify-send >/dev/null 2>&1 && \
      notify-send "Claude Code" "$MSG" >/dev/null 2>&1 || true
    ;;
  *)  # Windows / Git Bash
    command -v powershell.exe >/dev/null 2>&1 && \
      NOTIFY_MSG="$MSG" NOTIFY_TITLE="Claude Code" powershell.exe -NoProfile -WindowStyle Hidden -Command '
Add-Type -AssemblyName System.Windows.Forms
$notify = New-Object System.Windows.Forms.NotifyIcon
$notify.Icon = [System.Drawing.SystemIcons]::Information
$notify.BalloonTipTitle = $env:NOTIFY_TITLE
$notify.BalloonTipText = $env:NOTIFY_MSG
$notify.Visible = $true
$notify.ShowBalloonTip(5000)
Start-Sleep -Seconds 6
$notify.Dispose()
' >/dev/null 2>&1 || true
    ;;
esac

exit 0
