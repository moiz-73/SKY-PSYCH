# SkyPsych — Presenter Guide for Non-Technical Friends

You can give this pitch. You do not need to understand cameras, code, or AI. You only need to read this sheet, click three things, and say the words in the quotes. That is the whole job.

**The only thing you must remember:** the demo runs itself. Your job is to stay calm, read the lines, and never over-promise.

---

## Before the pitch (days earlier)

1. Open the folder: **`F:\SKY PSYCH\skypsych-ai`**
2. Open the file named **`README_FIRST.txt`** and read it. It is written for you.
3. Double-click **`00_SETUP.bat`** and wait for it to finish. (You only do this once, ever.)
   - If you see a message saying setup is needed, just run **`00_SETUP.bat`** now.
4. Double-click **`01_VALIDATE.bat`** and **wait** until you see **VALIDATION COMPLETE**.
   - If it says setup is still needed, run **`00_SETUP.bat`** again, then **`01_VALIDATE.bat`** again.
5. Close the window. You are done. If you ever see anything else, skip to "If something goes wrong" below.

## One hour before the pitch

1. Double-click **`01_VALIDATE.bat`**. Wait for **VALIDATION COMPLETE**.
2. Double-click **`02_SIM_DEMO.bat`**. A dark window with a **GREEN** banner should appear. Watch it change colors for 45 seconds.
3. Close it with the **Q** key (or **ESC**).
4. Both worked? Great — you are ready. (If not, see "If something goes wrong".)

## During the pitch — exact click order

1. Start your conversation. Say: **"Let me show you what fatigue looks like before it causes an incident."**
2. **Double-click `02_SIM_DEMO.bat`.** The demo window opens. You will see the title **"SkyPsych (SIMULATION MODE)"**.
3. **Narrate the 45-second timeline** — the phases change on their own; you just read:

| When | Screen says | Say |
|------|-------------|-----|
| 0–10s | **GREEN** | "This is a simulated operator in a normal state — healthy and alert." |
| 10–20s | **YELLOW** | "Fatigue signals are rising — slower blinks, longer closures, more head movement." |
| 20–26s | **RED** | "Now it flags critical fatigue — this is when we want a human to act." |
| 26–30s | **MICROSLEEP** | "A microsleep — the operator briefly lost awareness. This is what usually comes before an incident." |
| 30–36s | **NO_FACE** | "Now the operator looks away — notice the system honestly says it cannot see them. It never pretends all is fine." |
| 36–45s | **RECOVERY** | "And recovery — the reading returns toward normal." |

4. When the demo finishes, press **Q** or **ESC**. Say: **"That ran on one laptop. No camera feed was ever saved."**
5. *(Optional)* If the audience wants to see a real face: **double-click `03_LIVE_CAMERA_DEMO.bat`.** Say: **"This is me — the system reading my fatigue live."** Look at the camera. Briefly look away once, so they see the honest "cannot see you" state.
6. Close with your ask — see "How to close the pitch" below.

## If the camera fails during the live demo

- Do not panic. Say: **"Our guaranteed demo is fully simulated; the live camera is an optional extra."**
- Close the live window (**Q** or **ESC**), and go back to the simulation: **double-click `02_SIM_DEMO.bat`** and narrate again.
- Keep talking. The story is unchanged.

## If the demo fails

1. Do not panic. Say: **"Let me show you the validation and pitch materials instead."**
2. Open **`ONE_PAGE_PITCH.md`** — it is the whole story on one page.
3. Walk through it: problem, solution, why now, markets, and the honest note.
4. After the meeting, run **`05_HELP.BAT`** and follow what it prints.

## How to close the pitch

1. Say the ask: **"We are looking for pilots for a demo, honest feedback, and introductions to aviation or defense program managers."**
2. Ask one question: **"Who in your world would want to see this next?"**
3. Say thanks: **"Thank you for your time."**
4. After the meeting, note who asked what and bring it back to the team.

## The "Don't Say" list

Never say any of these — they are false and could hurt people:

- **Never claim it prevents fatigue.** It only reports an estimate.
- **Never claim it is certified.** It is not certified by the FAA, EASA, or anyone.
- **Never claim it is a medical device.** It is not.
- **Never claim it replaces pilots or air-traffic controllers.** It helps a human, it does not replace one.
- **Never claim the reading is medical-grade accuracy.** It is an early, research-level estimate.

The honest short version, if asked: **"This is an advisory early research system — not certified aviation equipment, and not a medical device. It estimates fatigue so a human can act sooner."**

## If something goes wrong (quick reference)

| You see | Do this |
|---------|---------|
| "Setup needed" message | Run **`00_SETUP.bat`**, wait, then run **`01_VALIDATE.bat`** again. |
| Validation fails | Run **`05_HELP.BAT`** and follow the instructions. |
| Demo window won't open | Close other programs, then run **`02_SIM_DEMO.bat`** again. |
| Demo window open and won't close | Press **Q** or **ESC**. |
| Anything else | Run **`05_HELP.BAT`**. Then keep your meeting to the one-pager.