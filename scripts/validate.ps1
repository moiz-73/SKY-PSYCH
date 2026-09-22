# validate.ps1
# Runs the test suite and the end-to-end MVP validation script.
# Stops on first failure ($LASTEXITCODE checks) and prints a PASS/FAIL summary.
# PowerShell 5.1 compatible. Robust to spaces in the repo path.

# NOTE: keep this 'Continue' (not 'Stop'): pytest and MediaPipe write INFO/WARN
# lines to stderr, and $ErrorActionPreference='Stop' would abort the script.
# We rely on explicit $LASTEXITCODE checks instead.
$ErrorActionPreference = 'Continue'

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ScriptDir
$VenvPython = Join-Path $RepoRoot '.venv\Scripts\python.exe'

Set-Location -LiteralPath $RepoRoot

if (-not (Test-Path -LiteralPath $VenvPython)) {
    Write-Host "FAIL: venv python not found at $VenvPython" -ForegroundColor Red
    Write-Host "Run scripts\bootstrap_env.ps1 first."
    exit 1
}

$Failed = $false

# 1) Run pytest.
Write-Host "==> Running pytest ..." -ForegroundColor Cyan
& $VenvPython -m pytest -q
if ($LASTEXITCODE -ne 0) {
    Write-Host "FAIL: pytest failed with exit code $LASTEXITCODE" -ForegroundColor Red
    $Failed = $true
}

# 2) Run MVP validation.
if (-not $Failed) {
    Write-Host "==> Running validate_mvp.py ..." -ForegroundColor Cyan
    & $VenvPython "scripts/validate_mvp.py"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "FAIL: validate_mvp.py failed with exit code $LASTEXITCODE" -ForegroundColor Red
        $Failed = $true
    }
}

# 3) Summary.
Write-Host ""
if ($Failed) {
    Write-Host "VALIDATION FAIL" -ForegroundColor Red
    exit 1
} else {
    Write-Host "VALIDATION PASS" -ForegroundColor Green
    exit 0
}