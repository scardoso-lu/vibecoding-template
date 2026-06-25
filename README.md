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
claude .
```

Then describe a feature and let the agents build it.

## License

MIT
