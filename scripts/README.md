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

These scripts keep mechanical agent-workflow rules out of long prompts.
`scripts/validate/` contains executable entrypoints. Shared validator implementation lives under
`scripts/validate/checks/` so command names do not collide with importable modules.

| Task | Command |
|---|---|
| Full workflow doctor | `python scripts/validate/doctor.py --root .` |
| Run all workflow validators | `python scripts/validate/workflow.py --root .` |
| Scan root/agent/template guidance | `python scripts/validate/agent-guidance.py --root .` |
| Validate feature memories | `python scripts/validate/feature-memory.py --root .` |
| Check feature-memory compaction threshold | `python scripts/validate/compaction.py --root .` |
| Validate Playwright story-test contracts | `python scripts/validate/playwright-stories.py --root .` |
| Validate hook registration and smoke paths | `python scripts/validate/hook-registration.py --root .` |
| Validate stack-local project layout | `python scripts/validate/project-layout.py --root .` |
| Validate backend database policy | `python scripts/validate/database.py --root .` |
| Validate Alembic migration bodies | `python scripts/validate/migrations.py --root .` |
| Validate backend mechanical contracts | `python scripts/validate/backend.py --root .` |
| Validate frontend mechanical contracts | `python scripts/validate/frontend.py --root .` |
| Validate QA Playwright workflow contracts | `python scripts/validate/qa.py --root .` |
| Validate acceptance-criteria test mapping | `python scripts/validate/test-coverage.py --root .` |
| Validate initial-prompt E2E coverage mapping | `python scripts/validate/e2e-coverage.py --root .` |
| Validate deterministic QA evidence | `python scripts/validate/qa-evidence.py --root .` |
| Validate hook/tool command shapes | `python scripts/validate/tooling.py --root .` |
| Validate changed-file ownership and Do Not Touch | `python scripts/validate/ownership.py --root . --agent <agent> --slice <slice.md>` |
| Execute deterministic gate and write QA evidence | `python scripts/validate/gate.py --root . --slice feature-memory/<slice>/slice.md` |
| Summarize Playwright failure output | `python scripts/validate/playwright-output.py <output-file>` |

Most validators accept `--root <path>` and `--json`. `doctor.py` also checks hook JSON, hook
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
