@echo off
cd /d "%~dp0"

echo ============================================================
echo   SKYPSYCH AI - LIVE CAMERA DEMO  (optional)
echo ============================================================
echo.
echo This demo uses your webcam. If a permission popup appears,
echo click Allow. If you have no webcam, close this window and
echo double-click 02_SIM_DEMO.bat instead.
echo.

if not exist ".venv\Scripts\python.exe" (
    echo First-time setup needed.
    echo Double-click 00_SETUP.bat now, then run this file again.
    echo.
    pause
    exit /b 1
)

echo Looking at your camera now. Press Q or ESC in the video
echo window to end the demo.
echo.

".\.venv\Scripts\python.exe" main.py --source 0 --max-frames 600

echo.
echo The camera demo has finished.
echo If the camera did not work, use 02_SIM_DEMO.bat
echo (simulation needs no camera). See 05_HELP.bat.
echo.
pause
exit /b 0