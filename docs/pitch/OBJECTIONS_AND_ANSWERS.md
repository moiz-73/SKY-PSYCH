# SkyPsych — Objections and Answers

*(Ten objections, ten confident, honest answers. Keep your tone steady — never defensive.)*

## 1. "It's just a demo."
It is a working MVP — the demo is the actual pipeline running on a deterministic timeline. The same software reads a real face in live mode. We're proud that it checks out on one laptop with no camera feed stored. The demo is the proof that the core works; the honest next step is validating it with real operators.

## 2. "How do I know it works?"
There is a camera-free validation script — 10 automated checks covering imports, config, telemetry, all three severity states, microsleep forcing RED, and the rule that it is never falsely green when it cannot see you. Everything passes. What we do **not** yet claim is research-grade accuracy against ground truth — that validation is our stated next milestone, not a thing we've invented numbers for.

## 3. "This could give false alarms."
Yes, it can, and I'd rather say that than hide it. In poor light, unusual faces, or occlusion, the index can over-flag or miss. The design reduces this — it never claims healthy when it can't see you, and a microsleep forces the highest alert — but it is an estimate, so it must never be the sole basis for a safety decision. Fewer false alarms is exactly what our validation roadmap targets.

## 4. "Pilots won't accept a camera."
Fair — and why the design removes the usual objections: nothing worn, nothing charged, no cloud, no stored video, no network egress, abstract metrics only. It reads state, not identity. We don't expect zero resistance, and that's why we deliberately want early pilots demos to have those human conversations now, not surprise anyone after a fleet is fitted.

## 5. "Regulators will never approve."
We are not claiming certification, and we are not pretending the path is easy. For the closest markets — UAV ground control and simulation — advisory software can deploy before aviation certification. For regulated aviation, FAA/EASA work is explicitly future and we will do it with them. A deterministic, explainable, auditable index is precisely the kind of thing a certifying body can examine.

## 6. "Webcams can't measure fatigue."
They don't have to measure fatigue directly. They measure involuntary physical signals that fatigue research ties to fatigue — blink duration lengthens, eyes close longer, PERCLOS rises, head pose drifts, and microsleeps appear. A webcam can absolutely observe those. What it can't do — and we don't claim — is prove a person's subjective tiredness, which is why we stay advisory.

## 7. "Why not wearables?"
Wearables have a real adoption problem: hardware to buy, charge, calibrate, and wear, and crews who stop wearing them. Software on an existing camera has no physical barrier and can deploy across a fleet by installing an app. Wearables can add signal (heart-rate, EEG) — that's why sensor fusion is on our roadmap. But the fastest, least objectionable first deployment is camera-only.

## 8. "What about privacy / union concerns?"
This concern is why privacy is the product's architecture, not a patch: no cloud, no raw frames stored, no network calls, abstract telemetry only. We want union and culture conversations early, with real operators, because an accepted advisory tool is the only kind that works in practice. If monitoring feels like surveillance, it will fail — we're building against exactly that failure.

## 9. "This is a liability magnet."
Fair, so let's be precise about the risk management: it is advisory only, it performs no control action, and it explicitly must not be the sole basis for a safety decision — that framing is part of the design, not a weasel word. The bigger liability we all live with is fatigue that goes unseen until an incident. Making fatigue visible is how teams reduce that underlying liability.

## 10. "Can't this be done with a phone app?"
Yes — and that's encouraging, not a threat. A consumer phone that already has a camera is one more deployment surface for the same engine. But the security, privacy, mounting, power, and integration requirements of an aviation and defense control station point to a rugged local software layer on operator workstations, which is exactly what SkyPsych is. Phone support is a natural future downstream surface, not the core product today.

---

### One closing line if they keep pushing
> "The honest answer is that this is early and unvalidated at research-grade. What we have is a real, working, privacy-preserving estimate that runs on an ordinary camera. We're looking for pilots and program managers to help prove how good it can be — with real operators, not just in a lab."