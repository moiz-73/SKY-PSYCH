@echo off
cd /d "%~dp0"

echo ============================================================
echo   SKYPSYCH AI - HEALTH CHECK  (run once)
echo ============================================================
echo.
echo This checks that everything is installed and working.
echo It takes about a minute. Please wait.
echo.

if not exist ".venv\Scripts\python.exe" (
    echo First-time setup needed.
    echo Double-click 00_SETUP.bat now, then run this file again.
    echo.
    pause
    exit /b 1
)

set "FAILED=0"

echo Step 1 of 3: checking the program's test suite...
echo.
".\.venv\Scripts\python.exe" -m pytest -q
if errorlevel 1 (
    echo.
    echo The test suite had a problem.
    set "FAILED=1"
) else (
    echo.
    echo The test suite passed.
)

echo.
echo Step 2 of 3: running the deep checks...
echo.
".\.venv\Scripts\python.exe" scripts\validate_mvp.py
if errorlevel 1 (
    echo.
    echo The deep checks had a problem.
    set "FAILED=1"
) else (
    echo.
    echo The deep checks passed.
)

echo.
echo Step 3 of 3: running a short simulated run...
echo.
".\.venv\Scripts\python.exe" main.py --simulate --headless --max-frames 120 --output telemetry_sim.csv

echo.
if exist "telemetry_sim.csv" (
    echo The simulated run produced its telemetry file. Good.
) else (
    echo The simulated run did not produce its telemetry file.
    set "FAILED=1"
)

echo.
echo ============================================================
if "%FAILED%"=="1" (
    echo VALIDATION FAILED
    echo One or more checks did not pass.
    echo Double-click 05_HELP.bat for help.
) else (
    echo VALIDATION COMPLETE
    echo Everything is ready. Next: double-click 02_SIM_DEMO.bat
)
echo ============================================================
echo.
pause
exit /b 0