#Requires -Version 5.1
<#
.SYNOPSIS
  Make this clone YOUR project (Windows).

.DESCRIPTION
  A fresh clone of the template still points at the template's GitHub repo, so
  your first push would fail or go to the wrong place. Run this ONCE, before you
  push any code, to:
    1. (optional) wipe the template's git history for a clean start
    2. connect the project to YOUR GitHub repo (creates it via `gh` if available,
       otherwise points at a repo URL you provide)
    3. update the template references in README.md to your repo
    4. make the first commit and push

  (macOS users: use scripts/init-project.sh instead.)

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File scripts\init-project.ps1
#>
[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot  = Split-Path -Parent $ScriptDir
Set-Location $RepoRoot

function Write-Step($m) { Write-Host "==> $m" -ForegroundColor Blue }
function Write-Ok($m)   { Write-Host " ok $m"  -ForegroundColor Green }
function Write-Warn2($m){ Write-Host "warn $m" -ForegroundColor Yellow }
function Die($m)        { Write-Host "ERROR $m" -ForegroundColor Red; exit 1 }
function Have($c)       { [bool](Get-Command $c -ErrorAction SilentlyContinue) }
function Ask($p, $d='') { $r = Read-Host $p; if ([string]::IsNullOrWhiteSpace($r)) { $d } else { $r } }
function Confirm2($p)   { (Ask "$p [Y/n]" 'Y') -match '^[Yy]$' }

if (-not (Have git)) { Die 'git is not installed. Run scripts\bootstrap.ps1 first.' }

$TemplateSlug = 'scardoso-lu/vibecoding-template'
function Slug-FromUrl($u) { ($u -replace '(git@github\.com:|https://github\.com/)','') -replace '\.git$','' -replace '/$','' }

Write-Step 'This connects the project to YOUR GitHub repo and disconnects it from the template.'
$currentOrigin = (git remote get-url origin 2>$null)
if ($currentOrigin) { Write-Step "Current origin: $currentOrigin" }
Write-Host ''

# 1. Project name
$DefaultName = Split-Path -Leaf $RepoRoot
$ProjectName = Ask "Project name [$DefaultName]" $DefaultName

# 2. Decide the GitHub target
$UseGh = $false; $NewSlug = ''; $RepoUrl = ''; $Visibility = 'private'
if ((Have gh) -and (& { gh auth status 2>$null; $LASTEXITCODE -eq 0 })) {
  if (Confirm2 'Create a new GitHub repo now with the GitHub CLI?') {
    $UseGh = $true
    $ghUser = (gh api user -q .login 2>$null)
    $Owner  = Ask "Repo owner [$ghUser]" $ghUser
    if (-not $Owner) { Die 'No owner given.' }
    if ((Ask 'Visibility (private/public) [private]' 'private') -eq 'public') { $Visibility = 'public' }
    $NewSlug = "$Owner/$ProjectName"
  }
}
if (-not $UseGh) {
  Write-Host ''
  Write-Step 'Create an EMPTY repo (no README/license) at: https://github.com/new'
  $RepoUrl = Ask 'Paste your repo URL (https or ssh)'
  if (-not $RepoUrl) { Die 'No repo URL given.' }
  $NewSlug = Slug-FromUrl $RepoUrl
}

# 3. Optional clean git history
$Fresh = Confirm2 'Start with a clean git history (delete the template''s commits)?'

Write-Host ''
Write-Step 'About to:'
$target = if ($NewSlug) { $NewSlug } else { $RepoUrl }
Write-Host "   * connect to: $target $(if ($UseGh) { "($Visibility, via gh)" })"
Write-Host "   * git history: $(if ($Fresh) { 'fresh (template commits removed)' } else { 'kept' })"
if (-not (Confirm2 'Proceed?')) { Die 'Aborted. Nothing changed.' }

# 4. Apply
if ($Fresh) {
  Write-Step 'Resetting git history...'
  Remove-Item -Recurse -Force .git
  git init -q -b main | Out-Null
  $Branch = 'main'
} else {
  $Branch = (git branch --show-current 2>$null)
  if (-not $Branch) { $Branch = 'main' }
}

# Rewrite template references in README so docs point at the new repo.
if ($NewSlug -and (Test-Path README.md) -and (Select-String -Path README.md -Pattern ([regex]::Escape($TemplateSlug)) -Quiet)) {
  (Get-Content README.md -Raw).Replace($TemplateSlug, $NewSlug) | Set-Content README.md -Encoding utf8
  Write-Ok "updated README.md references -> $NewSlug"
}

Write-Step 'Staging and committing...'
git add -A
git diff --cached --quiet
if ($LASTEXITCODE -ne 0) {
  $msg = if ($Fresh) { 'Initial commit' } else { 'chore: connect project to its own repo' }
  git commit -q -m $msg
} else {
  Write-Warn2 'Nothing to commit.'
}

# 5. Connect + push
if ($UseGh) {
  Write-Step "Creating $NewSlug on GitHub and pushing..."
  gh repo create $NewSlug "--$Visibility" --source=. --remote=origin --push
} else {
  git remote remove origin 2>$null
  git remote add origin $RepoUrl
  Write-Step "Pushing to $RepoUrl ($Branch)..."
  git push -u origin $Branch
}

Write-Host ''
Write-Ok "Done. '$ProjectName' is now connected to $target."
Write-Ok 'Push normally from here on with: git push'
