# Scripts

## Bootstrap

One command sets up the local toolchain.

| Platform | Command |
|---|---|
| macOS | `bash scripts/bootstrap.sh` |
| Windows | `powershell -ExecutionPolicy Bypass -File scripts\bootstrap.ps1` |

Use `--check` for bash or `-Check` for PowerShell to report installed tools without changing
anything. Re-running bootstrap is safe.

## Init Project

A fresh clone still points `origin` at the template repo. Run this once before the first push:

| Platform | Command |
|---|---|
| macOS | `bash scripts/init-project.sh` |
| Windows | `powershell -ExecutionPolicy Bypass -File scripts\init-project.ps1` |

The script asks for the project name, connects the clone to your GitHub repo, can reset template
history, rewrites template references in `README.md`, and pushes the initial commit.

## Workflow Checks

These scripts keep mechanical agent-workflow rules out of long prompts. `scripts/validate/` is a
small layered package with a single entrypoint:

- `cli.py` — **view/entry**: the one CLI. `python scripts/validate/cli.py <check> [--root .] [--json]`.
- `controller.py` — **controller**: the check registry and run orchestration (`all`, `doctor`).
- `services/` — **service**: one module per check domain; each returns `Finding`s or an exit code.
- `repository.py` — **repository**: all filesystem/git/config reads.
- `models.py` — the `Finding` value object and pure parsing helpers.

There are no per-check wrapper files; every check is a subcommand of `cli.py`.

| Task | Command |
|---|---|
| Full workflow doctor | `python scripts/validate/cli.py doctor --root .` |
| Run all workflow validators | `python scripts/validate/cli.py all --root .` |
| Scan root/agent/template guidance | `python scripts/validate/cli.py agent-guidance --root .` |
| Validate memory contracts | `python scripts/validate/cli.py memory --root .` |
| Validate agent prompt interpretation evidence | `python scripts/validate/cli.py agent-evidence --root .` |
| Generate agent evidence hashes | `python scripts/validate/cli.py agent-evidence-hash --root . --file agent-evidence/prompt-N/agent-evidence.json --write` |
| Validate Playwright story-test contracts | `python scripts/validate/cli.py playwright-stories --root .` |
| Validate hook registration and smoke paths | `python scripts/validate/cli.py hook-registration --root .` |
| Validate stack-local project layout | `python scripts/validate/cli.py project-layout --root .` |
| Validate backend database policy | `python scripts/validate/cli.py database --root .` |
| Validate Alembic migration bodies | `python scripts/validate/cli.py migrations --root .` |
| Validate backend mechanical contracts | `python scripts/validate/cli.py backend --root .` |
| Validate frontend mechanical contracts | `python scripts/validate/cli.py frontend --root .` |
| Validate QA Playwright workflow contracts | `python scripts/validate/cli.py qa --root .` |
| Validate acceptance-criteria test mapping | `python scripts/validate/cli.py test-coverage --root .` |
| Validate initial-prompt E2E coverage mapping | `python scripts/validate/cli.py e2e-coverage --root .` |
| Validate deterministic QA evidence | `python scripts/validate/cli.py qa-evidence --root .` |
| Validate hook/tool command shapes | `python scripts/validate/cli.py tooling --root .` |
| Validate changed-file ownership and Do Not Touch | `python scripts/validate/cli.py ownership --root . --agent <agent> --slice <slice.md>` |
| Execute deterministic gate and write QA evidence | `python scripts/validate/cli.py gate --root . --slice memory/feature/<slice>/slice.md` |
| Summarize Playwright failure output | `python scripts/validate/cli.py playwright-output --file <output-file>` |

Most validators accept `--root <path>` and `--json`. `cli.py doctor` also checks hook JSON, hook
launcher syntax, shell hook syntax, and registered smoke paths. The Stop and SubagentStop hooks run
the applicable validators automatically; run these commands manually only when debugging or before
committing workflow changes.

When `docker-compose.yml` exists, the deterministic gate records `docker compose up --build --wait`
and cleanup evidence. The QA evidence validator rejects full slices that do not show a successful
compose startup run.

Run the validator test suite with:

```bash
uv run --with pytest pytest scripts/test_validate
```

## Toolchain Notes

Bootstrap installs Git, GitHub CLI, jq, uv, Python, Node.js, pnpm, playwright-cli, Docker Desktop,
Chromium, and Playwright system libraries when possible.

Toolchain versions live in `scripts/lib/versions.env`. The bootstrap scripts install through signed
package managers where possible and configure a rolling dependency cooldown. When a generated
frontend workspace exists, pnpm cooldown settings belong in `pnpm-workspace.yaml`; until then this
template may not have a root pnpm workspace file.
