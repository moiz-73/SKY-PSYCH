# SkyPsych AI — Troubleshooting & Presenter Recovery

Plain-English guide for non-technical presenters. You only ever need to
double-click files. No typing required unless a section says so.

## QUICK RECOVERY CHEAT SHEET
Double-click these in order. One line each.
1. **00_SETUP.bat** — Builds the private environment folder (_.venv_) and installs everything. Run it once (or whenever a message says to).
2. **01_VALIDATE.bat** — Self-check. Confirms everything is installed and works. Ends with the green "VALIDATION PASS".
3. **02_SIM_DEMO.bat** — The **guaranteed demo**. Runs the full product with **no camera and no typing**. A HUD window plays a 45-second fatigue story on its own. Press **Q** or **ESC** to close.
4. **05_HELP.bat** — Opens helpful info. Use it any time you feel stuck.

**If validation says "run setup":** run **00_SETUP.bat**, then run **01_VALIDATE.bat** again.

## GOLDEN RULE
**The simulation demo (02_SIM_DEMO.bat) needs NO camera, NO webcam, and NO typing.** It is the one thing you can always fall back on and it always shows the full product. If anything else fails during a pitch, smile, say one of the lines under "What to say while you fix it", and relaunch **02_SIM_DEMO.bat**. When in doubt: **setup, validate, simulate.**

## Failure cases and fixes

### 1. Python not found
- **What you will see:** 00_SETUP.bat window closes instantly, or a message like `'py' is not recognized`.
- **What it means:** The computer does not have the "Python" helper program that 00_SETUP needs. A once-per-computer missing piece.
- **Simplest fix:** Ask your tech contact to install Python 3.11 (check "Add python.exe to PATH" during install), then run **00_SETUP.bat** again.

### 2. .venv missing (environment not built)
- **What you will see:** A launcher says "First-time setup needed" or "Run 00_SETUP.bat first", then stops.
- **What it means:** The private environment folder (_.venv_) has not been created yet on this computer.
- **Simplest fix:** Double-click **00_SETUP.bat**. Wait for it to finish (it can take a few minutes), then **01_VALIDATE.bat** again.

### 3. Dependencies missing
- **What you will see:** An error like `No module named 'mediapipe'` or `pytest` not found.
- **What it means:** A supporting piece of software is missing or outdated.
- **Simplest fix:** Run **00_SETUP.bat** (installs everything), then **01_VALIDATE.bat** again.

### 4. MediaPipe INFO/WARN lines (harmless)
- **What you will see:** Extra yellow/red lines like `WARNING` or `INFO` in the window while everything still runs fine.
- **What it means:** Nothing is wrong. MediaPipe (the face-reading library) always prints these notes. They look alarming but are cosmetic only; ignore them.
- **Simplest fix:** None. Keep watching. This is expected noise.

### 5. Camera not found
- **What you will see:** 03_LIVE_CAMERA_DEMO.bat prints "Could not open video source" or a similar error.
- **What it means:** The program cannot open the camera — none plugged in, it is in use by another app, or it is unplugged.
- **Simplest fix:** Use the guaranteed path: close it and run **02_SIM_DEMO.bat** (no camera needed).

### 6. Camera permission blocked
- **What you will see:** A black or blank window, an operating-system pop-up you denied earlier, or a privacy setting with "camera" turned off.
- **What it means:** Windows is blocking the camera for this program.
- **Simplest fix:** For the demo, do not fight permission blockers — run **02_SIM_DEMO.bat**. (To allow later: Windows Settings → Privacy → Camera → allow apps to use the camera, then relaunch 03_LIVE_CAMERA_DEMO.bat.)

### 7. HUD window does not open
- **What you will see:** 02_SIM_DEMO.bat runs (text appears) but no video window shows.
- **What it means:** Something stopped it before the window could appear — often missing pieces or a one-time glitch.
- **Simplest fix:** Run **00_SETUP.bat**, then **01_VALIDATE.bat**, then **02_SIM_DEMO.bat** again. If all pass and it still will not open, use the headless fallback below so you still deliver the story with numbers.

### 8. Headless mode needed (no display / remote / virtual machine)
- **What you will see:** You are on a remote or VM box with no screen and the HUD window will not appear.
- **What it means:** There is no display for the window, but the product can still stream its numbers out to a chart file.
- **Simplest fix:** Follow the headless fallback below. This is a fallback, not the main demo.

### 9. Simulation mode needed (the safe path)
- **What you will see:** You are unsure a camera will behave during the pitch.
- **What it means:** Simulation runs the **entire** product with a built-in fake story, so no camera and no internet are needed. Perfectly safe and, for a non-camera setup, the **go-to** demo.
- **Simplest fix:** Run **02_SIM_DEMO.bat**. Nothing to install, nothing to type.

### 10. telemetry.csv not created
- **What you will see:** You ran with `--headless --output telemetry.csv` but the file is not where you looked.
- **What it means:** The run stopped before it wrote the export, or the file was written to a different folder. The file is saved inside the project folder (`F:\SKY PSYCH\skypsych-ai`) because that is the working directory every launcher uses.
- **Simplest fix:** Always double-click the `.bat` files (never run from another folder) and check the file in `F:\SKY PSYCH\skypsych-ai`. The run must finish before writing, so use `--max-frames 300` (ends after 300 frames and saves).

### 11. PowerShell execution-policy confusion
- **What you will see:** You opened a `scripts\*.ps1` file directly and got "running scripts is disabled on this system".
- **What it means:** Windows blocks raw PowerShell script files. The `.bat` launchers already bypass this by themselves, so this only bites when you open the `.ps1` files manually.
- **Simplest fix:** Always use the `.bat` files. Never open the `scripts\` or `.ps1` files manually.

### 12. PATH python is wrong
- **What you will see:** A tool uses `python` and gets a different, unrelated Python — but you do **not** see this with the launchers.
- **What it means:** Every launcher calls the project's own interpreter directly (`.\.venv\Scripts\python.exe`), so it never relies on the Windows "PATH" search. That is why this almost never happens here.
- **Simplest fix:** Nothing to fix — use the `.bat` files. (Curious how to check it is the right Python? A "VALIDATION PASS" from 01_VALIDATE.bat means it is.)

### 13. Window closes instantly (bonus "double-clicked and it vanished")
- **What you will see:** You double-clicked a file and the window flashed and closed before you could read it.
- **What it means:** The launchers print their message, **pause automatically** so you can read it, and only close when you press a key — or the program finished on its own.
- **Simplest fix:** Do not worry. Use **05_HELP.bat** for friendly guidance. If you prefer, open a terminal in the folder and type `.\02_SIM_DEMO.bat` so the window stays open — but you never have to.

## Simulation without a window (headless fallback)
Open a terminal in the SkyPsych folder and type:
```
.\.venv\Scripts\python.exe main.py --simulate --headless --max-frames 300 --output telemetry.csv
```
Replace `telemetry.csv` with `telemetry.json` for JSON lines. The file lands in the SkyPsych folder. Use this only if there is no display at all; the visible demo is **02_SIM_DEMO.bat**.

## What to say while you fix it (during a pitch)
- "Our guaranteed demo is fully simulated and needs no camera — give me one moment and we'll relaunch it."
- "That check only touches the computer's settings, not at all the work I'm about to show you. Running the automatic fix now."
- "One moment — the app is just finishing its self-check. It will be up in a few seconds."
- "Everything I'm about to show runs right here on this laptop with your data protected — no camera, no cloud."
- "Here's the live simulation now — watch the operator's fatigue move from healthy, to tired, to microsleep, and back to recovery."
