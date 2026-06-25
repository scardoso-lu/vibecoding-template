# vibecoding-template

A starter template for building fullstack web apps with AI — fast, consistent, and production-ready from the first commit.

## What it does

Turns feature requests written in plain English into working, reviewed, mergeable code — following the same architecture and quality standards every time.

You describe what you want. The AI agents figure out the implementation pattern, write the code, test it, and review it before anything gets merged.

## How it works

Each feature request flows through a pipeline of specialized agents:

- **Orchestrator** — understands what you're asking for and coordinates the work
- **Backend developer** — builds the API and database layer
- **Frontend developer** — builds the UI
- **Tester** — verifies the feature meets the definition of done
- **QA** — reviews the code and gives a final APPROVED or BLOCKED verdict

No agent writes a line of code before consulting the project's architectural guidelines. Every commit cites which guidelines were followed.

## Stack

Python / FastAPI backend · Next.js 15 frontend · daisyUI · Alembic migrations

## Get started

```bash
git clone https://github.com/scardoso-lu/vibecoding-template my-project
cd my-project
claude .
```

Then describe a feature and let the agents build it.

## License

MIT
