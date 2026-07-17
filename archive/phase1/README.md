# Phase 1 Archive

These files document the earlier rule-based and single-frame classifier stages:

- `gesture_detector.py`: rule-based landmark gesture detection.
- `gesture_model.pkl`: legacy single-frame MLP classifier.

They are not imported by the active tray application or packaged runtime. The current model pipeline uses `gesture_model.pth` for training and `gesture_model_runtime.npz` for NumPy inference.
