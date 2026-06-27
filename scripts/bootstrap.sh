#!/usr/bin/env bash
#
# bootstrap.sh — install the full toolchain for this project on macOS.
#
# Installs via Homebrew: Node.js, Docker Desktop, plus uv (official installer) and
# Python, pnpm (Corepack), and the Chromium browser + libs Playwright needs.
# Then it turns on the supply-chain cooldown (no dependency younger than 2 weeks)
# for uv & pnpm.
#
# (Windows users: use scripts/bootstrap.ps1 instead.)
#
# Security model:
#   - The toolchain comes from Homebrew, which verifies each formula/cask download
#     against the SHA-256 pinned in its manifest.
#   - uv is installed with Astral's official installer, which verifies the
#     downloaded binary's checksum itself; the version is pinned.
#   - Any direct download you add later must go through verify_sha256 (below),
#     which fails closed against scripts/lib/checksums.txt.
#
# Usage:
#   bash scripts/bootstrap.sh            # install everything
#   bash scripts/bootstrap.sh --check    # only report what's installed/missing
#
# Re-running is safe: each step is idempotent and skips work already done.

set -euo pipefail

# --------------------------------------------------------------------------
# Setup & helpers
# --------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LIB_DIR="$SCRIPT_DIR/lib"
CHECKSUMS_FILE="$LIB_DIR/checksums.txt"
CHECK_ONLY=0
[[ "${1:-}" == "--check" ]] && CHECK_ONLY=1

# shellcheck disable=SC1090
set -a; source "$LIB_DIR/versions.env"; set +a

c_reset='\033[0m'; c_red='\033[31m'; c_grn='\033[32m'; c_ylw='\033[33m'; c_blu='\033[34m'
log()  { printf "${c_blu}==>${c_reset} %s\n" "$*"; }
ok()   { printf "${c_grn} ok${c_reset} %s\n" "$*"; }
warn() { printf "${c_ylw}warn${c_reset} %s\n" "$*" >&2; }
die()  { printf "${c_red}ERROR${c_reset} %s\n" "$*" >&2; exit 1; }
have() { command -v "$1" >/dev/null 2>&1; }

[[ "$(uname -s)" == "Darwin" ]] || die "This script is macOS-only. On Windows use scripts/bootstrap.ps1."

# Rolling cooldown cutoff: now minus DEPENDENCY_COOLDOWN_DAYS, recomputed each run.
# macOS ships BSD date; fall back to GNU date if someone has coreutils installed.
cooldown_date_rfc3339() {
  date -u -v-"${DEPENDENCY_COOLDOWN_DAYS}"d +%Y-%m-%dT00:00:00Z 2>/dev/null \
    || date -u -d "${DEPENDENCY_COOLDOWN_DAYS} days ago" +%Y-%m-%dT00:00:00Z
}
COOLDOWN_RFC3339="$(cooldown_date_rfc3339)"
COOLDOWN_MINUTES=$(( DEPENDENCY_COOLDOWN_DAYS * 24 * 60 ))

# verify_sha256 <file> <logical-name-in-checksums.txt> — fail closed.
# Homebrew + the uv installer verify their own downloads, so nothing in this
# script calls this today. Use it for any RAW download you add later.
verify_sha256() {
  local file="$1" name="$2" expected actual
  [[ -f "$CHECKSUMS_FILE" ]] || die "Missing checksum manifest: $CHECKSUMS_FILE"
  expected="$(awk -v n="$name" '$2==n {print $1}' "$CHECKSUMS_FILE" | head -n1)"
  [[ -n "$expected" ]] || die "No checksum entry for '$name' in $CHECKSUMS_FILE. Refusing to install unverified."
  [[ "$expected" == PLACEHOLDER_* ]] && die "Checksum for '$name' is a placeholder. Fill it in (see scripts/README.md) before installing."
  actual="$(shasum -a 256 "$file" | awk '{print $1}')"
  [[ "$actual" == "$expected" ]] || die "SHA-256 mismatch for '$name'.\n  expected: $expected\n  actual:   $actual"
  ok "verified $name (sha256)"
}

report_versions() {
  log "Installed toolchain:"
  for t in brew uv python3 node pnpm docker; do
    if have "$t"; then printf "   %-8s %s\n" "$t" "$("$t" --version 2>&1 | head -n1)"
    else printf "   %-8s ${c_red}missing${c_reset}\n" "$t"; fi
  done
  have uv && printf "   %-8s %s\n" "py(uv)" "$(uv python list --only-installed 2>/dev/null | head -n1 || echo '-')"
}

if [[ "$CHECK_ONLY" == 1 ]]; then report_versions; exit 0; fi

log "macOS toolchain bootstrap | cooldown: ${DEPENDENCY_COOLDOWN_DAYS}d (cutoff ${COOLDOWN_RFC3339})"

# --------------------------------------------------------------------------
# 1. Homebrew
# --------------------------------------------------------------------------
if ! have brew; then
  log "Installing Homebrew (official installer; verifies its own downloads)…"
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi
# Make brew available on PATH for this run (Apple Silicon vs Intel locations).
if ! have brew; then
  for b in /opt/homebrew/bin/brew /usr/local/bin/brew; do [[ -x "$b" ]] && eval "$("$b" shellenv)"; done
fi
have brew || die "Homebrew not on PATH after install. Open a new terminal and re-run."
ok "Homebrew present ($(brew --version | head -n1))"

