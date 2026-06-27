#!/usr/bin/env bash
# Notification hook — desktop alert when Codex is waiting for input or permission, so
# you can step away from the terminal. Cross-platform; a silent no-op where no
# notification backend exists (remote containers, CI).
set -uo pipefail

MSG="${1:-Codex needs your attention}"

# Consume and ignore the Notification event JSON on stdin.
cat >/dev/null 2>&1 || true

case "$(uname -s 2>/dev/null || echo unknown)" in
  Darwin)
    command -v osascript >/dev/null 2>&1 && \
      NOTIFY_MSG="$MSG" osascript -e 'display notification system attribute "NOTIFY_MSG" with title "Codex"' >/dev/null 2>&1 || true
    ;;
  Linux)
    command -v notify-send >/dev/null 2>&1 && \
      notify-send "Codex" "$MSG" >/dev/null 2>&1 || true
    ;;
  *)  # Windows / Git Bash
    command -v powershell.exe >/dev/null 2>&1 && \
      NOTIFY_MSG="$MSG" NOTIFY_TITLE="Codex" powershell.exe -NoProfile -WindowStyle Hidden -Command '
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
