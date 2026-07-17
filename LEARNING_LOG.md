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

## Phase 2 — Custom dataset + trained classifier

### Technologies & Methods used

| Concept | What it does here | Why chosen / Key advantage |
|---|---|---|
| **Landmark Normalization** | Subtracts wrist (landmark 0) from all landmarks; divides all by the maximum landmark distance to the wrist. | Provides **translation-invariance** (hand position in frame doesn't matter) and **scale-invariance** (hand distance to camera doesn't matter). Prevents real-world model confusion. |
| **GridSearchCV Tuning** | Explores hyperparameter space (capacity, regularization, estimator sizes) using 5-fold cross-validation. | Empirically selects optimal model configurations instead of guessing parameters. |
| **MLP Classifier** | Multi-layer Perceptron (Neural Network) predicting hand gestures from normalized landmarks. | Achieved **98.36% test accuracy** after normalization (up from 95.67%), outperforming Random Forest (97.01%) and resolving Point vs. Rock confusion. |
| **Sample Rate Limiter** | Caps recording speed to at most 15 FPS (every 0.066s). | Prevents collecting thousands of identical, redundant frames. Forces user to record diverse hand angles/distances. |

### Things I still need to be able to explain out loud
- [ ] Why does raw absolute coordinate training cause the model to fail in real life despite high test split scores? (Data leakage/overfitting to absolute image position and distance).
- [ ] How does vector translation (subtracting $x_0, y_0, z_0$) make the hand origin-centered?
- [ ] How does scale normalization keep features bounded between -1.0 and 1.0?
- [ ] Why did normalization benefit the MLP model performance more than the Random Forest model? (Neural networks are highly sensitive to unscaled input features; Random Forests are scale-invariant but benefit from cleaner bounding).

### Environment & Dataset Stats
- **Dataset Size**: ~6,900 samples across 6 classes (`none`, `peace`, `point`, `rock`, `thumbs_down`, `thumbs_up`).
- **Classifier Saved**: `gesture_model.pkl` (best-performing MLP configuration).

---

## Phase 3 - Motion / temporal gestures with a PyTorch LSTM

### What changed

- Replaced the single-frame MLP runtime with a PyTorch LSTM that consumes 20-frame landmark sequences.
- Expanded the labels to nine classes: `none`, four static gestures, and four swipe directions.
- Preserved wrist displacement across the sequence so motion remains visible to the model while keeping finger pose wrist-relative and scale-normalized.
- Mirrored left-hand pose coordinates so one model can recognize either hand more consistently.
- Added a confidence threshold of `0.8`; lower-confidence predictions become `none`.
- Initially added frame-count gesture cooldowns, then replaced them with monotonic time deadlines so behavior no longer changes with webcam FPS.
- Saved the active checkpoint as `gesture_model.pth`, including model weights and label mappings. The older `gesture_model.pkl` is now a legacy artifact.

### Current dataset

The active CSV contains 1,387 recorded sequences:

| Label | Sequences |
|---|---:|
| `none` | 484 |
| `thumbs_up` | 62 |
| `thumbs_down` | 63 |
| `fist` | 95 |
| `peace` | 80 |
| `swipe_left` | 200 |
| `swipe_right` | 131 |
| `swipe_up` | 152 |
| `swipe_down` | 120 |

This is enough to exercise the full pipeline, but the class imbalance should be addressed before treating accuracy as a strong quality measure. Per-class precision/recall and the confusion matrix matter more than overall accuracy alone.

### Desktop application layer

- `tray.py` is now the main entry point and keeps the camera off until recognition is enabled.
- `config_gui.py` edits `gestures_config.json` and supports the same action types as the dispatcher: built-in actions, executable paths, URIs, scripts, and hotkeys.
- `app_discovery.py` scans Windows Start Menu shortcuts and caches resolved executable paths.
- `setup_shortcuts.py` creates Desktop and Start Menu launchers and configures per-user auto-start. Development launchers use `pythonw.exe`; packaged launchers use `GestureAssistant.exe`.
- The tray now provides a graceful Exit action and a camera-preview toggle. Hiding the preview leaves recognition active while skipping landmark drawing, overlays, and window rendering. The last confident label remains visible for `1.5` seconds so brief predictions are readable without changing action timing.
- The tray sends only lifecycle notifications: recognition ready, user-requested stop, and startup/runtime errors. Gesture detections and actions remain silent.
- Each configured gesture can be enabled or disabled independently. Disabling blocks dispatch without changing or retraining the model, and old configuration files remain enabled by default.
- A named Windows mutex prevents duplicate tray processes, and an HKCU Run entry provides a user-controlled Start with Windows option without administrator privileges.
- A PyInstaller one-folder build gives the process its own Task Manager name.
- Packaged writable state lives under `%LOCALAPPDATA%\GestureAssistant` instead of the temporary PyInstaller resource directory.

