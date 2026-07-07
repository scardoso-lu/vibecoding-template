#!/usr/bin/env bash
# SessionStart hook (matcher: startup|resume) - pick up a previous session's handoff.
#
# When a prior session wrote SESSION-HANDOFF.md (normally because context-usage-watch.sh
# fired at ~90% usage), this announces it and instructs Claude to ask the user whether to
# inject it before any other work. Stdout is added to Claude's context. The file's content
# is deliberately NOT dumped here - it is only read after the user says yes.
#
# SESSION-HANDOFF.md is gitignored: it only exists when the same workspace persists across
# sessions. In a fresh clone the durable copy is the chat output the 90% watch requested.
set -uo pipefail

ROOT="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
cd "$ROOT" 2>/dev/null || true

HANDOFF="SESSION-HANDOFF.md"
[ -f "$HANDOFF" ] || exit 0

# GNU date first, BSD/macOS stat fallback; cosmetic only.
updated="$(date -r "$HANDOFF" '+%Y-%m-%d %H:%M' 2>/dev/null || stat -f '%Sm' "$HANDOFF" 2>/dev/null || echo unknown)"

cat <<EOF
[session-handoff] A previous session left a handoff file: $HANDOFF (last updated: $updated).
Before starting any other work, use the AskUserQuestion tool to ask: "A session handoff exists
in $HANDOFF. Do you want me to inject it and continue the unfinished work?" with exactly these
three options (do not just type the question as plain text - render it as a real multi-choice
prompt so the user can pick without typing):
- "Yes" - read $HANDOFF, follow its '## References' section (linked memory/PRD/**/prd.md,
  memory/ADR/**/adr.md, memory/feature/**/slice.md, and memory/rules.md slugs), and implement
  the '## Missing / Not Completed' items in the '## Next steps' order. Route product/feature
  work through the agent system directly per the operating rules. When everything is done, update
  $HANDOFF (or delete it if nothing remains).
- "No" - leave $HANDOFF untouched and proceed with the user's new request.
- "Something else" - ask the user what they want instead of guessing between the two paths above.
EOF

exit 0
