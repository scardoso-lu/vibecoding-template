# Toolchain bootstrap

One command sets up everything this project needs — **you do not need to know how
to install any of it.**

| You're on | Run this |
|---|---|
| **macOS / Linux** | `bash scripts/bootstrap.sh` |
| **Windows** | `powershell -ExecutionPolicy Bypass -File scripts\bootstrap.ps1` |

Add `--check` (bash) or `-Check` (PowerShell) to just report what's installed
without changing anything. Re-running is safe — every step is idempotent.

When it finishes, **open a new terminal** so the updated `PATH` and the cooldown
environment take effect.

## What gets installed

- **uv** — Python package manager (also installs **Python 3.12**)
- **Node.js** (LTS) + **pnpm** (via Corepack)
- **Docker** — Docker Desktop on Windows/macOS, Docker Engine on Linux
- **Chromium** + the system libraries **Playwright** needs (for the
  `e2e-explorer` agent and frontend E2E tests)
- A base package manager if missing — **Homebrew** on macOS

## The supply-chain guarantees

Two protections are wired in, using the package managers' own built-in features
(not hand-rolled checks):

### 1. Everything is hash/signature verified — fail closed

- Toolchain installs go through **signed package managers** — winget (macOS:
  Homebrew; Linux: apt). They verify publisher signatures and package hashes
  themselves. Versions are pinned in [`lib/versions.env`](lib/versions.env).
- The **Node.js** runtime on Linux is verified with **SHA-256 against Node's own
  GPG-signed `SHASUMS256.txt`** — a real, signed checksum, never a value we typed
  in by hand.
- Any other **direct download** is checked against
  [`lib/checksums.txt`](lib/checksums.txt). If an entry is **missing or a
  placeholder, the script aborts** rather than installing something unverified.

> We never invent hashes. If you add a raw download to a script, populate its
> entry in `checksums.txt` from the vendor's published checksum (see that file's
> header for the safe procedure), then commit it.

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
2. If that tool is a **direct download** with a `checksums.txt` entry, refresh its
   hash from the official source (procedure in that file's header) and commit.
3. Re-run the bootstrap.

## Bypassing the cooldown for one package (rare)

Only if you genuinely need a release younger than the window:

- pnpm: add the package name to `minimumReleaseAgeExclude` in
  `pnpm-workspace.yaml`.
- uv: run that one command with `--exclude-newer` overridden, or unset
  `UV_EXCLUDE_NEWER` for a single invocation. Prefer not to.
