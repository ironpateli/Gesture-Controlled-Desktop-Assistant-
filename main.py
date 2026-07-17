"""
main.py

Camera engine: webcam -> MediaPipe landmarks -> LSTM inference through
the lightweight NumPy runtime exported from the PyTorch training
checkpoint -> custom debounce -> OS action.

This module no longer runs on its own by default — tray.py is the
entry point. The tray icon starts/stops run_gesture_engine() below on
demand, so the camera only turns on when you actually want it to.

Requires gesture_model_runtime.npz to be present. There is no rule-based
fallback. Run export_runtime_model.py after retraining the PyTorch model.

To run the camera loop standalone for testing (no tray icon, no
start/stop control — just Ctrl+C or 'q' to quit):
    python main.py
"""

import time
import os
import threading
import collections
import math
import warnings
import cv2
import numpy as np
import mediapipe as mp

from actions import dispatch, get_action_entry, setup_always_on_top
from action_timing import GestureActionGate, MOTION_GESTURES
from app_paths import resource_path
from runtime_model import NumpyGestureLSTM

warnings.filterwarnings("ignore", category=UserWarning, module="google.protobuf")
mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
mp_styles = mp.solutions.drawing_styles

MODEL_PATH = resource_path("gesture_model_runtime.npz")
SEQ_LEN = 20
INPUT_SIZE = 63
CONFIDENCE_THRESHOLD = 0.8  # Predictions below this are auto-classified as 'none'
GESTURE_LABEL_HOLD_SECONDS = 1.5
WINDOW_TITLE = "Gesture Assistant"


def calculate_scale_factor(landmarks_0):
    """Calculate hand scale factor based on max landmark distance from wrist in frame 0."""
    wrist_0 = landmarks_0[0]
    max_dist = 0.0
    for lm in landmarks_0[1:]:
        dist = math.hypot(math.hypot(lm.x - wrist_0.x, lm.y - wrist_0.y), lm.z - wrist_0.z)
        if dist > max_dist:
            max_dist = dist
    return max_dist if max_dist > 0.0 else 1.0


def normalize_sequence_frame(landmarks, wrist_0, scale_factor, is_left_hand=False):
    """Normalize landmarks for a single frame inside a sequence:
    - Landmark 0: stores displacement of wrist relative to start of sequence (never mirrored).
    - Landmarks 1-20: stores finger shapes relative to current wrist (mirrored if left hand).
    All values are scaled by scale_factor."""
    wrist_t = landmarks[0]
    row = []

    # Landmark 0: Global motion
    x_motion = (wrist_t.x - wrist_0.x) / scale_factor
    y_motion = (wrist_t.y - wrist_0.y) / scale_factor
    z_motion = (wrist_t.z - wrist_0.z) / scale_factor
    row += [x_motion, y_motion, z_motion]

    # Landmarks 1-20: Relative pose
    for lm in landmarks[1:]:
        x_pose = (lm.x - wrist_t.x) / scale_factor
        if is_left_hand:
            x_pose = -x_pose  # Mirror Left hand to match Right hand
        y_pose = (lm.y - wrist_t.y) / scale_factor
        z_pose = (lm.z - wrist_t.z) / scale_factor
        row += [x_pose, y_pose, z_pose]

    return row


def load_model():
    """Load the exported NumPy LSTM runtime model."""
    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(
            f"[main] No runtime model found at {MODEL_PATH}. Run "
            f"export_runtime_model.py after training."
        )

    model = NumpyGestureLSTM(MODEL_PATH)
    print(f"[main] Loaded lightweight LSTM runtime from {MODEL_PATH}")
    return model


