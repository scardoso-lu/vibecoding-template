# Hooks

Event-driven scripts that turn the agent system's prose rules into hard,
machine-enforced guarantees. Registered in `.codex/hooks.json` and committed so
every clone inherits them.

| Hook | Event | Matcher | What it does |
|---|---|---|---|
| `session-start.sh` | `SessionStart` | - | Installs backend/frontend deps (`uv sync`, `pnpm install`) when their manifests exist, so tests and linters are ready in a fresh remote container. |
| `guard-bash.sh` | `PreToolUse` | `Bash` | Blocks `playwright install`, catastrophic `rm -rf` of root/home/cwd, `git push --force`, implementer/QA shell reads of agent infrastructure, echoing/dumping env vars or secrets files (`.env`, `env`/`printenv`/`set`, secret-shaped `$VAR`/`%VAR%`/`$env:VAR`, `os.environ`/`process.env` one-liners), and broad filesystem scans hunting for installed tools (ask the user for the exact path instead). |
| `guard-edits.sh` | `PreToolUse` | `Edit\|Write\|apply_patch` | Blocks edits to secrets files (`.env`, `.env.*`; `.env.example` stays editable). Enforces the memory placement contract (`prd.md`/`adr.md`/`slice.md` only at their contract paths; `memory/` limited to `PRD/ ADR/ feature/ rules.md`) and the role write scopes: challengers are read-only, product-owner writes only `memory/PRD/**`, software-architect only `memory/ADR/**`+`memory/feature/**`+`memory/rules.md`, orchestrator never memory or app code, developers never the other stack's app root or planning memory, and **QA** only `frontend/e2e/**` specs/helpers, `qa-evidence.json`/`e2e-coverage.json`, and the slice verdict. |
| `guard-infra-read.sh` | `PreToolUse` | `Read\|Grep\|Glob\|LS` | Blocks implementer/QA subagents from reading `AGENTS.md`, `CLAUDE.md`, agent prompts/hooks/settings, and `scripts/`. Both `.codex/templates/**` and `.codex/skills/**` (and their `.claude/` mirrors) are whitelisted for every subagent - reference material, not agent infrastructure. Main-thread and coordination-tier reads pass through. |
| `guard-mcp.sh` | `PreToolUse` | `mcp__fullstack_guidelines__.*` | Enforces the core MCP budget rule: **only the software-architect may call the guidelines server**; other roles are denied and told to request context through the orchestrator. Also enforces the tool budget: `get_all_context` is denied for every caller, and the software-architect may call only `get_metadata`/`search_guidelines`/`get_guideline`. |
| developer handoff prompt gate | `SubagentStart` | `backend-developer\|frontend-developer` | Model-checks implementer handoffs before code starts: slice path, linked PRD/ADR/rules context, Agent Plan row, Do Not Touch, ACs, tests/evidence expectations, provenance, and narrow read scope. |
| coordination prompt gate | `SubagentStop` | `orchestrator` | Model-checks the orchestrator's return: one mode per response, no plan/memory/code writing, both 90% challenge gates and the 3-round cap enforced, round count + acceptance percentages recorded, and handoffs carry Do Not Touch + Stop condition. |
| business planning prompt gate | `SubagentStop` | `product-owner\|business-challenger` | Model-checks the PRD phase: selectable options for broad work, complete PRDs under `memory/PRD/<purpose>/prd.md`, P0/P1/P2 MVP requirements by journey/use case, and parent/component PRD links for large components. |
| architecture planning prompt gate | `SubagentStop` | `software-architect\|technical-challenger` | Model-checks the architecture phase: accepted PRDs become ADRs under `memory/ADR/<purpose>/adr.md`, slices link `PRD:`/`ADR:`/`Rules:`, rules stay in global `memory/rules.md`, and Agent Plan handoffs include larger component context. |
| QA judgment prompt gate | `SubagentStop` | `qa-challenger` | Model-checks qa-challenger's final judgment: clear slice verdict, required Playwright story coverage/output, deterministic gate evidence, linked PRD/ADR/rules context, and routable `BLOCKED` findings instead of app fixes. |
| `auto-format.sh` | `PostToolUse` | `Edit\|Write\|apply_patch` | Formats the file Codex just wrote (`ruff` for `.py`, locally-installed `prettier` for JS/TS/JSON/CSS/YAML). No-op when the tool isn't installed; never triggers a network install. |
| `verify-subagent.sh` | `SubagentStop` | `backend-developer\|frontend-developer` | Deterministic gate: runs stack-local validators, static checks, and available tests/coverage before a developer returns. |
| `verify-qa.sh` | `SubagentStop` | `qa-checker` | Deterministic QA artifact gate: runs QA, agent evidence, Playwright story, test coverage, E2E coverage, and QA evidence validators before qa-checker returns. |
| `verify-challenge.sh` | `SubagentStop` | `business-challenger\|technical-challenger` | Deterministic scoring gate: reads the challenger's own transcript, recomputes accepted/total from its `### Persona Votes` table, and hard-blocks if that doesn't match the stated `- Acceptance: N%` line or a vote is missing/malformed. An LLM's self-reported percentage is a claim, not evidence. |
| `guard-commit.sh` | `PreToolUse` | `Bash` (`if: Bash(git commit *)`) | Scans the staged diff before a commit for private keys, AWS/Stripe/GitHub/Slack/Google/OpenAI/npm keys, Azure connection strings/SAS tokens, DB connection-string passwords, JWTs, and credential-named variables being logged - blocks the commit on a finding. Defense-in-depth for main-thread commits the developer gate never sees. |
| `format-changed.sh` | `Stop` | - | Formats files created via `Bash` (Alembic migrations, codegen) that `auto-format.sh` never saw, by routing each `git status` change back through `auto-format.sh`. |
| `guard-harness.sh` | `Stop` | - | Runs targeted `scripts/validate/*` checks for changed guidance, hooks, memory, backend, frontend, QA, and Playwright story contracts. |
| `reinject-context.sh` | `SessionStart` | `compact` | After compaction, re-injects the 4 AGENTS.md rules + the deterministic-gate model + the active PRD/ADR/feature-slice states, and points back at `SESSION-HANDOFF.md` when one exists. |
| `track-compact.sh` | `PostCompact` | - | Appends a JSON line (timestamp + event fields) to a temp-dir log every time a compaction completes. `PostCompact` stdout is never fed back into context (unlike `SessionStart`), so this hook is side-effects-only - it cannot and does not replace `reinject-context.sh`. |
| `context-usage-watch.sh` | `PostToolUse` | - (all tools) | Watches transcript token usage; at >=90% of the context window (once per session) it injects an instruction to write the repo-root `SESSION-HANDOFF.md` (completed / missing / PRD-ADR-slice references / next steps) before auto-compaction, and to output the handoff verbatim in the chat reply (the file is gitignored, so chat is the durable copy). |
| `resume-handoff.sh` | `SessionStart` | `startup\|resume` | If `SESSION-HANDOFF.md` exists, instructs Codex to first ask the user whether to inject it; on yes, the missing items are implemented following the handoff's PRD/ADR/feature references. |
| `notify-attention.sh` | `Notification` | `permission_prompt\|idle_prompt\|agent_needs_input` | Desktop toast when the main thread needs you (a permission prompt, an idle prompt, or an agent waiting on input). Skips if the event carries an `agent_type` (subagent-attributed, not yours to act on). Silent no-op with no notification backend (remote containers, CI). |
| `notify-stop.sh` | `Stop` | - | Speaks a short phrase (local TTS) when a turn ends, audible only on the machine running the session. Silent no-op with no TTS backend. |

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

