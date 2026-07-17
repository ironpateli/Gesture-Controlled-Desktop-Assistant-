# Gesture-Controlled Desktop Assistant

A Windows desktop utility that recognizes static and motion hand gestures from a webcam and maps them to configurable OS actions. The model is trained as a PyTorch LSTM and exported to a lightweight NumPy runtime for distribution.

## Current architecture

```text
System tray (tray.py)
    -> camera engine (main.py)
    -> MediaPipe Hands: 21 landmarks per frame
    -> 20-frame normalized sequence
    -> NumPy LSTM runtime (gesture_model_runtime.npz)
    -> confidence rejection + monotonic time-based action gate
    -> configurable action dispatcher (actions.py)

Configure Gestures menu
    -> Tkinter editor (config_gui.py)
    -> gestures_config.json
```

The tray icon is the normal entry point. It starts with the camera off, lets you start or stop recognition, toggles the optional camera preview, controls Start with Windows, opens the gesture configuration window, and exits the application cleanly. Recognition continues when the preview is hidden. Simple Windows notifications report when recognition is ready, stopped by the user, or stopped by an error.

Configuration changes are read during recognition, so remapping or enabling/disabling a gesture does not require restarting the app. Disabled gestures may still be recognized by the model, but their actions are blocked. Older configuration files without an `enabled` field remain enabled by default.

A named Windows mutex prevents duplicate tray processes. Starting the application while it is already running exits the second process and leaves the existing tray instance active.

## Recognized gestures

| Gesture | Default/current action type |
|---|---|
| `thumbs_up` | Volume up |
| `thumbs_down` | Volume down |
| `fist` | Mute toggle |
| `peace` | Play/pause |
| `swipe_left` | Rewind 10 seconds (`J`, YouTube default) |
| `swipe_right` | Forward 10 seconds (`L`, YouTube default) |
| `swipe_up` | Fullscreen toggle (`F`, YouTube default) |
| `swipe_down` | Captions toggle (`C`, YouTube default) |

`none` is a trained rejection class and never dispatches an action. Predictions below the `0.8` confidence threshold are also treated as `none`.

The action editor supports built-in controls, executable paths, Windows/application URIs such as `spotify:` or `ms-settings:`, scripts, and keyboard shortcuts. The initial configuration is oriented toward YouTube, but it is not a separate mode: every gesture can be remapped or disabled for another player.

Action timing uses `time.monotonic()` and is independent of webcam FPS. Continuous volume and scrolling actions repeat every `0.20` seconds, ordinary motion gestures use a `0.80` second repositioning interval, and app/URI/script launches use `2.00` seconds. One-shot static actions also require the gesture to be released for `0.35` seconds before they can fire again. A motion gesture remapped to an app or script automatically receives the longer launch interval.

## Setup and run

This project targets Windows. The currently verified environment uses Python 3.12.10, MediaPipe 0.10.14, and protobuf 4.25.9. A virtual environment is recommended.

End users do not need Python or these development dependencies; they are bundled in the packaged application.

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
4. The resulting `gesture_model.pth` checkpoint remains the training artifact.
5. Run `python export_runtime_model.py` to create `gesture_model_runtime.npz` and verify inference parity.
6. `main.py` loads the exported NumPy runtime model without importing PyTorch.

Each sample contains 20 frames x 21 landmarks x 3 coordinates (1,260 features). Pose landmarks are wrist-relative and scale-normalized; left-hand poses are mirrored to match right-hand orientation. Wrist displacement across the sequence is retained so the LSTM can learn motion.

The retained training baseline is shown in [docs/assets/lstm-training-baseline.png](docs/assets/lstm-training-baseline.png). It records the earlier 96.04% sequence test accuracy and confusion matrix for comparison during the next model-improvement cycle.

## Main files

- `tray.py`: persistent tray process and camera start/stop control.
- `main.py`: live inference, confidence filtering, cooldowns, and dispatch.
- `action_timing.py`: time-based action categories, cooldown deadlines, and release-to-rearm state.
- `actions.py`: config loading and OS action runners.
- `config_gui.py`: gesture-to-action editor.
- `app_discovery.py`: Start Menu application discovery and cache.
- `collect_data.py`: sequence data recorder.
- `train_classifier.py`: LSTM training and evaluation.
- `export_runtime_model.py`: exports and verifies the lightweight runtime model.
- `runtime_model.py`: NumPy implementation of the trained one-layer LSTM.
- `archive/phase1/gesture_detector.py` and `archive/phase1/gesture_model.pkl`: retained Phase 1/early Phase 2 artifacts; they are not used by the active runtime.

