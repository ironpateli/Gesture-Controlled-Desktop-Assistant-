"""
main.py

Phase 2 entry point: webcam -> MediaPipe landmarks -> trained ML classifier
(gesture_model.pkl from train_classifier.py) -> debounce -> OS action.

Falls back to rule-based classify_gesture() if gesture_model.pkl is not
found, so Phase 1 still works without retraining.

Run:
    python main.py

Press 'q' to quit.
"""

import time
import os

import cv2
import joblib
import mediapipe as mp
import numpy as np

from gesture_detector import classify_gesture, Debouncer
from actions import dispatch

mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
mp_styles = mp.solutions.drawing_styles

MODEL_PATH = "gesture_model.pkl"


def load_model():
    """Load trained model if available, otherwise return None
    (main loop falls back to rule-based classifier)."""
    if os.path.exists(MODEL_PATH):
        model = joblib.load(MODEL_PATH)
        print(f"[main] Loaded trained model from {MODEL_PATH}")
        return model
    print(f"[main] No model found at {MODEL_PATH} — using rule-based classifier.")
    return None


def landmarks_to_features(landmarks):
    """Flatten 21 MediaPipe landmark objects into a 1x63 numpy array,
    matching the exact format collect_data.py used to build the dataset."""
    row = []
    for lm in landmarks:
        row += [lm.x, lm.y, lm.z]
    return np.array(row).reshape(1, -1)


def predict_gesture(model, landmarks, handedness):
    """Use the trained model if available, else fall back to rules."""
    if model is not None:
        features = landmarks_to_features(landmarks)
        return model.predict(features)[0]   # returns a string label e.g. "thumbs_up"
    # Phase 1 fallback
    result = classify_gesture(landmarks, handedness)
    return result.name


def main():
    model = load_model()

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        raise RuntimeError("Could not open webcam. Check camera index / permissions.")

    debouncer = Debouncer(stable_frames=8, cooldown_frames=15)
    prev_time = time.time()

    mode = "ML model" if model is not None else "Rule-based (Phase 1)"

    with mp_hands.Hands(
        model_complexity=1,
        max_num_hands=1,
        min_detection_confidence=0.7,
        min_tracking_confidence=0.6,
    ) as hands:
        while True:
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

                mp_drawing.draw_landmarks(
                    frame,
                    hand_landmarks,
                    mp_hands.HAND_CONNECTIONS,
                    mp_styles.get_default_hand_landmarks_style(),
                    mp_styles.get_default_hand_connections_style(),
                )

                gesture_name = predict_gesture(
                    model, hand_landmarks.landmark, handedness
                )

                fired = debouncer.update(gesture_name)
                if fired:
                    dispatch(fired)
            else:
                debouncer.update("none")

            # FPS + mode overlay
            now = time.time()
            fps = 1.0 / max(now - prev_time, 1e-6)
            prev_time = now

            cv2.putText(frame, f"Gesture: {gesture_name}", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
            cv2.putText(frame, f"FPS: {fps:.1f}", (10, 60),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
            cv2.putText(frame, f"Mode: {mode}", (10, 90),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 255), 1)

            cv2.imshow("Gesture Assistant (Phase 2 - Trained Classifier)", frame)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()