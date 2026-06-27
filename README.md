# vibecoding-template

A starter template for building fullstack web apps with AI - fast, consistent, and production-ready from the first commit.

## What it does

Turns feature requests written in plain English into working, reviewed, mergeable code - following the same architecture and quality standards every time.

You describe what you want. The orchestrator fetches the relevant MCP guideline rules once for the feature slice, writes compact feature memory, and routes only the agents needed to implement, test, and review the change.

## How it works

Each feature request is routed to the smallest useful set of specialized agents:

- **Orchestrator** - understands what you're asking for and coordinates the work
- **Backend developer** - builds the API and database layer
- **Frontend developer** - builds the UI
- **Tester** - writes and runs focused tests for the feature
- **QA** - reviews the code and gives a final APPROVED or BLOCKED verdict

The orchestrator fetches only the guideline context needed for the slice, writes a compact feature memory, and passes tiny role-specific handoffs to downstream agents. Tester writes and runs tests; QA owns validation, MCP validators, and the final APPROVED or BLOCKED verdict.

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

This installs the entire toolchain — Git, GitHub CLI, jq, uv, Python, Node,
pnpm, Docker, and Chromium + libs for browser tests — with two supply-chain protections
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
