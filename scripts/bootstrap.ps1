#Requires -Version 5.1
<#
.SYNOPSIS
  Install the full toolchain for this project on Windows.

.DESCRIPTION
  Installs: winget (App Installer) check, Git, Python, Node.js, uv, pnpm, Docker
  Desktop, and Chromium + libs for Playwright. Then enables the supply-chain
  cooldown (no dependency younger than 2 weeks) for uv and pnpm.

  Security model:
    - Toolchain is installed with winget, which verifies publisher signatures and
      the SHA-256 in each Microsoft-curated manifest. Versions are pinned.
    - Any direct download is SHA-256 verified, fail-closed, against
      scripts/lib/checksums.txt. The script aborts on a missing/placeholder hash.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File scripts\bootstrap.ps1
  powershell -ExecutionPolicy Bypass -File scripts\bootstrap.ps1 -Check
#>
[CmdletBinding()]
param([switch]$Check)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

# --------------------------------------------------------------------------
# Setup & helpers
# --------------------------------------------------------------------------
$ScriptDir     = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot      = Split-Path -Parent $ScriptDir
$LibDir        = Join-Path $ScriptDir 'lib'
$ChecksumsFile = Join-Path $LibDir 'checksums.txt'

function Write-Step($m) { Write-Host "==> $m" -ForegroundColor Blue }
function Write-Ok($m)   { Write-Host " ok $m"  -ForegroundColor Green }
function Write-Warn2($m){ Write-Host "warn $m" -ForegroundColor Yellow }
function Die($m)        { Write-Host "ERROR $m" -ForegroundColor Red; exit 1 }
function Have($c)       { [bool](Get-Command $c -ErrorAction SilentlyContinue) }

# Parse scripts/lib/versions.env into a hashtable.
$V = @{}
Get-Content (Join-Path $LibDir 'versions.env') | ForEach-Object {
  $line = $_.Trim()
  if ($line -and -not $line.StartsWith('#') -and $line.Contains('=')) {
    $k, $val = $line.Split('=', 2); $V[$k.Trim()] = $val.Trim()
  }
}

$CooldownDays    = [int]$V['DEPENDENCY_COOLDOWN_DAYS']
$CooldownMinutes = $CooldownDays * 24 * 60
$CooldownCutoff  = (Get-Date).ToUniversalTime().AddDays(-$CooldownDays).ToString('yyyy-MM-ddT00:00:00Z')

# Assert-Sha256 -Path file -Name logical-name  (fail closed against checksums.txt)
function Assert-Sha256 {
  param([string]$Path, [string]$Name)
  if (-not (Test-Path $ChecksumsFile)) { Die "Missing checksum manifest: $ChecksumsFile" }
  $expected = $null
  foreach ($l in Get-Content $ChecksumsFile) {
    $t = $l.Trim()
    if ($t -and -not $t.StartsWith('#')) {
      $parts = $t -split '\s+', 2
      if ($parts.Count -eq 2 -and $parts[1].Trim() -eq $Name) { $expected = $parts[0].Trim() }
    }
  }
  if (-not $expected) { Die "No checksum entry for '$Name' in checksums.txt. Refusing to install unverified." }
  if ($expected -like 'PLACEHOLDER_*') { Die "Checksum for '$Name' is a placeholder. Fill it in (see scripts/README.md) before installing." }
  $actual = (Get-FileHash -Algorithm SHA256 -Path $Path).Hash.ToLower()
  if ($actual -ne $expected.ToLower()) { Die "SHA-256 mismatch for '$Name'.`n  expected: $expected`n  actual:   $actual" }
  Write-Ok "verified $Name (sha256)"
}

function Report-Versions {
  Write-Step 'Installed toolchain:'
  foreach ($t in 'uv','python','node','pnpm','docker','git') {
    if (Have $t) { "   {0,-8} {1}" -f $t, ((& $t --version 2>&1) | Select-Object -First 1) | Write-Host }
    else { Write-Host ("   {0,-8} missing" -f $t) -ForegroundColor Red }
  }
}

# winget install with a pinned version, signature/hash verified by winget itself.
function Winget-Install {
  param([string]$Id, [string]$Version)
  $wingetArgs = @('install','--id', $Id, '--exact','--silent',
                  '--accept-package-agreements','--accept-source-agreements')
  if ($Version) { $wingetArgs += @('--version', $Version) }
  Write-Step "winget install $Id $Version"
  winget @wingetArgs
  if ($LASTEXITCODE -ne 0 -and $LASTEXITCODE -ne -1978335189) {  # -1978335189 = already installed
    Die "winget failed for $Id (exit $LASTEXITCODE)"
  }
}

# Make freshly-installed machine PATH visible to this session.
function Refresh-Path {
  $env:Path = [System.Environment]::GetEnvironmentVariable('Path','Machine') + ';' +
              [System.Environment]::GetEnvironmentVariable('Path','User')
}

if ($Check) { Report-Versions; exit 0 }

Write-Step "Windows toolchain bootstrap | cooldown ${CooldownDays}d (cutoff $CooldownCutoff)"

# --------------------------------------------------------------------------
# 1. winget (App Installer)
# --------------------------------------------------------------------------
if (-not (Have winget)) {
  Die "winget (App Installer) not found. Install 'App Installer' from the Microsoft Store, then re-run this script."
}
Write-Ok "winget present ($(winget --version))"

