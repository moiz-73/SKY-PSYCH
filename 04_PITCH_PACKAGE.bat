@echo off
cd /d "%~dp0"

echo ============================================================
echo   SKYPSYCH AI - PITCH PACKAGE
echo ============================================================
echo.
echo This opens the talking-points guide and the one-page
echo summary for your pitch.
echo.

set "OPENED=0"

if exist "docs\pitch\NON_TECH_PRESENTER_GUIDE.md" (
    start "" "docs\pitch\NON_TECH_PRESENTER_GUIDE.md"
    echo Opened: NON_TECH_PRESENTER_GUIDE.md
    set "OPENED=1"
) else (
    echo Note: the file docs\pitch\NON_TECH_PRESENTER_GUIDE.md is not here yet.
)

if exist "docs\pitch\ONE_PAGE_PITCH.md" (
    start "" "docs\pitch\ONE_PAGE_PITCH.md"
    echo Opened: ONE_PAGE_PITCH.md
    set "OPENED=1"
) else (
    echo Note: the file docs\pitch\ONE_PAGE_PITCH.md is not here yet.
)

if exist "docs\pitch\pitch.html" (
    start "" "docs\pitch\pitch.html"
    echo Opened: pitch.html in your web browser.
    set "OPENED=1"
)

echo.
if "%OPENED%"=="1" (
    echo The pitch documents are now open on your screen.
    echo They may open in Notepad or in your web browser.
) else (
    echo No pitch documents were found on this computer yet.
)

echo.
echo See 05_HELP.bat if you need help.
echo.
pause
exit /b 0