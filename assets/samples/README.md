# Sample clips

## Automated-validation sample

`synthetic_no_face.mp4` is the automated-validation sample used by the
camera-free checks:

```bash
python scripts/validate_mvp.py
python main.py --source assets/samples/synthetic_no_face.mp4 --headless \
  --max-frames 20 --output telemetry_smoke.csv
```

It is a fully synthetic 320x240 @ 30 fps clip (~6 s) of drifting geometric
shapes on a dark background. It contains **no human faces** and no text, so
MediaPipe detects nothing; the pipeline must report `coverage=NO_FACE` and
`severity=YELLOW` (never a false-normal GREEN). Do not replace it with a real
recording.

## Optional operator demo clip

`demo.mp4` is optional and operator-supplied. It must be fully synthetic,
rendered, or otherwise de-identified (no identifiable biometric data), and it
is never committed to version control:

```bash
python main.py --source assets/samples/demo.mp4
```

## Privacy notice

**Do not commit raw frames or clips that contain identifiable biometric data.**
Any sample clip used with this repository must be fully synthetic, rendered,
or otherwise de-identified (e.g. animated avatars, license-free stock footage
without real faces). Real operator recordings must never be added to version
control. All processing is local, raw frames are transient, and only abstract
telemetry is logged.