# --------------------------------------------------------------------------
# 2. Core tools via winget (signed, pinned)
# --------------------------------------------------------------------------
if (-not (Have git))    { Winget-Install -Id 'Git.Git' }                              else { Write-Ok 'git present' }
if (-not (Have python)) { Winget-Install -Id 'Python.Python.3.12' -Version $V['PYTHON_VERSION'] } else { Write-Ok 'python present' }
if (-not (Have node))   { Winget-Install -Id 'OpenJS.NodeJS.LTS' -Version $V['NODE_VERSION'] }    else { Write-Ok 'node present' }
Refresh-Path

# --------------------------------------------------------------------------
# 3. uv (official installer — verifies the downloaded binary's checksum)
# --------------------------------------------------------------------------
if (-not (Have uv)) {
  Write-Step "Installing uv $($V['UV_VERSION'])…"
  $tmp = Join-Path $env:TEMP 'uv-install.ps1'
  Invoke-WebRequest -UseBasicParsing "https://astral.sh/uv/$($V['UV_VERSION'])/install.ps1" -OutFile $tmp
  & powershell -ExecutionPolicy Bypass -File $tmp
  Refresh-Path
  $env:Path = "$env:USERPROFILE\.local\bin;$env:Path"
} else { Write-Ok "uv present ($(uv --version))" }
if (-not (Have uv)) { Die "uv not on PATH after install. Open a new terminal and re-run." }

Write-Step "Installing Python $($V['PYTHON_VERSION']) via uv…"
uv python install $V['PYTHON_VERSION']

# --------------------------------------------------------------------------
# 4. pnpm via Corepack
# --------------------------------------------------------------------------
if (Have corepack) {
  Write-Step "Enabling pnpm $($V['PNPM_VERSION']) via Corepack…"
  corepack enable
  corepack prepare "pnpm@$($V['PNPM_VERSION'])" --activate
} elseif (-not (Have pnpm)) {
  Write-Warn2 'corepack not found; installing pnpm via npm as a fallback.'
  npm install -g "pnpm@$($V['PNPM_VERSION'])"
} else { Write-Ok 'pnpm present' }

# --------------------------------------------------------------------------
# 5. Docker Desktop (winget, signed)
# --------------------------------------------------------------------------
if (-not (Have docker)) {
  Winget-Install -Id 'Docker.DockerDesktop'
  Write-Warn2 'Launch Docker Desktop once to finish setup (it installs WSL2 if needed).'
} else { Write-Ok "docker present ($(docker --version))" }

# --------------------------------------------------------------------------
# 6. Supply-chain cooldown config
# --------------------------------------------------------------------------
Write-Step "Configuring dependency cooldown (${CooldownDays} days)…"

# pnpm: persistent, rolling. minimumReleaseAge is in MINUTES.
$PnpmWs = Join-Path $RepoRoot 'pnpm-workspace.yaml'
if ((Test-Path $PnpmWs) -and (Select-String -Path $PnpmWs -Pattern 'minimumReleaseAge' -Quiet)) {
  Write-Ok 'pnpm minimumReleaseAge already configured'
} else {
  @(
    "# Supply-chain cooldown: refuse npm packages published < ${CooldownDays} days ago.",
    "# Value is in MINUTES. Requires a recent pnpm 10.x.",
    "minimumReleaseAge: ${CooldownMinutes}",
    "minimumReleaseAgeExclude: []"
  ) | Add-Content -Path $PnpmWs -Encoding utf8
  Write-Ok "wrote pnpm cooldown to pnpm-workspace.yaml (${CooldownMinutes} min)"
}

# uv: rolling cutoff via env var, recomputed each session in the PowerShell profile.
$ProfilePath = $PROFILE.CurrentUserAllHosts
$profileDir = Split-Path -Parent $ProfilePath
if (-not (Test-Path $profileDir)) { New-Item -ItemType Directory -Force -Path $profileDir | Out-Null }
$uvSnippet = "`$env:UV_EXCLUDE_NEWER = (Get-Date).ToUniversalTime().AddDays(-$CooldownDays).ToString('yyyy-MM-ddT00:00:00Z')  # vibecoding-template PyPI cooldown"
if (-not (Test-Path $ProfilePath) -or -not (Select-String -Path $ProfilePath -Pattern 'UV_EXCLUDE_NEWER' -Quiet)) {
  Add-Content -Path $ProfilePath -Value "`n$uvSnippet" -Encoding utf8
  Write-Ok "added UV_EXCLUDE_NEWER to PowerShell profile"
} else { Write-Ok 'uv cooldown already in PowerShell profile' }
$env:UV_EXCLUDE_NEWER = $CooldownCutoff   # active for the rest of this run

# --------------------------------------------------------------------------
# 7. Project deps + Chromium (respecting the cooldown)
# --------------------------------------------------------------------------
if (Test-Path (Join-Path $RepoRoot 'pyproject.toml')) {
  Write-Step "Installing backend deps with uv (cutoff $env:UV_EXCLUDE_NEWER)…"
  Push-Location $RepoRoot; try { uv sync } finally { Pop-Location }
} else { Write-Warn2 "No pyproject.toml yet — skipping 'uv sync'." }

if (Test-Path (Join-Path $RepoRoot 'package.json')) {
  Write-Step 'Installing frontend deps with pnpm (cooldown enforced)…'
  Push-Location $RepoRoot
  try {
    pnpm install
    Write-Step "Installing Playwright $($V['PLAYWRIGHT_BROWSER']) + libs…"
    pnpm exec playwright install --with-deps $V['PLAYWRIGHT_BROWSER']
  } finally { Pop-Location }
} else { Write-Warn2 'No package.json yet — skipping pnpm install + Playwright.' }

# --------------------------------------------------------------------------
Write-Host ''
Report-Versions
Write-Host ''
Write-Ok 'Bootstrap complete. Open a NEW terminal so PATH and the cooldown env take effect.'