### Distribution checkpoint verified

- The PyInstaller one-folder build launches successfully and appears as `GestureAssistant` in Task Manager.
- Duplicate launch testing leaves the original process running and exits the second instance.
- Desktop and Start Menu launchers, Start with Windows, URI/path editing, preview toggling, recognition controls, and clean Exit were confirmed in the real user session.
- Lazy-loading `main.py` reduced packaged tray-only memory from roughly 244-255 MB to about 52 MB because Torch, OpenCV, and MediaPipe are not imported until recognition starts.
- Development CPU measurements were approximately 1% with only the tray running and 3.5-3.7% while recognition was active, with little difference between no-hand and active-gesture scenes.
- The distribution runtime now evaluates the trained LSTM with NumPy instead of importing PyTorch. Parity testing on 25 recorded sequences produced identical classes with a maximum logit difference of `0.00000191`.
- Removing PyTorch and optional MediaPipe dependency trees reduced the packaged folder from about 1.06 GB to approximately 321 MB. Tray-only memory dropped again from about 52 MB to 31-33 MB.
- Packaged user-session testing verified time-based cooldowns, action-category timing, lifecycle notifications, live per-gesture enable/disable changes, and the readable preview-label hold.

### Packaging lessons

- A Windows process launched through Python remains `python.exe`/`pythonw.exe` in Task Manager; producing a process named `GestureAssistant` requires a packaged executable with that name.
- MediaPipe's `drawing_utils` imports Matplotlib. Excluding Matplotlib from the PyInstaller graph caused a packaged-only `ModuleNotFoundError`, even though the application does not call Matplotlib directly.
- Windows Desktop folders may be redirected through OneDrive. Shortcut setup must ask Windows for the known Desktop folder instead of assuming `%USERPROFILE%\Desktop`.
- Elevated automation may use a different Windows user hive. Startup registry and shortcut behavior must be finalized and verified from the actual user's session.
- A small trained model does not imply a small package when its full training framework is bundled. Separating training from inference removed hundreds of megabytes without retraining or changing predictions.
- Application binaries and writable settings need separate lifecycles. The installer places binaries under `%LOCALAPPDATA%\Programs\Gesture Assistant`, while gesture mappings live under `%LOCALAPPDATA%\GestureAssistant`; reinstalling the executable must not erase a user's configuration.
- Installer `0.1.1` replaced legacy Desktop and Start Menu shortcuts after an older shortcut resolved to a development executable. The installer now deletes old links and recreates them with the actual installation directory as both target and working directory.
- A private beta can be shared as one Inno Setup executable through Google Drive. The SHA-256 value is a deterministic fingerprint for detecting a changed or corrupted download; the installer itself remains outside normal Git history.
- After publishing a recovery checkpoint, generated `build`/`dist` output, the superseded installer, caches, and personal runtime configuration were removed from the workspace. Legacy Phase 1 code and weights were moved under `archive/phase1`, while the LSTM baseline image was retained under `docs/assets` for future model comparisons.

### Dependency and configuration lessons

- `requirements.txt` is the canonical dependency list for runtime, training, tray UI, and Windows integration.
- `pywin32` is required for Start Menu shortcut resolution, shortcut creation, and the optional always-on-top integration.
- Persisted configuration values and GUI control values must use the same vocabulary. The earlier editor offered `app` but saved `path`, and did not expose `uri`; reopening those entries produced a blank editor. The GUI now uses the dispatcher's actual type names.
- `time.monotonic()` is the correct clock for cooldown deadlines because it measures elapsed time and is unaffected by wall-clock adjustments.
- Cooldown behavior belongs to both the gesture and its configured action. Motion gestures receive a repositioning interval, while paths, URIs, and scripts receive a longer launch interval even when assigned to a swipe.
- Feature flags in persisted config need a backward-compatible default. Treating a missing `enabled` field as `true` preserves every existing user's behavior.

### Things I still need to be able to explain out loud

- [ ] Why an LSTM can distinguish directional motion that a single-frame MLP cannot.
- [ ] Why wrist motion must remain in the normalized sequence while finger pose is wrist-relative.
- [ ] How class imbalance can make overall accuracy misleading.
- [ ] Why a confidence threshold and a trained `none` class solve related but different false-trigger problems.
- [x] Why frame-based cooldowns vary with FPS and why monotonic time makes action behavior predictable.

### Next steps

1. Refine configurable media actions and the background movie/YouTube workflow.
2. Measure packaged active CPU/memory use and reduce unnecessary runtime work where measurements justify it.
3. Return to model work with balanced data, realistic hard negatives, session-based evaluation, and false-positive tuning.
4. Improve settings persistence, upgrades, and installer behavior.
5. Move duplicated normalization and `GestureLSTM` definitions into shared modules before the next training cycle so collection, training, and inference cannot drift.
