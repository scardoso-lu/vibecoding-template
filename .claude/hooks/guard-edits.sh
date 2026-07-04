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
FP="$(hook_json_get "$INPUT" "tool_input.file_path")"
AGENT="$(hook_json_get "$INPUT" "agent_type")"
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

# Read-only challengers: their entire output is a scored critique. Any file write is out of role.
case "$AGENT" in
  business-challenger|technical-challenger|qa-challenger)
    deny "A '$AGENT' subagent is read-only: never edit PRDs, memory, rules, code, or configuration. Return findings in the challenge verdict instead of writing '$FP'." ;;
esac

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
  orchestrator)
    case "$FP" in
      */memory/*|memory/*|*/backend/*|backend/*|*/frontend/*|frontend/*)
        deny "orchestrator coordinates and routes only: never edit PRDs, ADRs, slices, memory/rules.md, or implementation code ('$FP'). Emit a handoff for the owning agent instead." ;;
    esac ;;
  backend-developer)
    case "$FP" in
      */frontend/*|frontend/*)
        deny "backend-developer implements backend code; frontend/** belongs to frontend-developer. Report to the orchestrator instead of writing '$FP'." ;;
      */memory/PRD/*|memory/PRD/*|*/memory/ADR/*|memory/ADR/*|*/memory/rules.md|memory/rules.md)
        deny "planning memory (PRDs, ADRs, memory/rules.md) is written by product-owner/software-architect, not implementers. Request a plan update through the orchestrator instead of editing '$FP'." ;;
    esac ;;
  frontend-developer)
    case "$FP" in
      */backend/*|backend/*)
        deny "frontend-developer implements frontend code; backend/** belongs to backend-developer. Report to the orchestrator instead of writing '$FP'." ;;
      */memory/PRD/*|memory/PRD/*|*/memory/ADR/*|memory/ADR/*|*/memory/rules.md|memory/rules.md)
        deny "planning memory (PRDs, ADRs, memory/rules.md) is written by product-owner/software-architect, not implementers. Request a plan update through the orchestrator instead of editing '$FP'." ;;
    esac ;;
esac

# Role scope: qa-checker may write only deterministic Playwright E2E specs/helpers and the
# terminal slice verdict. Application code, unit tests, config, and non-E2E fixes route through
# the orchestrator. qa-challenger is read-only (covered by the challenger case above) - it never
# writes slice.md itself; the orchestrator relays its confirmed verdict to qa-checker to persist.
if [ "$AGENT" = "qa-checker" ]; then
  case "$FP" in
    */frontend/e2e/*|frontend/e2e/*|*/memory/feature/*/slice.md|memory/feature/*/slice.md|*/memory/feature/*/qa-evidence.json|memory/feature/*/qa-evidence.json|*/agent-evidence/*/agent-evidence.json|agent-evidence/*/agent-evidence.json)
      : ;;  # allowed
    *)
      deny "qa-checker may write only frontend/e2e/** Playwright specs/helpers, agent-evidence/prompt-N/agent-evidence.json, memory feature QA evidence, or the slice.md verdict. Route app code, unit-test, config, and non-E2E fixes through the orchestrator instead of editing '$FP'." ;;
  esac
fi

exit 0

