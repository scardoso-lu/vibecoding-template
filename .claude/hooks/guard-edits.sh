#!/usr/bin/env bash
# PreToolUse guard for Edit / Write / MultiEdit - protects files that must not be
# hand-edited, and enforces qa-checker's write scope using the subagent
# identity (agent_type) the hook receives. Emits the PreToolUse deny decision as
# JSON. Fails open (exit 0) if JSON parsing is unavailable.
set -uo pipefail

HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$HOOK_DIR/hook-json.sh"
hook_json_can_parse || exit 0

INPUT="${HOOK_INPUT_JSON:-}"
[ -n "$INPUT" ] || INPUT="$(cat)"
eval "$(hook_json_get_many "$INPUT" FP=tool_input.file_path AGENT=agent_type)"
[ -z "$FP" ] && exit 0
FP="$(hook_json_normalize_path "$FP")"

deny() {
  hook_json_pretool_deny "$1"
  exit 0
}

# Secrets files. .env.example is the tracked template and stays editable.
base="$(basename "$FP")"
case "$base" in
  .env.example)
    : ;;  # allowed
  .env|.env.*)
    deny "editing a secrets file ('$base') is blocked. Put real values in .env by hand; document required keys in .env.example." ;;
esac

# Memory placement contract (any role, including the main thread): planning artifacts only
# live at their contract paths, and memory/ has a fixed layout. The Stop-hook validators catch
# this after the fact; denying the write keeps the bad artifact from existing at all.
case "$base" in
  prd.md)
    case "$FP" in
      */memory/PRD/*/prd.md|memory/PRD/*/prd.md) : ;;
      *) deny "PRDs must live under memory/PRD/<purpose>/prd.md; '$FP' violates the memory contract." ;;
    esac ;;
  adr.md)
    case "$FP" in
      */memory/ADR/*/adr.md|memory/ADR/*/adr.md) : ;;
      *) deny "ADRs must live under memory/ADR/<purpose>/adr.md; '$FP' violates the memory contract." ;;
    esac ;;
  slice.md)
    case "$FP" in
      */memory/feature/*/slice.md|memory/feature/*/slice.md) : ;;
      *) deny "feature slices must live under memory/feature/<feature>/slice.md; '$FP' violates the memory contract." ;;
    esac ;;
