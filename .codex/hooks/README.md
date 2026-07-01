# Hooks

Event-driven scripts that turn the agent system's prose rules into hard,
machine-enforced guarantees. Registered in `.codex/hooks.json` and committed so
every clone inherits them.

| Hook | Event | Matcher | What it does |
|---|---|---|---|
| `session-start.sh` | `SessionStart` | - | Installs backend/frontend deps (`uv sync`, `pnpm install`) when their manifests exist, so tests and linters are ready in a fresh remote container. |
| `guard-bash.sh` | `PreToolUse` | `Bash` | Blocks `playwright install`, catastrophic `rm -rf` of root/home/cwd, `git push --force`, and non-orchestrator shell reads of agent infrastructure. |
| `guard-edits.sh` | `PreToolUse` | `Edit\|Write\|apply_patch` | Blocks edits to review-only `feature-memory/history/**` and secrets files (`.env`, `.env.*`; `.env.example` stays editable). Also confines **QA** to writing `frontend/e2e/**` Playwright specs/helpers and the slice verdict. |
| `guard-infra-read.sh` | `PreToolUse` | `Read\|Grep\|Glob\|LS` | Blocks non-orchestrator subagents from reading `AGENTS.md`, `CLAUDE.md`, `.codex/`, `.claude/`, `scripts/`, hooks, settings, and agent templates. Main-thread and orchestrator reads pass through. |
| `guard-mcp.sh` | `PreToolUse` | `mcp__fullstack_guidelines__.*` | Enforces the core MCP budget rule: **only the orchestrator may call the guidelines server**; downstream roles are denied and told to ask the orchestrator. |
| `auto-format.sh` | `PostToolUse` | `Edit\|Write\|apply_patch` | Formats the file Codex just wrote (`ruff` for `.py`, locally-installed `prettier` for JS/TS/JSON/CSS/YAML). No-op when the tool isn't installed; never triggers a network install. |
| `verify-subagent.sh` | `SubagentStop` | `backend-developer\|frontend-developer` | Deterministic gate: runs stack-local validators, static checks, and available tests/coverage before a developer returns. |
| `guard-commit.sh` | `PreToolUse` | `Bash` | Scans the staged diff before a commit for private keys / AWS keys and blocks the commit on a finding. Defense-in-depth for main-thread commits the developer gate never sees. |
| `format-changed.sh` | `Stop` | - | Formats files created via `Bash` (Alembic migrations, codegen) that `auto-format.sh` never saw, by routing each `git status` change back through `auto-format.sh`. |
| `compaction-watch.sh` | `Stop` | - | Runs `scripts/validate/compaction.py --enforce` and blocks when four or more active QA-approved feature memories require history compaction. |
| `workflow-watch.sh` | `Stop` | - | Runs targeted `scripts/validate/*` checks for changed guidance, hooks, feature memory, backend, frontend, QA, and Playwright story contracts. |
| `reinject-context.sh` | `SessionStart` | `compact` | After compaction, re-injects the 4 AGENTS.md rules + the deterministic-gate model + the active feature-memory slice states. |

## How blocking works

These guards use the documented `PreToolUse` decision output: on a violation they
print

```json
{ "hookSpecificOutput": { "hookEventName": "PreToolUse",
                          "permissionDecision": "deny",
                          "permissionDecisionReason": "..." } }
```

to stdout and exit 0; otherwise they exit 0 with no output and the normal permission
flow applies. (Exiting with code **2** and writing the reason to stderr is an
equivalent way to block.) The guards parse hook JSON through `hook-json.sh`, which prefers
Python and falls back to a verified working `jq`. If neither parser is available, they
**fail open** (exit 0, no decision), so a broken toolchain can never brick a session -
they enforce, they never trap.

## Agent-scoped enforcement

`PreToolUse` events carry the calling subagent's identity when the call fires inside a
subagent:

- `agent_type` - the agent name (e.g. `orchestrator`, `backend-developer`, `qa`).
- `agent_id` - a unique id for that subagent invocation.

The guards read `agent_type` to enforce role-scoped contracts that used to live only in
the agent prompts:

- **MCP is orchestrator-only** (`guard-mcp.sh`): calls to `mcp__fullstack_guidelines__*`
  from `backend-developer` / `frontend-developer` / `qa` are
  denied. The orchestrator (and the main thread, which has no `agent_type`) pass through.
