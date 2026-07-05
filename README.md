# Gesture-Controlled Desktop Assistant — Phase 1

Real-time hand-gesture human-computer-interaction system. Webcam feed →
pretrained hand-landmark model (MediaPipe) → rule-based gesture classifier →
debouncer → OS-level action.

## Architecture
```
Webcam → MediaPipe Hands (landmark extraction, pretrained)
       → classify_gesture() (geometric rules on 21 landmarks)
       → Debouncer (stable_frames + cooldown to avoid spam-firing)
       → actions.dispatch() (maps gesture -> pyautogui OS action)
```

## Gestures (Phase 1 — static poses only)
| Gesture     | Action           |
|-------------|------------------|
| 👍 thumbs up | Volume up        |
| 👎 thumbs down | Volume down    |
| ✌️ peace     | Play / pause media |
| ☝️ point     | Next slide / track |
| 🤟 rock      | Screenshot       |

`none` is an explicit rejection class — no action fires if no known
gesture is confidently detected.

## Run it
```bash
pip install -r requirements.txt
python main.py
```
Press `q` to quit. Move your hand to a screen corner to trigger pyautogui's
failsafe if something misbehaves.

## Why rule-based first (Phase 1)?
MediaPipe's landmark model is pretrained and very robust — no reason to
retrain that. But gesture *classification* here is intentionally simple
geometric rules, so the pipeline (capture → detect → debounce → act) can
be validated end-to-end before any custom ML is introduced.

## Phase 2 (next step)
Replace `classify_gesture()` with a trained model on YOUR OWN landmark
dataset:
1. Collect landmark sequences per gesture (see `collect_data.py`, to be added).
2. Train a small MLP (static gestures) and/or 1D-CNN/LSTM (motion gestures
   like swipe/pinch) on landmark coordinates — not raw images, much
   smaller/faster.
3. Swap the rule-based function for `model.predict(landmarks)`.
4. Report accuracy, confusion matrix, and false-trigger rate on a held-out
   test set you collected yourself.

## Known limitations (be ready to discuss these in an interview)
- Single-hand only (`max_num_hands=1`) — multi-hand handling adds complexity.
- Static poses only — no motion/temporal gestures yet.
- Rule thresholds were tuned by eye, not learned — expected to be brittle
  across very different hand shapes/lighting, which is exactly the
  motivation for Phase 2.