- `agent_type` - the agent name (e.g. `orchestrator`, `backend-developer`, `qa-checker`).
- `agent_id` - a unique id for that subagent invocation.

The guards read `agent_type` to enforce role-scoped contracts that used to live only in
the agent prompts:

- **MCP is software-architect-only** (`guard-mcp.sh`): calls to `mcp__fullstack_guidelines__*`
  from `backend-developer` / `frontend-developer` / `qa-checker` / `qa-challenger` /
  `product-owner` / `business-challenger` / `technical-challenger` / `orchestrator` are denied.
  The software-architect (and the main thread, which has no `agent_type`) pass through.
- **Agent infrastructure reads are coordination-tier-only** (`guard-infra-read.sh`): direct
  `Read`/`Grep`/`Glob`/`LS` calls against root guidance, `.codex/`, `.claude/`, or
  `scripts/` are denied for implementer/QA subagents. The coordination tier passes through. The
  Bash guard also blocks obvious shell reads/searches of those paths.
  Whitelist: every subagent may read `.codex/templates/**` and `.codex/skills/**` (and the
  `.claude/` mirrors) - they are reference material (e.g. qa-checker's own prompt points at
  `.codex/templates/categories/e2e.md`), not agent infrastructure.
- **Role write scopes** (`guard-edits.sh`): challengers (`business-challenger`,
  `technical-challenger`, `qa-challenger`) are fully read-only; `product-owner` writes only
  `memory/PRD/**` and `agent-evidence/**`; `software-architect` writes only `memory/ADR/**`,
  `memory/feature/**`, `memory/rules.md`, and `agent-evidence/**`; `orchestrator` never writes
  memory or `backend/`/`frontend/` code; `backend-developer`/`frontend-developer` never write the
  other stack's app root or planning memory (PRDs, ADRs, `memory/rules.md`). The same hook
  enforces the memory placement contract for every caller, main thread included.
