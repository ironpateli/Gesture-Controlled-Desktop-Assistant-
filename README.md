# Gesture-Controlled Desktop Assistant

A Windows desktop utility that recognizes static and motion hand gestures from a webcam and maps them to configurable OS actions. The active system uses MediaPipe hand landmarks and a custom PyTorch LSTM trained on 20-frame sequences.

## Current architecture

```text
System tray (tray.py)
    -> camera engine (main.py)
    -> MediaPipe Hands: 21 landmarks per frame
    -> 20-frame normalized sequence
    -> PyTorch LSTM (gesture_model.pth)
    -> confidence rejection + gesture-specific cooldown
    -> configurable action dispatcher (actions.py)

Configure Gestures menu
    -> Tkinter editor (config_gui.py)
    -> gestures_config.json
```

The tray icon is the normal entry point. It starts with the camera off, lets you start or stop recognition, toggles the optional camera preview, controls Start with Windows, opens the gesture configuration window, and exits the application cleanly. Recognition continues when the preview is hidden. Configuration changes are read when an action is dispatched, so they do not require restarting the app.

A named Windows mutex prevents duplicate tray processes. Starting the application while it is already running exits the second process and leaves the existing tray instance active.

## Recognized gestures

| Gesture | Default/current action type |
|---|---|
| `thumbs_up` | Volume up |
| `thumbs_down` | Volume down |
| `fist` | Mute toggle |
| `peace` | Play/pause |
| `swipe_left` | Configurable action |
| `swipe_right` | Configurable action |
| `swipe_up` | Configurable action |
| `swipe_down` | Configurable action |

`none` is a trained rejection class and never dispatches an action. Predictions below the `0.8` confidence threshold are also treated as `none`.

The action editor supports built-in controls, executable paths, Windows/application URIs such as `spotify:` or `ms-settings:`, scripts, and keyboard shortcuts.

## Setup and run

This project targets Windows. The currently verified environment uses Python 3.12.10, MediaPipe 0.10.14, and protobuf 4.25.9. A virtual environment is recommended.

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python tray.py
```

For automatic startup shortcuts, run:

```powershell
python setup_shortcuts.py
```

This creates Desktop and Start Menu launchers and enables Start with Windows for the current user. The same startup setting can be changed from the tray menu without administrator access.

You can also run `python main.py` to test the camera engine directly or `python config_gui.py` to test the configuration window.

## Training workflow

1. Run `python collect_data.py` and record labeled 20-frame sequences.
2. Use keys `0-4` for `none`, thumbs up/down, fist, and peace; use `a-d` for the four swipe directions.
3. Run `python train_classifier.py` to train and evaluate the LSTM.
4. The resulting `gesture_model.pth` checkpoint is loaded by `main.py`.

Each sample contains 20 frames x 21 landmarks x 3 coordinates (1,260 features). Pose landmarks are wrist-relative and scale-normalized; left-hand poses are mirrored to match right-hand orientation. Wrist displacement across the sequence is retained so the LSTM can learn motion.

## Main files

- `tray.py`: persistent tray process and camera start/stop control.
- `main.py`: live inference, confidence filtering, cooldowns, and dispatch.
- `actions.py`: config loading and OS action runners.
- `config_gui.py`: gesture-to-action editor.
- `app_discovery.py`: Start Menu application discovery and cache.
- `collect_data.py`: sequence data recorder.
- `train_classifier.py`: LSTM training and evaluation.
- `gesture_detector.py` and `gesture_model.pkl`: retained Phase 1/early Phase 2 artifacts; they are not used by the active runtime.

## Build the Windows application

Run the build from PowerShell:

```powershell
.\build_app.ps1
```

The one-folder application is written to `dist\GestureAssistant`. Launch `GestureAssistant.exe` from that folder. Windows Task Manager displays the process as `GestureAssistant.exe`, while development runs continue to appear as `python.exe` or `pythonw.exe`.

The packaged application stores writable configuration, uploaded scripts, generated tray icons, and the app-discovery cache under `%LOCALAPPDATA%\GestureAssistant`. The model and bundled assets remain inside the application folder.

### Verified packaged behavior

The current Windows build has been tested successfully for:

- Launching from Desktop and Start Menu shortcuts.
- Displaying as `GestureAssistant` in Task Manager.
- Rejecting duplicate launches while keeping the original tray process active.
- Starting with Windows through the current user's startup setting.
- Loading MediaPipe and the bundled LSTM model.
- Starting and stopping recognition, hiding and restoring the preview, editing gesture actions, and exiting cleanly.

The packaged tray uses about 52 MB while recognition is stopped. Heavy modules such as PyTorch, OpenCV, and MediaPipe are loaded lazily when the gesture engine starts. The development environment previously measured about 1% CPU tray-only and 3.5-3.7% CPU with recognition active.

Hardware interaction and Windows-account integration should be verified from the user's own terminal/session. Automated checks cover syntax, build output, bundled assets, and isolated application logic; webcam behavior, tray interaction, shortcuts, startup registry state, and Task Manager measurements require a user-session smoke test.

## Roadmap

1. Replace frame-count cooldowns with predictable time-based action control.
2. Refine the laid-back media workflow and expand user-configurable media actions.
3. Measure packaged active CPU/memory use and reduce unnecessary runtime and bundle weight.
4. Improve settings, error reporting, upgrades, and installer behavior.
5. Return to model improvement with balanced data, hard negatives, session-based evaluation, and false-positive tuning.
6. Produce a signed installer after runtime and model validation.

## Current limitations

- Windows-specific action launching, app discovery, tray shortcuts, and always-on-top behavior.
- One hand and camera index `0` only.
- The model checkpoint is required; there is no rule-based fallback.
- Cooldowns are frame-based, so their real duration varies with webcam FPS.
- The dataset is class-imbalanced, especially because `none` has substantially more samples than several static gestures.
- The current PyInstaller output is a development build, not yet a signed installer.
- The current one-folder build is large because it bundles the Python runtime, PyTorch, OpenCV, MediaPipe, Matplotlib, and their native dependencies.
