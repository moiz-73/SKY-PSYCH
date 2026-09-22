# SkyPsych — Demo Talk-Track

Word-by-word narration timed to the 45-second simulation timeline. Run the simulation (`02_SIM_DEMO.bat`), then read the line that matches the phase on screen. Speak slowly — the simulation is the star; your words just frame it.

## Timed narration (45 seconds)

| Time | Screen state | What to say |
|------|--------------|-------------|
| **0–10s** | **GREEN** | "This is a simulated operator in a normal state. The system reads a healthy, alert baseline — green." |
| **10–20s** | **YELLOW** | "Fatigue signals are rising — slower blinks, longer eye closures, more head deviation. The system flags it early, before any error." |
| **20–26s** | **RED** | "Now the system flags critical fatigue. This is the moment we want the right human to look and act." |
| **26–30s** | **MICROSLEEP** | "A microsleep event forces the highest alert — the operator briefly lost awareness. This lapse is exactly what usually precedes an incident." |
| **30–36s** | **NO_FACE** | "Now the operator looks away. Notice what the system does *not* say: it never pretends everything is fine. It tells you it cannot see the operator." |
| **36–45s** | **RECOVERY** | "And here the operator recovers — the reading returns toward normal. Fatigue rises and falls; the system tracks the whole curve, not one instant." |

### Closing line (after 45s / when the window closes)
> "That was the full journey — healthy, warning, critical, microsleep, coverage loss, and recovery — running on one laptop, deterministic and privacy-preserving. No camera feed was ever stored."

---

## What to do during the live camera demo *(optional)*

After the simulation, if you are comfortable, run the live camera demo:

- Say: **"This is me — the system reading my fatigue live."**
- Face the camera normally and keep a steady voice.
- Briefly look away from the camera at least once so you can demonstrate the honest **NO_FACE** behavior — the system should *not* claim green while you are not visible. Point that out.
- If the reading stays green, say: **"I'm alert right now — which is the correct, honest answer."**
- Close with: **"Everything you saw in simulation is exactly the same software — just reading a real face now."**

## If the camera fails

Keep going — the simulation is your guaranteed demo.

1. Say calmly: **"Our guaranteed demo is fully simulated; the live camera is an optional extra."**
2. Switch to (or restart) the simulation and continue narrating normally.
3. Do not improvise excuses. One honest sentence is enough.

## Practical notes for the demo window

- The window title shows **SkyPsych (SIMULATION MODE)** during the simulated demo.
- Press **Q** or **ESC** to close the demo window and return to your presentation.
- The severity banner and warning text move on their own — you do not need to click anything during the 45 seconds.
- If telemetry text scrolls in a terminal behind the window, ignore it; it is the same data, exported to numbers only.