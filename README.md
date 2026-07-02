# vibecoding-template

A starter template for building fullstack web apps with AI - fast, consistent, and production-ready from the first commit.

## What it does

Turns feature requests written in plain English into working, reviewed, mergeable code - following the same architecture and quality standards every time.

You describe what you want. A planner fetches the relevant MCP guideline rules once for the feature slice and writes compact feature memory, a challenger gang stress-tests that plan until it clears a 90 percent acceptance bar, and the orchestrator routes only the agents needed to implement, test, and review the change.

## How it works

Each feature request is routed to the smallest useful set of specialized agents:

- **Orchestrator** - coordinates the plan/challenge loop and routes the work
- **Planner** - understands what you're asking for, fetches guideline rules, writes feature memory, and asks you when something is unclear
- **Challenger** - challenges the plan as a gang of adversarial reviewers and scores it; planning only proceeds at 90 percent acceptance or higher
- **Backend developer** - builds the API and database layer
- **Frontend developer** - builds the UI
- **QA** - generates or heals small-story Playwright specs, reviews the code, and gives a final APPROVED or BLOCKED verdict

The planner fetches only the guideline context needed for the slice, writes compact feature memory, and maps each user-facing E2E story to a Playwright spec. The challenger scores the plan against a panel of personas and loops it back (or asks you) until it reaches 90 percent acceptance. Developers write the implementation tests for their slice, deterministic hooks run validators and test commands, and QA owns Playwright spec generation/healing plus the final APPROVED or BLOCKED verdict.

## Stack

Python / FastAPI backend / Next.js 15 frontend / daisyUI / Alembic migrations

## Get started

```bash
git clone https://github.com/scardoso-lu/vibecoding-template my-project
cd my-project
```

**Don't have Python, Node, uv, Docker, etc.? One command installs all of it:**

```bash
# macOS
bash scripts/bootstrap.sh

# Windows (PowerShell)
powershell -ExecutionPolicy Bypass -File scripts\bootstrap.ps1
```

This installs the entire toolchain - Git, GitHub CLI, jq, uv, Python, Node,
pnpm, playwright-cli, Docker, and Chromium + libs for browser tests - with two supply-chain protections
baked in: every download is signature/hash verified (fail-closed), and no
dependency younger than 2 weeks is ever installed. See
[`scripts/README.md`](scripts/README.md).

### Make it your own repo (run this before pushing)

The clone still points at the template's GitHub repo. Before you push any code,
connect the project to **your** GitHub repo with one command:

```bash
# macOS
bash scripts/init-project.sh

# Windows (PowerShell)
powershell -ExecutionPolicy Bypass -File scripts\init-project.ps1
```

It optionally gives you a clean git history, creates your repo (via the GitHub
CLI, or points at a repo URL you paste), updates the README, and makes the first
push. After that, `git push` works normally.

Then start building:

```bash
claude .
```

Describe a feature and let the agents build it.

## License

MIT