esac
case "$FP" in
  */memory/PRD/*|memory/PRD/*|*/memory/ADR/*|memory/ADR/*|*/memory/feature/*|memory/feature/*|\
  */memory/rules.md|memory/rules.md)
    : ;;
  */memory/*|memory/*)
    deny "memory/ may only contain PRD/, ADR/, feature/, and rules.md. Do not create role-specific or ad-hoc memory files ('$FP')." ;;
esac

# Repo-hygiene checks (no secrets committed, migrations apply cleanly) are owned deterministically
# by scripts/validate/** plus guard-commit.sh - never by a slice's own test suite, even one filed
# under a "harness" directory. Matched by filename, not directory: "harness" is also this repo's
# legitimate Test Coverage category for real, AC-mapped feature tests (e.g. a slice's own
# no-raw-value-in-logs or no-retention check) that must stay writable. Only the specific
# repo-hygiene concerns already covered elsewhere are blocked.
base_lower="$(printf '%s' "$base" | tr '[:upper:]' '[:lower:]')"
case "$base_lower" in
  *secrets_committed*|*secret_committed*|*migrations_apply*)
    deny "'$base' duplicates a repo-hygiene check scripts/validate/** and guard-commit.sh already run deterministically (secrets committed / migrations apply cleanly). Cite that existing check in the slice instead of writing a new test for it at '$FP'." ;;
esac

# Read-only challengers: their entire output is a scored critique. Any file write is out of role.
case "$AGENT" in
  business-challenger|technical-challenger|qa-challenger)
    deny "A '$AGENT' subagent is read-only: never edit PRDs, memory, rules, code, or configuration. Return findings in the challenge verdict instead of writing '$FP'." ;;
esac

# Built-in utility subagents (Explore, Plan, general-purpose, ...) may read agent
# infrastructure on the main thread's behalf, but planning memory is written only by the
# owning workflow agents - routing a memory write through a general-purpose helper would
# bypass the owning agent and every gate attached to it.
if hook_json_is_builtin_utility_agent "$AGENT"; then
  case "$FP" in
    */memory/*|memory/*)
      deny "A built-in '$AGENT' subagent may not write memory planning artifacts. PRDs belong to product-owner, ADRs/slices/rules to software-architect, and QA evidence/verdicts to qa-checker; route '$FP' through the owning agent." ;;
  esac
fi

# Role write scopes from the agent contracts (CLAUDE.md + .claude/agents/*.md). The main thread
# (empty agent_type) is unaffected.
case "$AGENT" in
  product-owner)
    case "$FP" in
      */memory/PRD/*|memory/PRD/*|*/agent-evidence/*|agent-evidence/*)
        : ;;
      *)
        deny "product-owner writes only memory/PRD/<purpose>/** and agent-evidence records. ADRs/slices/rules belong to the software-architect and code to the developers; '$FP' is out of scope." ;;
    esac ;;
  software-architect)
    case "$FP" in
      */memory/ADR/*|memory/ADR/*|*/memory/feature/*|memory/feature/*|*/memory/rules.md|memory/rules.md|*/agent-evidence/*|agent-evidence/*)
        : ;;
      *)
        deny "software-architect writes only memory/ADR/**, memory/feature/**, memory/rules.md, and agent-evidence records. PRDs belong to the product-owner and implementation code to the developers; '$FP' is out of scope." ;;
    esac ;;
  backend-developer)
    case "$FP" in
      */frontend/*|frontend/*)
        deny "backend-developer implements backend code; frontend/** belongs to frontend-developer. Report to the main thread instead of writing '$FP'." ;;
      */memory/PRD/*|memory/PRD/*|*/memory/ADR/*|memory/ADR/*|*/memory/rules.md|memory/rules.md)
        deny "planning memory (PRDs, ADRs, memory/rules.md) is written by product-owner/software-architect, not implementers. Request a plan update through the main thread instead of editing '$FP'." ;;
    esac ;;
  frontend-developer)
    case "$FP" in
      */backend/*|backend/*)
        deny "frontend-developer implements frontend code; backend/** belongs to backend-developer. Report to the main thread instead of writing '$FP'." ;;
      */memory/PRD/*|memory/PRD/*|*/memory/ADR/*|memory/ADR/*|*/memory/rules.md|memory/rules.md)
        deny "planning memory (PRDs, ADRs, memory/rules.md) is written by product-owner/software-architect, not implementers. Request a plan update through the main thread instead of editing '$FP'." ;;
    esac ;;
esac

# Role scope: qa-checker may write only deterministic Playwright E2E specs/helpers and the
# terminal slice verdict. Application code, unit tests, config, and non-E2E fixes route through
# the main thread. qa-challenger is read-only (covered by the challenger case above) - it never
# writes slice.md itself; the main thread relays its confirmed verdict to qa-checker to persist.
if [ "$AGENT" = "qa-checker" ]; then
  case "$FP" in
    */frontend/e2e/*|frontend/e2e/*|*/memory/feature/*/slice.md|memory/feature/*/slice.md|*/memory/feature/*/qa-evidence.json|memory/feature/*/qa-evidence.json|*/memory/feature/*/e2e-coverage.json|memory/feature/*/e2e-coverage.json|*/agent-evidence/*/agent-evidence.json|agent-evidence/*/agent-evidence.json)
      : ;;  # allowed
    *)
      deny "qa-checker may write only frontend/e2e/** Playwright specs/helpers, agent-evidence/prompt-N/agent-evidence.json, memory feature QA evidence (qa-evidence.json, e2e-coverage.json), or the slice.md verdict. Route app code, unit-test, config, and non-E2E fixes through the main thread instead of editing '$FP'." ;;
  esac
fi

exit 0

