# vibecoding-template

A starter template for building fullstack web apps with AI - fast, consistent, and production-ready from the first commit.

## What it does

Turns feature requests written in plain English into working, reviewed, mergeable code - following the same architecture and quality standards every time.

You describe what you want. A product owner writes PRDs in `memory/PRD/`, a software architect writes ADRs in `memory/ADR/`, fetches the relevant MCP guideline rules once, and derives feature slices in `memory/feature/`. Business and technical challengers stress-test the plan until both clear a 90 percent acceptance bar, and the main thread routes only the agents needed to implement, test, and review the change.

## How it works

**Orchestration happens on the main thread - there is no separate orchestrator agent.** The main
thread itself sequences the plan/challenge loop and routes each feature request to the smallest
useful set of specialized agents:

- **Product owner** - understands what you're asking for, defines business slices, user stories, acceptance behavior, and product questions
- **Software architect** - fetches guideline rules, writes ADRs, completes technical contracts and feature slices, and emits the implementation plan
- **Business challenger** - challenges product fit, scope, user outcomes, acceptance behavior, and business risk
- **Technical challenger** - challenges provenance, architecture, contracts, feasibility, coverage, operations, and security
- **Backend developer** - builds the API and database layer
- **Frontend developer** - builds the UI
- **QA** - generates or heals small-story Playwright specs, reviews the code, and gives a final APPROVED or BLOCKED verdict

The product owner writes PRDs, the software architect converts them into ADRs and feature slices, and each user-facing slice maps E2E stories to planned coverage. The business and technical challengers score their domains against persona panels and loop the plan back (or ask you) until both reach 90 percent acceptance. Developers write implementation tests for their slice, deterministic hooks run validators and test commands, and QA owns Playwright spec generation/healing plus the final APPROVED or BLOCKED verdict.

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