- **Agent infrastructure reads are orchestrator-only** (`guard-infra-read.sh`): direct
  `Read`/`Grep`/`Glob`/`LS` calls against root guidance, `.codex/`, `.claude/`, or
  `scripts/` are denied for downstream subagents. The Bash guard also blocks obvious
  shell reads/searches of those paths. Narrow exception: QA may read
  `.codex/skills/playwright-cli/**` for Playwright spec generation/healing.
- **QA write scope** (`guard-edits.sh`): when `agent_type` is `qa`, writes are allowed only under
  `frontend/e2e/**` or to the terminal `slice.md` verdict; anything else is denied so app fixes
  route back through the orchestrator.

Downstream agents already omit MCP tools from their frontmatter, so `guard-mcp.sh` is
defense-in-depth: it survives tool-config drift (e.g. an agent edited to grant `*`) and
makes the invariant explicit and enforced rather than merely requested.

When extending these guards, keep rules either universal or correctly gated on
`agent_type`; do not assume identity is present for main-thread calls (there `agent_type`
is empty - treat that as "not a restricted subagent").

It is invoked through `.codex/hooks/run-hook.py`, which runs on Windows, macOS, and Linux.
The launcher resolves Bash from `PATH`, common Git-for-Windows install locations, or `GIT_BASH`.

The committed hook command is `python .codex/hooks/run-hook.py ...`, so Python must be
available as `python` on `PATH` before hooks can launch. The project bootstrap installs/configures
this.

`run-hook.py` passes hook event JSON through `HOOK_INPUT_JSON` before launching Bash, then
the scripts fall back to stdin. This avoids Windows shells where redirected stdin makes a
WinGet-provided `jq.exe` fail to execute.

## Closing the Bash gap, compaction, and commit secrets

Five hooks cover paths the per-edit hooks miss:

- **`format-changed.sh` (`Stop`)** - `auto-format.sh` only fires on `Edit`/`Write`, so files written
  through `Bash` (Alembic `--autogenerate` migrations, codegen, scaffolding) never get formatted.
  Once per turn this scans `git status --porcelain` and routes each changed/untracked file back
  through `auto-format.sh`, so there is one source of truth for the ruff/prettier mapping. Never
  blocks; loop-safe via `stop_hook_active`; a no-op when no formatter is installed.

- **`compaction-watch.sh` (`Stop`)** - counts active `feature-memory/*/slice.md` files with
  `State: QA APPROVED`. When four or more are active, it blocks with the three oldest approved
  slice directories to move under `feature-memory/history/`. The hook only watches and blocks; the
  LLM still writes the historical summary and performs the move.

- **`workflow-watch.sh` (`Stop`)** - runs one aggregate workflow check for workflow-infrastructure
  changes, otherwise runs only the relevant targeted validators based on `git status`. This keeps
  guidance drift, hook registration, feature-memory, Playwright story, backend, frontend, and QA
  mechanical checks out of agent prompts without repeatedly fanning out through overlapping wrappers.

- **`reinject-context.sh` (`SessionStart`, matcher `compact`)** - compaction can drop the operating
  rules. Anything it prints to stdout is added back to context, so it restates the four AGENTS.md
  rules, the "deterministic work is a hook" model, and lists the active feature-memory slices with
  their QA `State`. It summarizes; it does not dump AGENTS.md.

- **`guard-commit.sh` (`PreToolUse` Bash)** - the `SubagentStop` gate only
  covers developer subagents, so a main-thread `git commit` is otherwise unchecked. This scans the
  **staged diff only** (added lines) for structural secret material - private-key blocks,
  `AKIA...` AWS key ids, AWS secret access keys - and denies the commit on a match. It deliberately
  does **not** use a generic `password|secret|token` regex or a whole-repo `validate-tools secrets`
  scan: both would flag this repo's own security tooling and block its commits. Whole-tree secret
  scanning already runs in the `SubagentStop` gate via `validate-tools run`.

## Deterministic verification (PostToolUse + SubagentStop)

Two hooks move work out of "the agent should remember to do this" and into "this always
happens":

- **`auto-format.sh` (`PostToolUse`)** runs after every `Edit`/`Write`. It formats the exact
  file Codex wrote using whatever formatter is installed locally - `ruff format` + `ruff check
  --fix` for Python, a locally-installed `prettier` for JS/TS/JSON/CSS/YAML. It deliberately
  resolves `prettier` from `node_modules/.bin` or `PATH` only, never via `npx` (which would fetch
  it over the network), and is a silent no-op when nothing is installed. `PostToolUse` can't block
  (the edit already happened) - this just keeps style consistent without asking each agent to run a
  formatter.

