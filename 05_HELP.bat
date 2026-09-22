@echo off
cd /d "%~dp0"

echo ============================================================
echo   SKYPSYCH AI - HELP
echo ============================================================
echo.

if exist "docs\TROUBLESHOOTING.md" (
    echo Opening the troubleshooting guide in Notepad...
    start "" notepad "docs\TROUBLESHOOTING.md"
    echo.
) else (
    echo Note: the troubleshooting guide is not on this computer yet.
    echo.
)

echo Quick summary:
echo.
echo  - The exact double-click sequence is:
echo        1) 01_VALIDATE.bat   (one time, checks everything)
echo        2) 02_SIM_DEMO.bat   (the guaranteed demo)
echo.
echo  - 02_SIM_DEMO.bat needs NO camera.
echo.
echo  - If a program is missing, double-click 00_SETUP.bat to
echo    install the missing Python pieces, then try again.
echo.
echo  - If the camera does not work, keep going anyway. Use
echo    02_SIM_DEMO.bat, which needs no camera. Do not let a
echo    camera problem stop the pitch.
echo.
echo  - If a blue window asks a question, just press any key.
echo.
echo For more help, see the troubleshooting guide above.
echo.
pause
exit /b 0