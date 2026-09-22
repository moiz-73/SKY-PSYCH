# SkyPsych AI — Five-Minute Pitch

*(~800–900 words, ~5 minutes at a normal pace. The "Live demo guidance" section tells you what the screen is doing so you can talk over it. PITCH_2_MINUTES.md is the short version.)*

---

## 1. Opening hook

Good morning. Remember one image: a control-room screen that changes color — green, yellow, red — as an operator's fatigue builds, in real time, from an ordinary webcam. No headset. No wristband. No cloud. Just a clear signal: this operator is getting tired, and we should look now, not after the incident.

## 2. The problem

Human error is the leading cause of aviation incidents — and what's less understood is what comes before the error.

Fatigue degrades perception, judgment, and reaction time incrementally — over minutes, not in one visible moment. A tired operator doesn't suddenly become incompetent; they gradually become slower to notice, decide, and react. The error, when it happens, looks like the cause; it is usually the symptom.

Fatigue is invisible to observers and unreliable when self-reported. Today, monitoring usually means wearables — headsets, wristbands, EEG — that operators dislike, fleets struggle to deploy, and crews quietly stop wearing.

## 3. The science — fatigue as an early observable signal

Fatigue leaves observable traces before it produces an error. As a person gets tired, involuntary signals change:

- Blink duration lengthens — the eyes close slower and stay closed longer.
- The fraction of time the eyes are nearly closed rises — researchers call it PERCLOS.
- Eye openness narrows.
- Head position drifts from its normal pose.
- When closure becomes long enough, it is a microsleep — a brief lapse of awareness.

None of these need a device on the body — they're visible on the face and measurable from ordinary video.

## 4. The solution — camera as sensor

SkyPsych AI turns the camera you already have into a cognitive telemetry sensor. The engineering is deliberately honest:

- Computer vision (MediaPipe FaceMesh) extracts facial landmarks in real time from an ordinary webcam.
- Deterministic, rule-based logic — not a black box — computes eye openness, blink dynamics, closure fraction, and head-pose deviation.
- They fuse into a single **Fatigue Index from 0 to 100** on an aviation-style HUD with three states: **GREEN** normal, **YELLOW** rising, **RED** critical.
- A detected **microsleep** forces the highest alert immediately.
- If it cannot see the operator's face, it says exactly that. It is **never** falsely green.

## 5. Live demo guidance

I'll run the guaranteed, fully simulated demo now — a 45-second timeline through every state, identical software to the live version, driven by a synthetic timeline instead of a camera.

*(Double-click `02_SIM_DEMO.bat`. Speak as each phase appears.)*

| Time | Screen | Say |
|------|--------|-----|
| 0–10s | **GREEN** | "This is a simulated operator in a normal state — a healthy, alert baseline." |
| 10–20s | **YELLOW** | "Fatigue signals are rising — slower blinks, longer closures, more head deviation. Flagged before any error." |
| 20–26s | **RED** | "Now it flags critical fatigue — the moment we want the right human to act." |
| 26–30s | **MICROSLEEP** | "A microsleep forces the highest alert — the operator briefly lost awareness. This lapse usually precedes an incident." |
| 30–36s | **NO_FACE** | "The operator looks away. Notice what the system does *not* say: it never claims everything is fine. It says it cannot see the operator." |
| 36–45s | **RECOVERY** | "And recovery — the reading returns toward normal. Fatigue is dynamic; the system tracks the curve, not one instant." |

*(Press Q or ESC to close.)* "That timeline ran on one laptop — deterministically, with no camera feed ever written to disk."

If you like, I can switch to the live camera demo — the same HUD reading a real face. *(Optional: double-click `03_LIVE_CAMERA_DEMO.bat`.)*

## 6. Privacy & edge-native design

Privacy is a feature, not an afterthought:

- **No cloud.** The pipeline runs in one process locally; there are no network calls at runtime.
- **No raw frames stored.** No screenshots or video persisted by default — frames exist only transiently in memory.
- **Abstract telemetry only.** Exports are numbers — nothing that could reconstruct a face.
- **Advisory only.** The system displays, chimes, and logs. It performs no control action on any vehicle or system.

This is the design that lets operators and unions accept it: it reads state, not identity.

## 7. Markets & go-to-market

- **UAV ground control stations** — remote pilots on long shifts; the closest, most urgent fit.
- **Defense simulation** — hours-long training runs where sustained attention is measured.
- **Commercial aviation** — fatigue risk management programs that rely on self-report today.
- **Rail, mining, long-haul trucking** — operators behind sustained, monotonous attention.
- **Remote surgery** — long, exacting procedures.

Go-to-market: start with the closest pilots — UAV and simulation programs — camera-only, software-only, no hardware to ship. Prove the reading is useful, then move toward regulated aviation.

## 8. Roadmap — future, not yet achieved

- **Research validation** — rule-based and deterministic today; research-grade validation against ground-truth fatigue measures is **not** done yet. Future work.
- **Sensor fusion** — adding optional heart-rate or EEG data is planned, not delivered.
- **Industry certifications** — FAA, EASA, and safety certifications are **future** work. We hold none today.

## 9. Ask

We're looking for three things: **pilots for demonstration** — operators who will let us read their fatigue and tell us if the signal matches reality; **honest feedback** on the HUD and thresholds; and **introductions to aviation or defense program managers** who own fatigue risk. Give us twenty minutes with your operations team, and we will show you what fatigue looks like before it causes the incident.

## 10. Honest risk & caveats

I will state the risks plainly, because you deserve them before you decide anything:

- This is an **advisory research MVP**. It estimates fatigue; it does **not** prevent it.
- It is **not** certified aviation equipment and **not** a medical device. We hold **no** regulatory certifications.
- The rule-based index is an estimate. It can produce **false alarms** — and it can **miss** fatigue too, especially in poor lighting or unusual faces.
- It must **never** be used as the sole basis for a safety decision. Its value is informing a human, not replacing one.

The honest pitch is the durable pitch. What we're showing today is the early, working core of a capability we believe belongs in every control room — built with the people who will rely on it.