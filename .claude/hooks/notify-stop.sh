#!/usr/bin/env bash
# Stop hook — speak a short notice when Claude finishes a turn.
#
# Audio plays on the machine running the session, so this is only audible in a LOCAL
# Claude Code session. It is a deliberate, silent no-op anywhere without a text-to-speech
# backend (remote containers, CI) — a Stop hook must never block or error the turn.
set -uo pipefail

PHRASE="${1:-Claude stopped}"

# Consume and discard the Stop-event JSON on stdin; none of its fields are needed.
cat >/dev/null 2>&1 || true

speak_with=""
case "$(uname -s 2>/dev/null || echo unknown)" in
  Darwin)
    if command -v say >/dev/null 2>&1; then speak_with="say"; fi ;;
  Linux)
    if   command -v spd-say   >/dev/null 2>&1; then speak_with="spd-say"
    elif command -v espeak-ng >/dev/null 2>&1; then speak_with="espeak-ng"
    elif command -v espeak    >/dev/null 2>&1; then speak_with="espeak"
    fi ;;
  *)  # MINGW*/MSYS*/CYGWIN* (Git Bash) or anything else → try Windows PowerShell TTS.
    if command -v powershell.exe >/dev/null 2>&1; then speak_with="powershell"; fi ;;
esac

if [ -n "${NOTIFY_STOP_DEBUG:-}" ]; then
  printf 'notify-stop: backend=%s phrase=%q\n' "${speak_with:-none}" "$PHRASE" >&2
fi

case "$speak_with" in
  say)        say "$PHRASE" ;;
  spd-say)    spd-say --wait "$PHRASE" ;;
  espeak-ng)  espeak-ng "$PHRASE" ;;
  espeak)     espeak "$PHRASE" ;;
  powershell) powershell.exe -NoProfile -Command \
                "Add-Type -AssemblyName System.Speech; (New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak('$PHRASE')" ;;
  *)          : ;;  # no backend available — silent no-op
esac

exit 0
