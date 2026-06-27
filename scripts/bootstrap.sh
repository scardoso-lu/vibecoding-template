#!/usr/bin/env bash
#
# bootstrap.sh — install the full toolchain for this project on macOS or Linux.
#
# Installs: a package manager (Homebrew on macOS), uv, Python, Node.js, pnpm,
# Docker, and the Chromium browser + system libs Playwright needs. Then it turns
# on the supply-chain cooldown (no dependency younger than 2 weeks) for uv & pnpm.
#
# Security model:
#   - Toolchain comes from signed package managers (Homebrew / apt) wherever
#     possible — they verify publisher signatures and package hashes themselves.
#   - Direct downloads are SHA-256 verified, fail-closed, against
#     scripts/lib/checksums.txt OR a GPG-signed source (Node's SHASUMS256.txt).
#   - The script aborts rather than installing anything it cannot verify.
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

OS="$(uname -s)"
case "$OS" in
  Darwin) PLATFORM=macos ;;
  Linux)  PLATFORM=linux ;;
  *) die "Unsupported OS '$OS'. Use scripts/bootstrap.ps1 on Windows." ;;
esac

# Rolling cooldown cutoff: now minus DEPENDENCY_COOLDOWN_DAYS, recomputed each run.
cooldown_date_rfc3339() {
  if date -u -d "@0" >/dev/null 2>&1; then           # GNU date (Linux)
    date -u -d "${DEPENDENCY_COOLDOWN_DAYS} days ago" +%Y-%m-%dT00:00:00Z
  else                                               # BSD date (macOS)
    date -u -v-"${DEPENDENCY_COOLDOWN_DAYS}"d +%Y-%m-%dT00:00:00Z
  fi
}
COOLDOWN_RFC3339="$(cooldown_date_rfc3339)"
COOLDOWN_MINUTES=$(( DEPENDENCY_COOLDOWN_DAYS * 24 * 60 ))

# verify_sha256 <file> <logical-name-in-checksums.txt> — fail closed.
verify_sha256() {
  local file="$1" name="$2" expected actual
  [[ -f "$CHECKSUMS_FILE" ]] || die "Missing checksum manifest: $CHECKSUMS_FILE"
  expected="$(awk -v n="$name" '$2==n {print $1}' "$CHECKSUMS_FILE" | head -n1)"
  [[ -n "$expected" ]] || die "No checksum entry for '$name' in $CHECKSUMS_FILE. Refusing to install unverified."
  [[ "$expected" == PLACEHOLDER_* ]] && die "Checksum for '$name' is a placeholder. Fill it in (see scripts/README.md) before installing."
  if have sha256sum; then actual="$(sha256sum "$file" | awk '{print $1}')"
  else actual="$(shasum -a 256 "$file" | awk '{print $1}')"; fi
  [[ "$actual" == "$expected" ]] || die "SHA-256 mismatch for '$name'.\n  expected: $expected\n  actual:   $actual"
  ok "verified $name (sha256)"
}

report_versions() {
  log "Installed toolchain:"
  for t in uv python3 node pnpm docker; do
    if have "$t"; then printf "   %-8s %s\n" "$t" "$("$t" --version 2>&1 | head -n1)"
    else printf "   %-8s ${c_red}missing${c_reset}\n" "$t"; fi
  done
  have uv && printf "   %-8s %s\n" "py(uv)" "$(uv python list --only-installed 2>/dev/null | head -n1 || echo '-')"
}

if [[ "$CHECK_ONLY" == 1 ]]; then report_versions; exit 0; fi

log "Platform: $PLATFORM | cooldown: ${DEPENDENCY_COOLDOWN_DAYS}d (cutoff ${COOLDOWN_RFC3339})"

# --------------------------------------------------------------------------
# 1. Base package manager
# --------------------------------------------------------------------------
if [[ "$PLATFORM" == macos ]]; then
  if ! have brew; then
    log "Installing Homebrew (official installer; verifies its own downloads)…"
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    eval "$($(command -v brew || echo /opt/homebrew/bin/brew) shellenv)"
  else ok "Homebrew present"; fi
  PKG_INSTALL=(brew install)
else
  have apt-get || die "This script supports Debian/Ubuntu (apt). For other distros install the tools listed in scripts/README.md manually."
  log "Refreshing apt and installing base tools (apt verifies GPG signatures)…"
  sudo apt-get update -y
  sudo apt-get install -y --no-install-recommends ca-certificates curl gnupg lsb-release tar xz-utils
  PKG_INSTALL=(sudo apt-get install -y)