- **MCP tool budget** (`guard-mcp.sh`): `get_all_context` is denied for all callers, and the
  software-architect is limited to `get_metadata` / `search_guidelines` / `get_guideline`.
- **qa-checker write scope** (`guard-edits.sh`): when `agent_type` is `qa-checker`, writes are
  allowed only under `frontend/e2e/**`, to `memory/feature/*/qa-evidence.json` and
  `memory/feature/*/e2e-coverage.json`, to `agent-evidence/*/agent-evidence.json`, or to the
  terminal `slice.md` verdict; anything else is
  denied so app fixes route back through the orchestrator. `qa-challenger` never writes at all -
  it is read-only, covered by the challenger rule above; the orchestrator relays its confirmed
  verdict to `qa-checker` to persist.

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

## Closing the Bash gap and commit secrets

Six hooks cover paths the per-edit hooks miss:

- **`format-changed.sh` (`Stop`)** - `auto-format.sh` only fires on `Edit`/`Write`, so files written
  through `Bash` (Alembic `--autogenerate` migrations, codegen, scaffolding) never get formatted.
  Once per turn this scans `git status --porcelain` and routes each changed/untracked file back
  through `auto-format.sh`, so there is one source of truth for the ruff/prettier mapping. Never
  blocks; loop-safe via `stop_hook_active`; a no-op when no formatter is installed.

- **`guard-harness.sh` (`Stop`)** - runs one aggregate workflow check for workflow-infrastructure
  changes, otherwise runs only the relevant targeted validators based on `git status`. This keeps
  guidance drift, hook registration, memory, Playwright story, backend, frontend, and QA
  mechanical checks out of agent prompts without repeatedly fanning out through overlapping wrappers.

- **`reinject-context.sh` (`SessionStart`, matcher `compact`)** - compaction can drop the operating
  rules. Anything it prints to stdout is added back to context, so it restates the four AGENTS.md
  rules, the "deterministic work is a hook" model, and lists the active memory slices with
  their QA `State`. It summarizes; it does not dump AGENTS.md.

- **`context-usage-watch.sh` (`PostToolUse`, all tools)** - auto-compaction can hit before anyone
  saves the working state. This hook tail-reads the session transcript after each tool call, sums
  the newest assistant `usage` record (`input` + `cache_read` + `cache_creation` + `output`
  tokens), and once usage crosses `CONTEXT_HANDOFF_THRESHOLD_PCT` (default `90`) of
  `CONTEXT_WINDOW_TOKENS` (default `200000`) it returns `additionalContext` telling Codex to
  write `SESSION-HANDOFF.md` at the repo root: `## Completed`, `## Missing / Not Completed`
  (checklist), `## References` (parent `memory/PRD/**/prd.md`, `memory/ADR/**/adr.md`,
  `memory/feature/**/slice.md`, `memory/rules.md` slugs), and `## Next steps`. It fires once per
  session (temp-dir sentinel keyed by `session_id`) and fails open on any parse/IO problem.

- **`resume-handoff.sh` (`SessionStart`, matcher `startup|resume`)** - the pickup half of the
  handoff loop. When `SESSION-HANDOFF.md` exists it injects an instruction to **ask the user
  first** whether to inject the handoff; on yes, Codex reads the file, follows its References to
  the linked PRDs/ADRs/feature slices, and continues implementing the missing items, updating or
  deleting the handoff when done. On no, the file is left untouched. The file content itself is
  not dumped into context until the user opts in.