Generated build directories, the local venv, app-discovery cache, personal gesture mappings, and uploaded user scripts are intentionally excluded from Git. `build_app.ps1` and `build_installer.ps1` recreate distributable outputs when needed.

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

The rebuilt package has also been verified for FPS-independent action timing, action-aware cooldowns, ready/stop tray notifications, per-gesture enable/disable controls, and a `1.5` second preview hold that keeps the latest confident gesture label readable.

The reduced packaged tray uses about 31-33 MB while recognition is stopped. OpenCV and MediaPipe are loaded lazily when the gesture engine starts. The NumPy runtime produces matching classes to the PyTorch model; verification on 25 recorded sequences measured a maximum logit difference of `0.00000191`. Development testing measured about 1% CPU tray-only and 3.5-3.7% CPU with recognition active.

The packaged folder is approximately 321 MB, down from about 1.06 GB after removing PyTorch, JAX, ONNX Runtime, SciPy, sounddevice, and unused MediaPipe assets from the distributed runtime.

Hardware interaction and Windows-account integration should be verified from the user's own terminal/session. Automated checks cover syntax, build output, bundled assets, and isolated application logic; webcam behavior, tray interaction, shortcuts, startup registry state, and Task Manager measurements require a user-session smoke test.

## System requirements

- Windows 10 or 11, 64-bit; Windows 11 is currently verified.
- Modern x64 dual-core processor; a recent quad-core processor is recommended.
- 4 GB RAM minimum; 8 GB recommended.
- 750 MB free storage minimum; 1 GB recommended for installation and updates.
- Windows-compatible webcam; 720p at 30 FPS is recommended.
- No dedicated GPU and no internet connection are required during normal use.

See [SYSTEM_REQUIREMENTS.md](SYSTEM_REQUIREMENTS.md) for details.

## Installer and download

`build_installer.ps1` compiles the packaged folder into a per-user Inno Setup installer. The installer creates Start Menu and optional Desktop shortcuts and can enable Start with Windows.

The tested private installer is `GestureAssistant-Setup-0.1.1.exe` (approximately 82 MiB). It installs application binaries under `%LOCALAPPDATA%\Programs\Gesture Assistant`, while writable user configuration remains under `%LOCALAPPDATA%\GestureAssistant`. Reinstalling or upgrading therefore preserves custom mappings. A fresh Windows user receives the YouTube-oriented defaults when configuration is first opened or recognition starts.

For private testing, the setup executable can be uploaded to Google Drive or another file-sharing service. Share only the installer, not the `dist` directory or project workspace. A SHA-256 checksum gives testers a fingerprint for confirming that their downloaded file exactly matches the published installer; generate it with `Get-FileHash`.

For a public download link, upload the installer to a versioned GitHub Release rather than committing it to Git history. See [RELEASE_GUIDE.md](RELEASE_GUIDE.md) for the clean-machine checklist, installer command, checksum guidance, and release-link formats.

## Roadmap

1. Refine the laid-back media workflow and expand user-configurable media actions.
2. Measure packaged active CPU/memory use and tune camera/inference work where measurements justify it.
3. Improve model quality with balanced data, hard negatives, session-based evaluation, and false-positive tuning.
4. Improve settings, upgrades, and code signing.
5. Validate and publish the installer from a clean Windows environment.

## Current limitations

- Windows-specific action launching, app discovery, tray shortcuts, and always-on-top behavior.
- One hand and camera index `0` only.
- The exported runtime model is required; there is no rule-based fallback.
- Mirrored swipe directions remain the model's most confusion-prone gesture group.
- The dataset is class-imbalanced, especially because `none` has substantially more samples than several static gestures.
- The current PyInstaller output is a development build, not yet a signed installer.
- Windows 10 and older x64 processors still need clean-machine compatibility testing.
