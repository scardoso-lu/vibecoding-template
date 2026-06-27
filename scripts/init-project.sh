#!/usr/bin/env bash
#
# init-project.sh — make this clone YOUR project (macOS).
#
# A fresh clone of the template still points at the template's GitHub repo, so
# your first push would fail or go to the wrong place. Run this ONCE, before you
# push any code, to:
#   1. (optional) wipe the template's git history for a clean start
#   2. connect the project to YOUR GitHub repo (creates it via `gh` if available,
#      otherwise points at a repo URL you provide)
#   3. update the template references in README.md to your repo
#   4. make the first commit and push
#
# (Windows users: use scripts/init-project.ps1 instead.)
#
# Usage:
#   bash scripts/init-project.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

c_reset='\033[0m'; c_red='\033[31m'; c_grn='\033[32m'; c_ylw='\033[33m'; c_blu='\033[34m'
log()  { printf "${c_blu}==>${c_reset} %s\n" "$*"; }
ok()   { printf "${c_grn} ok${c_reset} %s\n" "$*"; }
warn() { printf "${c_ylw}warn${c_reset} %s\n" "$*" >&2; }
die()  { printf "${c_red}ERROR${c_reset} %s\n" "$*" >&2; exit 1; }
have() { command -v "$1" >/dev/null 2>&1; }
ask()  { local p="$1" d="${2:-}" r; read -rp "$p" r || true; printf '%s' "${r:-$d}"; }
confirm() { local a; a="$(ask "$1 [Y/n]: " Y)"; [[ "$a" =~ ^[Yy]$|^$ ]]; }

have git || die "git is not installed. Run scripts/bootstrap.sh first."

TEMPLATE_SLUG="scardoso-lu/vibecoding-template"
slug_from_url() { echo "$1" | sed -E 's#(git@github\.com:|https://github\.com/)##; s#\.git$##; s#/$##'; }

log "This connects the project to YOUR GitHub repo and disconnects it from the template."
current_origin="$(git remote get-url origin 2>/dev/null || echo '')"
[[ -n "$current_origin" ]] && log "Current origin: $current_origin"
echo

# --------------------------------------------------------------------------
# 1. Project name
# --------------------------------------------------------------------------
DEFAULT_NAME="$(basename "$REPO_ROOT")"
PROJECT_NAME="$(ask "Project name [$DEFAULT_NAME]: " "$DEFAULT_NAME")"

# --------------------------------------------------------------------------
# 2. Decide the GitHub target (gh create, or an existing repo URL)
# --------------------------------------------------------------------------
USE_GH=0; NEW_SLUG=""; REPO_URL=""; VISIBILITY="private"
if have gh && gh auth status >/dev/null 2>&1; then
  if confirm "Create a new GitHub repo now with the GitHub CLI?"; then
    USE_GH=1
    GH_USER="$(gh api user -q .login 2>/dev/null || echo '')"
    OWNER="$(ask "Repo owner [$GH_USER]: " "$GH_USER")"
    [[ -n "$OWNER" ]] || die "No owner given."
    v="$(ask "Visibility (private/public) [private]: " private)"
    [[ "$v" == public ]] && VISIBILITY=public
    NEW_SLUG="$OWNER/$PROJECT_NAME"
  fi
fi
if [[ "$USE_GH" == 0 ]]; then
  echo
  log "Create an EMPTY repo (no README/license) at: https://github.com/new"
  REPO_URL="$(ask "Paste your repo URL (https or ssh): ")"
  [[ -n "$REPO_URL" ]] || die "No repo URL given."
  NEW_SLUG="$(slug_from_url "$REPO_URL")"
fi

# --------------------------------------------------------------------------
# 3. Optional clean git history
# --------------------------------------------------------------------------
FRESH=0
if confirm "Start with a clean git history (delete the template's commits)?"; then
  FRESH=1
fi

echo
log "About to:"
echo "   • connect to: ${NEW_SLUG:-$REPO_URL} ${USE_GH:+($VISIBILITY, via gh)}"
echo "   • git history: $([[ "$FRESH" == 1 ]] && echo 'fresh (template commits removed)' || echo 'kept')"
confirm "Proceed?" || die "Aborted. Nothing changed."

# --------------------------------------------------------------------------
# 4. Apply
# --------------------------------------------------------------------------
if [[ "$FRESH" == 1 ]]; then
  log "Resetting git history…"
  rm -rf .git
  git init -q -b main
  BRANCH=main
else
  BRANCH="$(git branch --show-current 2>/dev/null || echo main)"
  [[ -n "$BRANCH" ]] || BRANCH=main
fi

# Rewrite template references in README so docs point at the new repo.
if [[ -n "$NEW_SLUG" && -f README.md ]] && grep -q "$TEMPLATE_SLUG" README.md; then
  sed -i.bak "s#${TEMPLATE_SLUG}#${NEW_SLUG}#g" README.md && rm -f README.md.bak
  ok "updated README.md references → $NEW_SLUG"
fi

log "Staging and committing…"
git add -A
if git diff --cached --quiet; then
  warn "Nothing to commit."
else
  git commit -q -m "$([[ "$FRESH" == 1 ]] && echo 'Initial commit' || echo 'chore: connect project to its own repo')"
fi

# --------------------------------------------------------------------------
# 5. Connect + push
# --------------------------------------------------------------------------
if [[ "$USE_GH" == 1 ]]; then
  log "Creating $NEW_SLUG on GitHub and pushing…"
  gh repo create "$NEW_SLUG" --"$VISIBILITY" --source=. --remote=origin --push
else
  git remote remove origin 2>/dev/null || true
  git remote add origin "$REPO_URL"
  log "Pushing to $REPO_URL ($BRANCH)…"
  git push -u origin "$BRANCH"
fi

echo
ok "Done. '$PROJECT_NAME' is now connected to $([[ -n "$NEW_SLUG" ]] && echo "$NEW_SLUG" || echo "$REPO_URL")."
ok "Push normally from here on with: git push"
