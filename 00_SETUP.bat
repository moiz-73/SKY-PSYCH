@echo off
cd /d "%~dp0"

echo ============================================================
echo   SKYPSYCH AI - FIRST-TIME SETUP
echo ============================================================
echo.
echo This installs the small programs the demo needs.
echo You only need to run this once.
echo.
echo It can take a few minutes. Please do not close this window
echo until it finishes.
echo.

if exist ".venv\Scripts\python.exe" (
    echo Environment already set up.
    echo.
    echo SETUP COMPLETE
    echo Next: double-click 01_VALIDATE.bat
    echo.
    pause
    exit /b 0
)

echo Creating the environment. Please wait...
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\bootstrap_env.ps1"

echo.
echo SETUP COMPLETE
echo Next: double-click 01_VALIDATE.bat
echo.
pause
exit /b 0
