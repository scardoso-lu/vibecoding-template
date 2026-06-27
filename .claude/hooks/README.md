# Hooks

Event-driven scripts that turn some of the agent system's prose rules into hard,
machine-enforced guarantees. Registered in `.claude/settings.json` and committed so
every clone inherits them.

| Hook | Event | Matcher | What it does |
|---|---|---|---|
| `session-start.sh` | `SessionStart` | — | Installs backend/frontend deps (`uv sync`, `pnpm install`) when their manifests exist, so tests and linters are ready in a fresh remote container. |
| `guard-bash.sh` | `PreToolUse` | `Bash` | Blocks `playwright install`, catastrophic `rm -rf` of root/home/cwd, and `git push --force`. |
| `guard-edits.sh` | `PreToolUse` | `Edit\|Write\|MultiEdit` | Blocks edits to review-only `feature-memory/history/**` and to secrets files (`.env`, `.env.*`; `.env.example` stays editable). |

## How blocking works

A `PreToolUse` hook that exits with code **2** blocks the tool call and returns its
stderr to the agent as the reason. Any other exit code allows the call. The guards
**fail open** (exit 0) when `jq` is missing, so a broken toolchain can never brick a
session — they enforce, they never trap.

## SessionStart behaviour

`session-start.sh` runs **synchronously** (dependencies are guaranteed before the
agent loop starts, avoiding a race where Claude runs tests before install finishes)
and only in the remote environment (`CLAUDE_CODE_REMOTE=true`). It is idempotent and
fail-tolerant: a failed install logs a warning and continues. Until the template has
real backend/frontend code, it is a no-op that just reports "scaffold only". To trade
the guarantee for faster startup, switch it to async per the SessionStart hook docs.

## Scope and limitations (read before extending)

These hooks enforce **agent-independent** rules only. A `PreToolUse` hook receives the
tool name and tool input, **not the identity of the subagent that issued the call**, so
hooks cannot tell the orchestrator apart from a developer or the e2e-explorer.

That means role-scoped contracts in `.claude/agents/*.md` — "developers never call MCP",
"the e2e-explorer writes only under `e2e/`", "QA runs only allowed validators" — stay
**prompt-level contracts**, not hook-enforced. Do not add guards that assume they can
detect the calling agent; they would either misfire on the orchestrator's legitimate
calls or give a false sense of enforcement. Keep hook rules universal: things that are
true for *every* caller in this repo.

## Testing a hook locally

Hooks read a JSON event on stdin. Simulate one:

```bash
echo '{"tool_input":{"command":"npx playwright install"}}' | .claude/hooks/guard-bash.sh; echo "exit=$?"
echo '{"tool_input":{"file_path":".env"}}'                  | .claude/hooks/guard-edits.sh; echo "exit=$?"
CLAUDE_CODE_REMOTE=true .claude/hooks/session-start.sh
```

Exit `2` = blocked (expected for the first two); `0` = allowed.
