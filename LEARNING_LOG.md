# Learning Log — Gesture-Controlled Desktop Assistant

This file tracks what was built, what technology was used, why it was
chosen, and what I (should) understand well enough to explain in an
interview. Updated as the project progresses — treat each entry as a
decision record, not just a changelog.

---

## Phase 1 — Pretrained landmark model + rule-based gestures

### Technologies used

| Tool | What it does here | Why chosen |
|---|---|---|
| **MediaPipe Hands** | Detects a hand in the frame and outputs 21 (x,y,z) landmark points per hand | Pretrained, real-time on CPU, avoids needing to train a hand-detector from scratch (needs huge labeled bbox+keypoint data). Internally chains a palm detector + landmark regressor. |
| **OpenCV (cv2)** | Webcam capture, color space conversion (BGR↔RGB), drawing overlays, displaying the window | De facto standard for frame-level video I/O in Python; MediaPipe expects RGB, OpenCV reads BGR by default — important gotcha. |
| **pyautogui** | Simulates OS-level keypresses/screenshots | Simplest way to trigger real OS actions from Python; works via synthetic input events (why it needs OS permission on macOS/some Linux setups). |
| **Rule-based classifier (hand-written)** | Classifies gesture from landmark geometry (finger-extension checks) | No ML model needed yet — lets the rest of the pipeline (capture→detect→act) be verified independently of any model's correctness. |
| **Debouncer (hand-written)** | Requires N stable frames + cooldown before a gesture "fires" | Without this, a held gesture fires 20-30x/sec (once per frame). Classic debouncing concept borrowed from hardware button design. |

### Key design decisions
- **Landmarks over raw images**: MediaPipe reduces a 640x480(ish) image down to 21 points. This is a *massive* dimensionality reduction — makes everything downstream (rules now, ML later) faster and less data-hungry.
- **Detection and action are decoupled** (`gesture_detector.py` vs `actions.py`): detection just outputs a gesture name string; it has zero knowledge of what that gesture *does*. This is a software design choice, not ML, but it's what makes the system extensible.
- **Explicit "none" / rejection class**: a system that always maps to *some* gesture is unusable — accidental hand positions must map to "do nothing."

### Things I still need to be able to explain out loud
- [ ] How does MediaPipe actually get from a frame to 21 points? (palm detector → crop → landmark regressor)
- [ ] Why does the thumb need different logic than the other 4 fingers? (moves sideways, not up/down, relative to palm)
- [ ] Why check landmark *distance from wrist* rather than just y-coordinate for "finger extended"? (works regardless of hand rotation/orientation)
- [ ] What exactly does the debouncer's `stable_frames` vs `cooldown_frames` each protect against?

### Known limitations at this stage
- Single hand only (`max_num_hands=1`).
- Static poses only — no motion/swipe gestures yet.
- Rule thresholds tuned by eye, not learned — expected to be brittle across hand shapes/lighting. This is the direct motivation for Phase 2.

### Environment issue hit + fixed (worth remembering)
- Global Python install already had TensorFlow from earlier ML coursework, with its own protobuf version requirement. Installing `mediapipe` (which transitively needs `tensorflow`) caused a `protobuf` version conflict:
  `ImportError: cannot import name 'runtime_version' from 'google.protobuf'`
- Root cause: pip installs into one shared global `site-packages` by default, so every project on the machine fights over the same package versions.
- Fix applied: pinned `protobuf==4.25.3` to satisfy mediapipe's stated range (`<5, >=4.25.3`).
- Proper long-term fix: use a **virtual environment** (`python -m venv venv`) per project so dependencies never collide across projects again.
- **This is good interview material** — shows real debugging of a dependency conflict, not just "pip install worked."

### First live test results (webcam confirmed working end-to-end)
- Pipeline confirmed working: webcam → landmarks → gesture → debounce → OS action, all live.
- ✌️ peace (play/pause) confirmed to work correctly via Spotify/YouTube — media keys are OS-level (Windows SMTC), not app-specific, so they work regardless of which app is playing.
- 🐛 **Open bug: thumbs up / thumbs down not reliable** — need to determine if this is a *detection* failure (gesture not recognized at all) or a *confusion* failure (up vs down mixed up). Root cause not yet diagnosed — next debugging session.
- Storage clarified: no video/images are persisted anywhere in Phase 1 except the explicit `pyautogui.screenshot()` call in `do_rock()`. Every other frame is processed in-memory and discarded on the next loop iteration. The `venv` folder only stores installed Python packages, unrelated to webcam data.

### Resume framing at this checkpoint
Since the resume was submitted before Phase 2 was finished, used this framing:
> "Built a real-time hand-gesture recognition system using MediaPipe for landmark extraction and a custom rule-based geometric classifier to map 5 hand gestures to OS-level actions (media control, volume, screenshots) via PyAutoGUI. Implemented a debouncing layer to prevent false-trigger spam. (In progress: trained classifier on custom dataset + motion gestures.)"

### Next steps queued up (in priority order)
1. Debug thumbs up/down misclassification — likely a threshold or thumb-orientation logic issue in `_thumb_points_up`/`_thumb_points_down`/`_thumb_extended`.
2. Full line-by-line code walkthrough of all three files (requested — to actually understand every line, not just use it).
3. Design and add motion/temporal gestures (swipe, pinch, hold-to-confirm) — requires moving from single-frame rules to a sequence-based approach (buffer of landmarks over N frames, then a small LSTM/1D-CNN).
4. Expand gesture set + make gesture→action mapping config-driven (JSON) instead of hardcoded.
5. Set up venv properly for this project and reinstall dependencies cleanly inside it.
6. Begin Phase 2 custom dataset collection once rule-based bugs are fixed (fixing rules first avoids labeling data around a buggy baseline).

---

## Phase 2 — Custom dataset + trained classifier (not started yet)

*(to be filled in as we build it: data collection method, dataset size,
model architecture, accuracy/confusion matrix, what changed from the
rule-based version and why)*

---

## Phase 3 — Motion / temporal gestures (not started yet)

*(to be filled in)*
