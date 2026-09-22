# SkyPsych — Likely Questions and Honest Answers

*(For investors and prospects. Every answer is short, and every answer is honest.)*

## 1. How accurate is it? How do we know it works?
This is an early MVP. The fatigue index is computed by deterministic, rule-based logic from face landmarks — not a trained model. We have validated that the pipeline behaves correctly (unit tests and synthetic scenarios), but we have **not** yet done research-grade validation against ground-truth fatigue measures. That validation is the next milestone, not something we claim today.

## 2. How private is it really?
Everything runs locally in one process. There are no network calls at runtime, no cloud, no API keys, and no raw frames, screenshots, or video stored by default. Only abstract numbers — blink rate, closure fraction, head position, fatigue index — can be exported. Your image never leaves the machine.

## 3. What hardware does it need?
An ordinary webcam. That is the entire requirement. MediaPipe FaceMesh runs in real time on a standard laptop. No wearable, no special sensor, no GPU required.

## 4. What is the latency?
Real-time and fully local. The pipeline processes each frame and updates the HUD continuously; there is no round-trip to a server. Perceived lag is near-instant (frame-rate bound, plus a small smoothing delay built into the metrics).

## 5. How is this different from fatigue wearables (wristbands, EEG headsets)?
Wearables require hardware to buy, charge, wear, and accept. SkyPsych is software-only on hardware that already exists. It can be deployed across a fleet by installing an app. It is also non-contact, so crews have nothing to refuse — which is often the single biggest adoption barrier.

## 6. Is it certified? Is it approved by the FAA or EASA?
No. It is an advisory research MVP with no regulatory certifications. Aviation certification (FAA/EASA) and medical standing are explicitly future work and not achieved. We say this unambiguously, because it is a safety-adjacent field and trust matters more than optics.

## 7. Who is the competition?
The category includes wearable fatigue monitors (wristbands, EEG), and academic/industrial gaze-and-drowsiness research. Most require hardware or are research projects without a product shell. Our differentiation is software-only, camera-only, deterministic (auditable), and privacy-preserving by design. The honest caveat: the field is crowded; we are not yet the validated standard, and we are early.

## 8. What is the business model?
For the MVP, licensing to operators — UAV ground control, simulation, and fatigue-risk programs — as a software subscription or site license. Later, OEM integration into control-station and fleet-management platforms. Pricing is not set; the first goal is proving the signal is useful to real operators.

## 9. Who is the team?
The core team is the engineering and research group behind this working MVP — a full pipeline implemented, tested, and validated end-to-end. The pitch today is asking for the partnerships (pilots, feedback, program managers) needed to grow the team and the evidence base.

## 10. How big is the market?
Fatigue affects every safety-critical operation that involves sustained attention — UAV ground control, defense simulation, commercial aviation, rail, mining, long-haul trucking, and remote surgery. We are not presenting a market-size number today; the honest framing is that any operation with cameras and tired humans is addressable, and we plan to validate demand in the nearest segments first.

## 11. How is it regulated, and what changes in production?
Today, none of it is regulated — it is an advisory research tool. Production deployment in aviation would require certification work with regulators (FAA/EASA), formal validation, and documentation. For non-aviation markets (simulation, mining, rail, trucking), the bar is lower but still requires evidence of reliable behavior. This is all future work.

## 12. Could it give false alarms? Could it miss fatigue?
Yes to both, honestly. In poor lighting, unusual face geometry, glasses, or partial occlusion, readings can degrade or miss. A healthy operator blinking slowly could trigger a caution. The design reduces risk — it is never falsely green when it cannot see the operator, and a microsleep forces the highest alert — but it is an estimate, not a ground truth, and must never be the sole basis for a safety decision.

## 13. What would make it production-ready?
(1) Research-grade validation against ground-truth fatigue measures; (2) broader testing across lighting, faces, and occlusion; (3) sensor fusion (heart-rate, EEG) for stronger evidence; (4) industry certifications for regulated markets; and (5) hardening, packaging, and an enterprise deployment story. None of these are done yet — they are the roadmap.

## 14. Does it replace pilots or air-traffic controllers?
No — and it never should. It is an advisory layer that informs the right human decision. It performs no control actions on any vehicle or system. Its entire purpose is to make fatigue visible so a human can act sooner, not to remove humans from the loop.

## 15. How do operators respond to a camera watching them?
This is a real concern and we respect it. The design answers it directly: no cloud, no storage of faces, no network egress, abstract metrics only. Privacy is the product's architecture, not a patch. We also position it as non-contact monitoring that requires nothing worn, which historically drives higher acceptance. We expect union and culture conversations and want to have them early with real operators.

## 16. Is the demo a fake — is that really the software working?
The simulation is the real software, driven by a synthetic timeline instead of a camera — the same fusion, the same HUD, the same alerts. We are transparent that the "operator" in the demo is simulated. The live-camera demo reads a real face with the identical pipeline. Nothing in the demo is pre-recorded.

## 17. Why should I believe a rule-based system is better than ML?
It is not "better" — it is more honest. Rules are auditable: every threshold is visible and explainable, which matters enormously for certification and for operator trust. The plan is to use validation data to tune those rules and, where it helps, add learned components later. Determinism today is a feature for this market, not a limitation.

## 18. What is the honest risk in this project?
The biggest risks: the fatigue signal may not be strong enough without additional sensors; validation is not yet done, so real-world accuracy is unproven; certification timelines are long; and the category has existing competitors. We are de-risking by starting with the easiest, most eager segments — UAV and simulation — where advisory software can be deployed without certification first.