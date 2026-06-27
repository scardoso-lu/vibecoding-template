#!/usr/bin/env bash
# Notification hook — desktop alert when Claude is waiting for input or permission, so
# you can step away from the terminal. Cross-platform; a silent no-op where no
# notification backend exists (remote containers, CI).
set -uo pipefail

MSG="${1:-Claude Code needs your attention}"

# Consume and ignore the Notification event JSON on stdin.
cat >/dev/null 2>&1 || true

case "$(uname -s 2>/dev/null || echo unknown)" in
  Darwin)
    command -v osascript >/dev/null 2>&1 && \
      osascript -e "display notification \"$MSG\" with title \"Claude Code\"" >/dev/null 2>&1 || true
    ;;
  Linux)
    command -v notify-send >/dev/null 2>&1 && \
      notify-send "Claude Code" "$MSG" >/dev/null 2>&1 || true
    ;;
  *)  # Windows / Git Bash
    command -v powershell.exe >/dev/null 2>&1 && \
      powershell.exe -NoProfile -Command \
        "[System.Reflection.Assembly]::LoadWithPartialName('System.Windows.Forms'); [System.Windows.Forms.MessageBox]::Show('$MSG','Claude Code')" >/dev/null 2>&1 || true
    ;;
esac

exit 0