- **`guard-commit.sh` (`PreToolUse` Bash, `if: Bash(git commit *)`)** - the `SubagentStop` gate only
  covers developer subagents, so a main-thread `git commit` is otherwise unchecked. This scans the
  **staged diff only** (added lines) for structural secret material - private-key blocks,
  `AKIA...` AWS key ids, AWS secret access keys - and denies the commit on a match. It deliberately
  does **not** use a generic `password|secret|token` regex or a whole-repo `validate-tools secrets`
  scan: both would flag this repo's own security tooling and block its commits. Whole-tree secret
  scanning already runs in the `SubagentStop` gate via `validate-tools run`.

## Deterministic verification (PostToolUse + SubagentStop)

Seven hooks move work out of "the agent should remember to do this" and into "this always
happens":

- **Developer handoff prompt gate (`SubagentStart`, matcher
  `backend-developer|frontend-developer`)** reviews the orchestrator handoff before code starts. It
  blocks when the implementer lacks a concrete slice, linked PRD/ADR/rules context, Do Not Touch,
  ACs, tests/evidence expectations, provenance, or narrow read scope.

- **Business planning prompt gate (`SubagentStop`, matcher
  `product-owner|business-challenger`)** reviews the PRD phase before architecture starts. It blocks
  when broad work skipped opinionated options, PRDs are not separate proposal folders, PRDs are mixed into feature slice files, PRDs lack
  the required product sections, or large components are not split into linked parent/component PRDs.

- **Architecture planning prompt gate (`SubagentStop`, matcher
  `software-architect|technical-challenger`)** reviews the ADR/slice phase before implementation
  starts. It blocks when accepted PRDs were not converted into ADR proposal folders, slices lack `PRD:` / `ADR:` /
  `Rules:` links, rules are not in the single global `memory/rules.md`, component splits are
  too broad, or Agent Plan rows omit the linked PRD/ADR context downstream agents may grep/read.

- **QA judgment prompt gate (`SubagentStop`, matcher `qa-challenger`)** reviews qa-challenger's
  return before the main thread accepts it. It blocks approvals without a clear slice verdict,
  missing Playwright story coverage/output for user-facing changes, missing deterministic gate
  evidence or agent evidence, missing linked PRD/ADR/rules context, app-code fixes made by
  qa-challenger, or vague findings the orchestrator cannot route.

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

- **`verify-qa.sh` (`SubagentStop`, matcher `qa-checker`)** runs the mechanical QA validators
  before qa-checker can return: QA contract, agent prompt interpretation evidence, Playwright
  story shape, acceptance/test coverage, initial-prompt E2E coverage, and machine-readable QA
  evidence. qa-challenger keeps judgment; this hook owns artifact mechanics.

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
gate runs them) and the original **`qa` agent was split into `qa-checker` and `qa-challenger`**
(the code-first Playwright work and the final merge judgment are different kinds of work, so they
are different agents - neither runs `validate-tools` itself, the gate does). The agents that
remain - orchestrator, product-owner, software-architect, business-challenger,
technical-challenger, the two developers, qa-checker, qa-challenger - each do something a script
cannot. The planning prompt gates are intentionally model-backed because PRD and
ADR quality is judgment work; deterministic validators only check registration and artifact shape.

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
echo '{"agent_type":"qa-checker","tool_input":{"file_path":"src/x.ts"}}' | .codex/hooks/guard-edits.sh
echo '{"agent_type":"backend-developer"}'                                  | .codex/hooks/guard-mcp.sh
echo '{"tool_input":{"file_path":"'"$PWD"'/x.py"}}'                         | .codex/hooks/auto-format.sh
echo '{"agent_type":"backend-developer","stop_hook_active":false}'         | .codex/hooks/verify-subagent.sh
CODEX_REMOTE=true .codex/hooks/session-start.sh
```

For `PreToolUse` guards, a `permissionDecision: "deny"` JSON object = blocked and no output =
allowed. For `verify-subagent.sh`, a `{"decision":"block"}` object = the developer must keep
working and no output = allowed to finish.

Reference: https://code.codex.com/docs/en/hooks
