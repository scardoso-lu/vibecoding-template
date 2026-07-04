#!/usr/bin/env bash
# SessionStart hook — bootstrap the dev toolchain for Claude Code on the web.
#
# Installs backend/frontend dependencies when their manifests exist so tests and
# linters are ready in a fresh remote container. Idempotent, non-interactive, and
# fail-tolerant: a failed install logs a warning but never blocks the session.
#
# Runs synchronously (deps are guaranteed before the agent loop starts). Switch to
# async mode if you prefer faster startup at the cost of a startup race window.
set -uo pipefail

# Only bootstrap in the remote (Claude Code on the web) environment; local sessions
# manage their own toolchain via scripts/bootstrap.sh.
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

ROOT="${CLAUDE_PROJECT_DIR:-$(pwd)}"
cd "$ROOT" || exit 0

log() { printf '[session-start] %s\n' "$1"; }

# Backend: uv-managed Python project.
if [ -f "pyproject.toml" ]; then
  if command -v uv >/dev/null 2>&1; then
    log "pyproject.toml found — running 'uv sync'"
    uv sync || log "WARN: 'uv sync' failed; continuing"
  else
    log "WARN: pyproject.toml present but 'uv' is not installed (see scripts/bootstrap.sh)"
  fi
fi

# Validators: the deterministic gate (verify-subagent.sh) runs `validate-tools run`.
# Make the CLI available so the gate enforces compliance instead of skipping it.
if command -v uv >/dev/null 2>&1 && ! command -v validate-tools >/dev/null 2>&1; then
  log "installing validate-tools (used by the SubagentStop gate)"
  uv tool install validate-tools || log "WARN: 'uv tool install validate-tools' failed; gate will skip validators"
fi

# A missing validate-tools silently downgrades verify-subagent.sh's compliance gate to
# ruff/mypy/pytest only (it does `have validate-tools || return 0` per check) - a WARN buried among
# routine install logs is easy to miss. Make this unmissable: SessionStart stdout is added back
# into context (see reinject-context.sh), so this block surfaces on every turn until resolved.
if ! command -v validate-tools >/dev/null 2>&1; then
  cat <<'EOF' >&2
[session-start] WARNING: 'validate-tools' is not on PATH in this remote session.
  verify-subagent.sh silently skips every validate-tools compliance check when the CLI is
  missing - the developer SubagentStop gate is running degraded (ruff/mypy/pytest only, no
  compliance scan). Install it manually with 'uv tool install validate-tools' or fix the
  failed install above; do not treat a green developer gate as compliance-checked until this
  is resolved.
EOF
  log "WARNING: validate-tools still unavailable - the SubagentStop compliance gate is running degraded (see stderr)"
fi

# Frontend: pnpm-managed Node project.
if [ -f "package.json" ]; then
  if command -v pnpm >/dev/null 2>&1; then
    log "package.json found — running 'pnpm install'"
    pnpm install || log "WARN: 'pnpm install' failed; continuing"
  else
    log "WARN: package.json present but 'pnpm' is not installed (see scripts/bootstrap.sh)"
  fi
fi

if [ ! -f "pyproject.toml" ] && [ ! -f "package.json" ]; then
  log "No backend/frontend manifests yet — template scaffold only, nothing to install."
fi

log "ready"
exit 0
