# Hooks

Event-driven scripts that turn the agent system's prose rules into hard,
machine-enforced guarantees. Registered in `.claude/settings.json` and committed so
every clone inherits them.

| Hook | Event | Matcher | What it does |
|---|---|---|---|
| `session-start.sh` | `SessionStart` | — | Installs backend/frontend deps (`uv sync`, `pnpm install`) when their manifests exist, so tests and linters are ready in a fresh remote container. |
| `guard-bash.sh` | `PreToolUse` | `Bash` | Blocks `playwright install`, catastrophic `rm -rf` of root/home/cwd, and `git push --force`. |
| `guard-edits.sh` | `PreToolUse` | `Edit\|Write\|MultiEdit` | Blocks edits to review-only `feature-memory/history/**` and secrets files (`.env`, `.env.*`; `.env.example` stays editable). Also confines the **e2e-explorer** to writing under `feature-memory/<slice>/e2e/`. |
| `guard-mcp.sh` | `PreToolUse` | `mcp__fullstack-guidelines__.*` | Enforces the core MCP budget rule: **only the orchestrator may call the guidelines server**; downstream roles are denied and told to ask the orchestrator. |
| `notify-stop.sh` | `Stop` | — | Speaks "Claude stopped" when a turn finishes. Audible only on a machine with a TTS backend (your local session); a silent no-op in remote/CI sessions. |

## How blocking works

These guards use the documented `PreToolUse` decision output: on a violation they
print

```json
{ "hookSpecificOutput": { "hookEventName": "PreToolUse",
                          "permissionDecision": "deny",
                          "permissionDecisionReason": "…" } }
```

to stdout and exit 0; otherwise they exit 0 with no output and the normal permission
flow applies. (Exiting with code **2** and writing the reason to stderr is an
equivalent way to block.) The guards **fail open** (exit 0, no decision) when `jq` is
missing, so a broken toolchain can never brick a session — they enforce, they never trap.

## Agent-scoped enforcement

`PreToolUse` events carry the calling subagent's identity when the call fires inside a
subagent:

- `agent_type` — the agent name (e.g. `orchestrator`, `backend-developer`, `e2e-explorer`).
- `agent_id` — a unique id for that subagent invocation.

The guards read `agent_type` to enforce role-scoped contracts that used to live only in
the agent prompts:

- **MCP is orchestrator-only** (`guard-mcp.sh`): calls to `mcp__fullstack-guidelines__*`
  from `backend-developer` / `frontend-developer` / `tester` / `e2e-explorer` / `qa` are
  denied. The orchestrator (and the main thread, which has no `agent_type`) pass through.
- **e2e-explorer write scope** (`guard-edits.sh`): when `agent_type` is `e2e-explorer`,
  writes are allowed only under `.claude/feature-memory/<slice>/e2e/`; anything else is
  denied so fixes route back through the orchestrator.

Downstream agents already omit MCP tools from their frontmatter, so `guard-mcp.sh` is
defense-in-depth: it survives tool-config drift (e.g. an agent edited to grant `*`) and
makes the invariant explicit and enforced rather than merely requested.

When extending these guards, keep rules either universal or correctly gated on
`agent_type`; do not assume identity is present for main-thread calls (there `agent_type`
is empty — treat that as "not a restricted subagent").

## Stop notification (voice)

`notify-stop.sh` speaks a short phrase ("Claude stopped") when the main agent finishes a turn,
so you get an audible cue without watching the terminal. It picks a text-to-speech backend by OS:
`say` on macOS, `spd-say` / `espeak-ng` / `espeak` on Linux, and PowerShell's
`System.Speech.Synthesis.SpeechSynthesizer` on Windows. With **no backend present it exits 0
silently** — so although it is registered in the committed `settings.json`, it makes noise only on
a machine that actually has speech + audio (your local session), and is a harmless no-op in remote
containers and CI.

It is invoked as `bash "$CLAUDE_PROJECT_DIR/.claude/hooks/notify-stop.sh"` so it works on Windows
under Git Bash. On native Windows without Git Bash, point the command at a PowerShell `.ps1`
equivalent instead. Override the phrase by passing an argument, e.g. `notify-stop.sh "done"`; check
which backend would be used with `NOTIFY_STOP_DEBUG=1`.

## SessionStart behaviour

`session-start.sh` runs **synchronously** (dependencies are guaranteed before the agent
loop starts, avoiding a race where Claude runs tests before install finishes) and only in
the remote environment (`CLAUDE_CODE_REMOTE=true`). It is idempotent and fail-tolerant: a
failed install logs a warning and continues. Until the template has real backend/frontend
code it is a no-op that just reports "scaffold only". To trade the guarantee for faster
startup, switch it to async per the SessionStart hook docs.

## Testing a hook locally

Hooks read a JSON event on stdin. Simulate one:

```bash
echo '{"tool_input":{"command":"npx playwright install"}}'                 | .claude/hooks/guard-bash.sh
echo '{"tool_input":{"file_path":".env"}}'                                 | .claude/hooks/guard-edits.sh
echo '{"agent_type":"e2e-explorer","tool_input":{"file_path":"src/x.ts"}}' | .claude/hooks/guard-edits.sh
echo '{"agent_type":"backend-developer"}'                                  | .claude/hooks/guard-mcp.sh
CLAUDE_CODE_REMOTE=true .claude/hooks/session-start.sh
```

A `permissionDecision: "deny"` JSON object = blocked; no output = allowed.

Reference: https://code.claude.com/docs/en/hooks
