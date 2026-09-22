# bootstrap_env.ps1
# Creates/repairs the project-local virtualenv and installs pinned dependencies.
# PowerShell 5.1 compatible. Robust to spaces in the repo path ("F:\SKY PSYCH\skypsych-ai").

# NOTE: keep this 'Continue' (not 'Stop'): pip and python emit INFO/WARN lines
# to stderr, and $ErrorActionPreference='Stop' would abort the script.
# We rely on explicit $LASTEXITCODE checks instead.
$ErrorActionPreference = 'Continue'

# Resolve repo root as parent of this script's directory ($PSScriptRoot/..).
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ScriptDir

Set-Location -LiteralPath $RepoRoot
Write-Host "Repo root: $RepoRoot"

# 1) Create the venv if it does not exist yet.
$VenvPython = Join-Path $RepoRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $VenvPython)) {
    Write-Host "Creating virtualenv '.venv' ..."
    # Prefer the py launcher with an explicit 3.11; fall back to plain `python`.
    py -3.11 -m venv .venv
    if ($LASTEXITCODE -ne 0) {
        Write-Host "py launcher failed, falling back to 'python -m venv .venv' ..."
        python -m venv .venv
        if ($LASTEXITCODE -ne 0) { throw "Failed to create virtualenv." }
    }
} else {
    Write-Host "Virtualenv '.venv' already exists, skipping creation."
}

# 2) Upgrade pip inside the venv.
Write-Host "Upgrading pip ..."
& $VenvPython -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw "pip upgrade failed." }

# 3) Install requirements.
Write-Host "Installing requirements.txt ..."
& $VenvPython -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw "pip install -r requirements.txt failed." }

# 4) Success message with the canonical interpreter path.
Write-Host ""
Write-Host "Environment ready."
Write-Host "Canonical interpreter: $VenvPython"
Write-Host ""
& $VenvPython -c "import cv2, mediapipe, numpy, scipy, yaml, pytest; print('IMPORTS_OK')"