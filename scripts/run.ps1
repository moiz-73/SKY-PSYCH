# run.ps1
# Runs the SkyPsych AI main entry point with the project venv interpreter.
# PowerShell 5.1 compatible. Uses the call operator + array splicing so paths with spaces work.
#
# Parameters:
#   -Source        Mandatory. Camera index (e.g. "0") or a video file path (e.g. "assets/samples/demo.mp4").
#   -Headless      Switch. Pass --headless (no GUI).
#   -Output        String, default "". If provided, pass --output <Output>.
#   -MaxFrames     Int, default 0 (0 means unset). If > 0, pass --max-frames <n>.
#   -Config        String, default "config/settings.yaml". Pass --config <Config>.
#   -ShowLandmarks Switch. Pass --show-landmarks.

param(
    [Parameter(Mandatory = $true)]
    [string]$Source,
    [switch]$Headless,
    [string]$Output = "",
    [int]$MaxFrames = 0,
    [string]$Config = "config/settings.yaml",
    [switch]$ShowLandmarks
)

# NOTE: keep this 'Continue' (not 'Stop'): main.py and MediaPipe write INFO/WARN
# lines to stderr, and $ErrorActionPreference='Stop' would abort the run. We rely
# on explicit $LASTEXITCODE checks instead.
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

# Build the argument list (array splicing keeps spaced paths intact).
$ArgsList = @('main.py', '--source', $Source, '--config', $Config)
if ($Headless) { $ArgsList += '--headless' }
if ($Output -ne "") { $ArgsList += '--output', $Output }
if ($MaxFrames -gt 0) { $ArgsList += '--max-frames', ([string]$MaxFrames) }
if ($ShowLandmarks) { $ArgsList += '--show-landmarks' }

# Informational message showing the exact command being run.
$CommandLine = "& '$VenvPython' " + (($ArgsList | ForEach-Object { "'$_'" }) -join ' ')
Write-Host "Running:" -ForegroundColor Cyan
Write-Host $CommandLine
Write-Host ""

& $VenvPython @ArgsList
exit $LASTEXITCODE