def run_gesture_engine(
    stop_event: threading.Event,
    preview_event: threading.Event | None = None,
    ready_callback=None,
):
    """Run the webcam -> gesture -> action loop until stop_event is set
    (or the 'q' key is pressed with the camera window focused, when run
    standalone). Called by tray.py's Start/Stop toggle — each call loads
    a fresh copy of the model and opens the webcam, and cleans both up
    on exit."""
    model = load_model()

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        raise RuntimeError("Could not open webcam. Check camera index / permissions.")

    # raw_buffer stores: (landmarks, is_left_hand)
    raw_buffer = collections.deque(maxlen=SEQ_LEN)
    action_gate = GestureActionGate()
    prev_time = time.monotonic()

    mode = "LSTM model (NumPy runtime)"
    preview_visible = False
    displayed_gesture = "none"
    displayed_gesture_until = 0.0

    with mp_hands.Hands(
        model_complexity=1,
        max_num_hands=1,
        min_detection_confidence=0.7,
        min_tracking_confidence=0.6,
    ) as hands:
        if ready_callback is not None:
            ready_callback()

        always_on_top_set = False

        while True:
            if stop_event.is_set():
                print("[main] Gesture engine stop requested.")
                break

            ok, frame = cap.read()
            if not ok:
                break

            frame = cv2.flip(frame, 1)
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = hands.process(rgb)

            gesture_name = "none"

            if results.multi_hand_landmarks and results.multi_handedness:
                hand_landmarks = results.multi_hand_landmarks[0]
                handedness = results.multi_handedness[0].classification[0].label
                is_left_hand = (handedness == "Left")

                show_preview = preview_event is None or preview_event.is_set()
                if show_preview:
                    mp_drawing.draw_landmarks(
                        frame,
                        hand_landmarks,
                        mp_hands.HAND_CONNECTIONS,
                        mp_styles.get_default_hand_landmarks_style(),
                        mp_styles.get_default_hand_connections_style(),
                    )

                # Append current frame to sliding window buffer
                raw_buffer.append((hand_landmarks.landmark, is_left_hand))

                if len(raw_buffer) == SEQ_LEN:
                    # Reconstruct sliding sequence normalized to raw_buffer[0]
                    landmarks_0, is_left_0 = raw_buffer[0]
                    wrist_0 = landmarks_0[0]
                    scale_factor = calculate_scale_factor(landmarks_0)

                    normalized_seq = []
                    for landmarks_t, is_left_t in raw_buffer:
                        flat_frame = normalize_sequence_frame(
                            landmarks_t, wrist_0, scale_factor, is_left_hand=is_left_t
                        )
                        normalized_seq.append(flat_frame)

                    gesture_name, confidence = model.predict(normalized_seq)
                    if confidence < CONFIDENCE_THRESHOLD:
                        gesture_name = "none"  # below threshold, reject

                    now = time.monotonic()
                    if gesture_name != "none":
                        displayed_gesture = gesture_name
                        displayed_gesture_until = now + GESTURE_LABEL_HOLD_SECONDS

                    if gesture_name == "none":
                        action_gate.observe("none", now)
                    else:
                        action_entry = get_action_entry(gesture_name)
                        if action_gate.should_fire(gesture_name, action_entry, now):
                            dispatch(gesture_name, action_entry)
                            if gesture_name in MOTION_GESTURES:
                                raw_buffer.clear()
            else:
                raw_buffer.clear()
                action_gate.hand_left_frame()

            # FPS + optional debug preview
            now = time.monotonic()
            fps = 1.0 / max(now - prev_time, 1e-6)
            prev_time = now

            show_preview = preview_event is None or preview_event.is_set()
            if show_preview:
                preview_gesture = (
                    displayed_gesture if now < displayed_gesture_until else "none"
                )
                cv2.putText(frame, f"Gesture: {preview_gesture}", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
                cv2.putText(frame, f"FPS: {fps:.1f}", (10, 60),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
                cv2.putText(frame, f"Mode: {mode}", (10, 90),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 255), 1)
                cooldown_remaining = action_gate.cooldown_remaining(gesture_name, now)
                if action_gate.waiting_for_release(gesture_name):
                    cv2.putText(frame, "RELEASE TO REARM", (10, 120),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 255), 1)
                elif cooldown_remaining > 0:
                    cv2.putText(frame, f"COOLDOWN ({cooldown_remaining:.1f}s)", (10, 120),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 255), 1)

                cv2.imshow(WINDOW_TITLE, frame)
                preview_visible = True

                if not always_on_top_set:
                    setup_always_on_top(WINDOW_TITLE)
                    always_on_top_set = True

                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
            elif preview_visible:
                cv2.destroyWindow(WINDOW_TITLE)
                cv2.waitKey(1)
                preview_visible = False
                always_on_top_set = False

    cap.release()
    cv2.destroyAllWindows()


def main():
    """Standalone runner for testing main.py directly, without the tray
    icon or its start/stop control. Press 'q' (camera window focused) or
    Ctrl+C to quit."""
    stop_event = threading.Event()
    try:
        run_gesture_engine(stop_event)
    except KeyboardInterrupt:
        stop_event.set()


if __name__ == "__main__":
    main()