# --------------------------------------------------------------------------
# 2. uv (also gives us Python)
# --------------------------------------------------------------------------
if ! have uv; then
  log "Installing uv ${UV_VERSION} (official installer verifies the binary checksum)…"
  curl -LsSf "https://astral.sh/uv/${UV_VERSION}/install.sh" | sh
  export PATH="$HOME/.local/bin:$PATH"
else ok "uv present ($(uv --version))"; fi
have uv || die "uv not on PATH after install. Open a new shell or add ~/.local/bin to PATH."

log "Installing Python ${PYTHON_VERSION} via uv…"
uv python install "$PYTHON_VERSION"
uv python pin "$PYTHON_VERSION" 2>/dev/null || true

# --------------------------------------------------------------------------
# 3. Node.js via Homebrew
# --------------------------------------------------------------------------
if ! have node; then
  log "Installing Node ${NODE_VERSION%%.*}.x via Homebrew…"
  brew install "node@${NODE_VERSION%%.*}" || brew install node
  brew link --overwrite --force "node@${NODE_VERSION%%.*}" 2>/dev/null || true
else ok "Node present ($(node --version))"; fi
have node || die "node not on PATH after install. Open a new terminal and re-run."

# --------------------------------------------------------------------------
# 4. pnpm via Corepack (ships with Node)
# --------------------------------------------------------------------------
if have corepack; then
  log "Enabling pnpm ${PNPM_VERSION} via Corepack…"
  corepack enable
  corepack prepare "pnpm@${PNPM_VERSION}" --activate
else
  warn "corepack not found; installing pnpm via Homebrew as a fallback."
  brew install pnpm
fi

# --------------------------------------------------------------------------
# 5. Docker Desktop via Homebrew cask
# --------------------------------------------------------------------------
if ! have docker; then
  log "Installing Docker Desktop via Homebrew cask…"
  brew install --cask docker
  warn "Launch Docker Desktop once from /Applications to finish setup and start the engine."
else ok "Docker present ($(docker --version))"; fi

# --------------------------------------------------------------------------
# 6. Configure the supply-chain cooldown (no dep younger than 2 weeks)
# --------------------------------------------------------------------------
log "Configuring dependency cooldown (${DEPENDENCY_COOLDOWN_DAYS} days)…"

# pnpm: persistent, rolling. minimumReleaseAge is in MINUTES.
PNPM_WS="$REPO_ROOT/pnpm-workspace.yaml"
if [[ -f "$PNPM_WS" ]] && grep -q "minimumReleaseAge" "$PNPM_WS"; then
  ok "pnpm minimumReleaseAge already configured"
else
  {
    echo "# Supply-chain cooldown: refuse npm packages published < ${DEPENDENCY_COOLDOWN_DAYS} days ago."
    echo "# Value is in MINUTES. Requires a recent pnpm 10.x."
    echo "minimumReleaseAge: ${COOLDOWN_MINUTES}"
    echo "minimumReleaseAgeExclude: []"
  } >> "$PNPM_WS"
  ok "wrote pnpm cooldown to pnpm-workspace.yaml (${COOLDOWN_MINUTES} min)"
fi

# uv: rolling cutoff via env var, recomputed every shell start. macOS defaults to zsh.
SHELL_RC="$HOME/.zshrc"; [[ "${SHELL:-}" == *bash ]] && SHELL_RC="$HOME/.bashrc"
COOLDOWN_SNIPPET='# vibecoding-template: PyPI supply-chain cooldown for uv (rolling '"${DEPENDENCY_COOLDOWN_DAYS}"'d)
export UV_EXCLUDE_NEWER="$(date -u -v-'"${DEPENDENCY_COOLDOWN_DAYS}"'d +%Y-%m-%dT00:00:00Z 2>/dev/null || date -u -d "'"${DEPENDENCY_COOLDOWN_DAYS}"' days ago" +%Y-%m-%dT00:00:00Z)"'
if ! grep -q "UV_EXCLUDE_NEWER" "$SHELL_RC" 2>/dev/null; then
  printf "\n%s\n" "$COOLDOWN_SNIPPET" >> "$SHELL_RC"
  ok "added UV_EXCLUDE_NEWER to $SHELL_RC"
else ok "uv cooldown already in $SHELL_RC"; fi
export UV_EXCLUDE_NEWER="$COOLDOWN_RFC3339"   # active for the rest of this run

# --------------------------------------------------------------------------
# 7. Project dependencies + Chromium (respecting the cooldown)
# --------------------------------------------------------------------------
if [[ -f "$REPO_ROOT/pyproject.toml" ]]; then
  log "Installing backend deps with uv (cutoff ${UV_EXCLUDE_NEWER})…"
  (cd "$REPO_ROOT" && uv sync)
else warn "No pyproject.toml yet — skipping 'uv sync'. Run it after the backend is scaffolded."; fi

if [[ -f "$REPO_ROOT/package.json" ]]; then
  log "Installing frontend deps with pnpm (cooldown enforced)…"
  (cd "$REPO_ROOT" && pnpm install)
  log "Installing Playwright ${PLAYWRIGHT_BROWSER} + system libs…"
  (cd "$REPO_ROOT" && pnpm exec playwright install --with-deps "$PLAYWRIGHT_BROWSER")
else
  warn "No package.json yet — skipping pnpm install + Playwright. Run 'pnpm exec playwright install --with-deps chromium' after scaffolding."
fi

# --------------------------------------------------------------------------
echo
report_versions
echo
ok "Bootstrap complete. Open a NEW terminal so PATH and the cooldown env take effect."
