@echo off
cd /d "%~dp0"

echo ============================================================
echo   SKYPSYCH AI - GUARANTEED DEMO  (no camera needed)
echo ============================================================
echo.
echo This demo needs NO camera. It shows a simulated operator
echo going from GREEN to YELLOW to RED, a microsleep alert,
echo a moment where the camera loses sight of the operator,
echo and then recovery.
echo.
echo Press Q or ESC in the video window to exit the demo.
echo.

if not exist ".venv\Scripts\python.exe" (
    echo First-time setup needed.
    echo Double-click 00_SETUP.bat now, then run this file again.
    echo.
    pause
    exit /b 1
)

".\.venv\Scripts\python.exe" main.py --simulate --simulate-duration 45.0 --demo-loop

echo.
echo The demo has finished.
echo.
echo If you did not see a video window, run:
echo    .\scripts\run.ps1 -Source assets\samples\synthetic_no_face.mp4 -Headless -Output telemetry.csv
echo for a headless check. Or see 05_HELP.bat.
echo.
pause
exit /b 0