- **`verify-subagent.sh` (`SubagentStop`, matcher `backend-developer|frontend-developer`)** turns
  the "run the checks before returning" instruction into a hard gate. When a developer subagent
  finishes, it runs the full deterministic set - `ruff`/`mypy` (or `tsc --noEmit`), `validate-tools
  `validate-tools project-layout .`, and the test suite (`pytest` / `pnpm test:coverage`) - and, on failure, returns
  `{"decision":"block","reason":"..."}` so the subagent keeps working and fixes the errors before it can
  hand back. It is **fail-safe** (no manifest or tool -> allow, so it's a no-op on the scaffold) and
  **loop-safe** (honors `stop_hook_active`, and Codex caps consecutive Stop-blocks at 8).

## Hooks vs subagents - the division of labor

The principle (AGENTS.md rule 3): **if a step can be made deterministic, it is a hook and is
deleted from the agents.** Applied here:

- **Deterministic, rule-based steps -> hooks:** formatting, linting, type-checking,
  `validate-tools` compliance, repo workflow validators, running the test suite, path/secrets
  guards, MCP scoping, and dependency bootstrap. These no longer depend on an LLM choosing to run them.
- **Judgment and authoring steps -> subagents:** writing backend/frontend code *and its tests*,
  Playwright spec generation/healing, architecture review, and the merge decision. A hook can run `pytest`; it cannot
  decide which tests to write or whether the design is sound.

This split is why the **`tester` agent was removed** (developers author tests; the SubagentStop
gate runs them) and the **`qa` agent was slimmed to judgment only** (it no longer runs
`validate-tools` - the gate does). The agents that remain - orchestrator, the two developers,
qa - each do something a script cannot.

**Opt-in: an LLM-backed Stop gate.** For an even stronger finish condition, Codex supports
`type: "prompt"` and `type: "agent"` hooks that call a model. For example, an agent-based `Stop`
hook can run the suite and refuse to let the main session stop until tests pass:

```json
{
  "hooks": {
    "Stop": [
      { "hooks": [ { "type": "agent",
                     "prompt": "Run the project's test suite (see AGENTS.md). If anything fails, return {\"ok\": false, \"reason\": \"<what failed>\"}.",
                     "timeout": 120 } ] }
    ]
  }
}
```

Not enabled by default - agent hooks are experimental, cost tokens on every turn, and overlap with
the developer SubagentStop gate. Add it deliberately if you want a model-checked finish on top of
the deterministic one.

## SessionStart behaviour

`session-start.sh` runs **synchronously** (dependencies are guaranteed before the agent
loop starts, avoiding a race where Codex runs tests before install finishes) and only in
the remote environment (`CODEX_REMOTE=true`). It is idempotent and fail-tolerant: a
failed install logs a warning and continues. Until the template has real backend/frontend
code it is a no-op that just reports "scaffold only". To trade the guarantee for faster
startup, switch it to async per the SessionStart hook docs.

## Testing a hook locally

Hooks read a JSON event on stdin. Simulate one through the same cross-platform launcher Codex uses:

```bash
printf '%s\n' '{"tool_input":{"command":"git status"}}' | python .codex/hooks/run-hook.py .codex/hooks/guard-bash.sh
```

```bash
echo '{"tool_input":{"command":"npx playwright install"}}'                 | .codex/hooks/guard-bash.sh
echo '{"tool_input":{"file_path":".env"}}'                                 | .codex/hooks/guard-edits.sh
echo '{"agent_type":"qa","tool_input":{"file_path":"src/x.ts"}}' | .codex/hooks/guard-edits.sh
echo '{"agent_type":"backend-developer"}'                                  | .codex/hooks/guard-mcp.sh
echo '{"tool_input":{"file_path":"'"$PWD"'/x.py"}}'                         | .codex/hooks/auto-format.sh
echo '{"agent_type":"backend-developer","stop_hook_active":false}'         | .codex/hooks/verify-subagent.sh
CODEX_REMOTE=true .codex/hooks/session-start.sh
```

For `PreToolUse` guards, a `permissionDecision: "deny"` JSON object = blocked and no output =
allowed. For `verify-subagent.sh`, a `{"decision":"block"}` object = the developer must keep
working and no output = allowed to finish.

Reference: https://code.codex.com/docs/en/hooks