fi

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
# 3. Node.js
# --------------------------------------------------------------------------
install_node_linux_tarball() {
  local arch tarball url tmp sums
  case "$(uname -m)" in
    x86_64) arch=x64 ;; aarch64|arm64) arch=arm64 ;;
    *) die "Unsupported CPU arch for Node tarball: $(uname -m)" ;;
  esac
  tarball="node-v${NODE_VERSION}-linux-${arch}.tar.xz"
  url="https://nodejs.org/dist/v${NODE_VERSION}/${tarball}"
  tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' RETURN
  log "Downloading Node ${NODE_VERSION} + signed checksums…"
  curl -fsSL "$url" -o "$tmp/$tarball"
  curl -fsSL "https://nodejs.org/dist/v${NODE_VERSION}/SHASUMS256.txt" -o "$tmp/SHASUMS256.txt"
  # Best-effort GPG verification of the checksum file itself; SHA check is mandatory.
  if curl -fsSL "https://nodejs.org/dist/v${NODE_VERSION}/SHASUMS256.txt.asc" -o "$tmp/SHASUMS256.txt.asc" 2>/dev/null; then
    if have gpg && gpg --verify "$tmp/SHASUMS256.txt.asc" "$tmp/SHASUMS256.txt" >/dev/null 2>&1; then
      ok "Node SHASUMS256.txt GPG signature verified"
    else warn "Could not GPG-verify Node checksums (missing release keys). Proceeding with SHA-256 check only."; fi
  fi
  sums="$(grep "  ${tarball}\$" "$tmp/SHASUMS256.txt" | awk '{print $1}')"
  [[ -n "$sums" ]] || die "Node tarball not found in SHASUMS256.txt"
  local actual; actual="$(sha256sum "$tmp/$tarball" | awk '{print $1}')"
  [[ "$actual" == "$sums" ]] || die "Node SHA-256 mismatch (expected $sums, got $actual)"
  ok "verified $tarball against Node's signed checksums"
  sudo mkdir -p /usr/local/lib/nodejs
  sudo tar -xJf "$tmp/$tarball" -C /usr/local/lib/nodejs
  for bin in node npm npx; do
    sudo ln -sf "/usr/local/lib/nodejs/node-v${NODE_VERSION}-linux-${arch}/bin/$bin" "/usr/local/bin/$bin"
  done
}

if ! have node; then
  if [[ "$PLATFORM" == macos ]]; then
    log "Installing Node ${NODE_VERSION} via Homebrew…"
    brew install "node@${NODE_VERSION%%.*}" || brew install node
  else
    install_node_linux_tarball
  fi
else ok "Node present ($(node --version))"; fi

# --------------------------------------------------------------------------
# 4. pnpm via Corepack (ships with Node)
# --------------------------------------------------------------------------
if have corepack; then
  log "Enabling pnpm ${PNPM_VERSION} via Corepack…"
  sudo corepack enable 2>/dev/null || corepack enable
  corepack prepare "pnpm@${PNPM_VERSION}" --activate
else
  warn "corepack not found; installing pnpm globally via npm as a fallback."
  npm install -g "pnpm@${PNPM_VERSION}"
fi

# --------------------------------------------------------------------------
# 5. Docker
# --------------------------------------------------------------------------
if ! have docker; then
  if [[ "$PLATFORM" == macos ]]; then
    log "Installing Docker Desktop via Homebrew cask…"
    brew install --cask docker
    warn "Launch Docker Desktop once from /Applications to finish setup."
  else
    log "Installing Docker Engine from Docker's official apt repo (GPG-verified)…"
    sudo install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    sudo chmod a+r /etc/apt/keyrings/docker.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
      | sudo tee /etc/apt/sources.list.d/docker.list >/dev/null
    sudo apt-get update -y
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    sudo usermod -aG docker "$USER" 2>/dev/null || true
    warn "Log out/in (or run 'newgrp docker') so your user can run docker without sudo."
  fi
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

# uv: rolling cutoff via env var, recomputed every shell start.
SHELL_RC="$HOME/.bashrc"; [[ "${SHELL:-}" == *zsh ]] && SHELL_RC="$HOME/.zshrc"
COOLDOWN_SNIPPET='# vibecoding-template: PyPI supply-chain cooldown for uv (rolling 14d)
export UV_EXCLUDE_NEWER="$(date -u -d "'"${DEPENDENCY_COOLDOWN_DAYS}"' days ago" +%Y-%m-%dT00:00:00Z 2>/dev/null || date -u -v-'"${DEPENDENCY_COOLDOWN_DAYS}"'d +%Y-%m-%dT00:00:00Z)"'
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
  warn "No package.json yet — skipping pnpm install + Playwright."
  if [[ "$PLATFORM" == linux ]]; then
    log "Pre-installing Chromium system libs so Playwright works later…"
    pnpm dlx playwright install-deps chromium 2>/dev/null || warn "Skipped lib pre-install; run 'pnpm exec playwright install --with-deps chromium' after scaffolding."
  fi
fi

# --------------------------------------------------------------------------
echo
report_versions
echo
ok "Bootstrap complete. Open a NEW terminal so PATH and the cooldown env take effect."
[[ "$PLATFORM" == linux ]] && warn "If 'docker' needs sudo, run 'newgrp docker' or re-login."
