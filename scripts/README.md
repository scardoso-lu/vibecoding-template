# Toolchain bootstrap

One command sets up everything this project needs — **you do not need to know how
to install any of it.**

| You're on | Run this |
|---|---|
| **macOS** | `bash scripts/bootstrap.sh` |
| **Windows** | `powershell -ExecutionPolicy Bypass -File scripts\bootstrap.ps1` |

Add `--check` (bash) or `-Check` (PowerShell) to just report what's installed
without changing anything. Re-running is safe — every step is idempotent.

When it finishes, **open a new terminal** so the updated `PATH` and the cooldown
environment take effect.

## Make the clone your own repo (`init-project`)

A fresh clone still points `origin` at the template's GitHub repo, so your first
push would fail or go to the wrong place. **Run this once, before you push any
code:**

| You're on | Run this |
|---|---|
| **macOS** | `bash scripts/init-project.sh` |
| **Windows** | `powershell -ExecutionPolicy Bypass -File scripts\init-project.ps1` |

It interactively:

1. asks your project name,
2. connects to **your** GitHub repo — creates it with the GitHub CLI (`gh`) if
   you're signed in (`gh auth login`), otherwise points at a repo URL you paste,
3. optionally wipes the template's git history for a clean start,
4. rewrites the template references in `README.md`, and
5. makes the first commit and pushes.

After that, `git push` works normally and the project is fully detached from the
template.

## What gets installed

- **Git** + **GitHub CLI** (`gh`) + **jq** for hook JSON parsing
- **uv** — Python package manager (also installs **Python 3.12**)
- **Node.js** (LTS) + **pnpm** (via Corepack)
- **Docker Desktop**
- **Chromium** + the system libraries **Playwright** needs (for the
  `e2e-explorer` agent and frontend E2E tests)
- A base package manager if missing — **Homebrew** (macOS); **winget** is used
  on Windows and must already be present (ships with Windows 10/11)

## The supply-chain guarantees

Two protections are wired in, using the package managers' own built-in features
(not hand-rolled checks):

### 1. Everything is hash/signature verified — fail closed

- Toolchain installs go through **signed package managers** — **Homebrew** on
  macOS, **winget** on Windows. They verify publisher signatures and package
  hashes against their own manifests. Versions are pinned in
  [`lib/versions.env`](lib/versions.env).
- **uv** is installed with Astral's official installer, which verifies the
  downloaded binary's checksum itself; the version is pinned.
- There are **no raw binary downloads** in the scripts, so there is nothing to
  hand-verify. If you ever add one, verify its SHA-256 against the vendor's
  published checksum (`shasum -a 256` / `Get-FileHash`) and abort on mismatch.

### 2. No dependency younger than 2 weeks (rolling cooldown)

Most npm/PyPI supply-chain attacks are a malicious **new version** that gets
caught and pulled within days. Waiting 14 days before adopting any release dodges
almost all of them. This is enforced for **every future install**, not just
during bootstrap:

- **PyPI / uv** → `UV_EXCLUDE_NEWER` is set to *today − 14 days*, recomputed every
  time you open a shell (added to your shell profile). `uv` then refuses any
  release published after that cutoff.
- **npm / pnpm** → `minimumReleaseAge: 20160` (minutes = 14 days) in
  [`../pnpm-workspace.yaml`](../pnpm-workspace.yaml). `pnpm install` refuses any
  version newer than the cooldown.

Change the window in one place — `DEPENDENCY_COOLDOWN_DAYS` in
[`lib/versions.env`](lib/versions.env) — and re-run the bootstrap.

## Updating pinned versions

1. Edit the version in [`lib/versions.env`](lib/versions.env).
2. Re-run the bootstrap. The package manager (Homebrew / winget) or the uv
   installer verifies the new version's integrity for you.

## Bypassing the cooldown for one package (rare)

Only if you genuinely need a release younger than the window:

- pnpm: add the package name to `minimumReleaseAgeExclude` in
  `pnpm-workspace.yaml`.
- uv: run that one command with `--exclude-newer` overridden, or unset
  `UV_EXCLUDE_NEWER` for a single invocation. Prefer not to.
