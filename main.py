"""
main.py

Entry point: webcam -> MediaPipe landmarks -> trained PyTorch LSTM classifier
(gesture_model.pth from train_classifier.py) -> custom debounce -> OS action.

Requires gesture_model.pth to be present — there is no rule-based fallback.
Run this from the same directory as your trained gesture_model.pth.

Run:
    python main.py

Press 'q' to quit.
"""

import time
import os
import collections
import math
import warnings
import cv2
import numpy as np
import torch
import torch.nn as nn
import mediapipe as mp

from actions import dispatch, setup_always_on_top

warnings.filterwarnings("ignore", category=UserWarning, module="google.protobuf")
mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
mp_styles = mp.solutions.drawing_styles

MODEL_PATH = "gesture_model.pth"
SEQ_LEN = 20
INPUT_SIZE = 63
CONFIDENCE_THRESHOLD = 0.8  # Predictions below this are auto-classified as 'none'


class GestureLSTM(nn.Module):
    def __init__(self, input_size=63, hidden_size=64, num_classes=9, num_layers=1):
        super().__init__()
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True)
        self.fc = nn.Linear(hidden_size, num_classes)

    def forward(self, x):
        # x shape: (batch_size, seq_len, input_size)
        out, _ = self.lstm(x)
        # Pass the output of the last time step through the linear layer
        out = self.fc(out[:, -1, :])
        return out


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
    """Load the trained PyTorch LSTM model. Raises if it can't be found or
    loaded — there is no rule-based fallback, so a valid model is required."""
    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(
            f"[main] No model found at {MODEL_PATH}. Place your trained "
            f"gesture_model.pth next to main.py before running."
        )

    checkpoint = torch.load(MODEL_PATH)
    label_to_id = checkpoint['label_to_id']
    id_to_label = checkpoint['id_to_label']
    num_classes = len(label_to_id)

    model = GestureLSTM(
        input_size=INPUT_SIZE,
        hidden_size=checkpoint.get('hidden_size', 64),
        num_classes=num_classes,
        num_layers=checkpoint.get('num_layers', 1)
    )
    model.load_state_dict(checkpoint['model_state_dict'])
    model.eval()
    print(f"[main] Loaded trained PyTorch LSTM model from {MODEL_PATH}")
    return model, id_to_label


def main():
    model, id_to_label = load_model()

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        raise RuntimeError("Could not open webcam. Check camera index / permissions.")

    # raw_buffer stores: (landmarks, is_left_hand)
    raw_buffer = collections.deque(maxlen=SEQ_LEN)
    cooldown = 0
    prev_time = time.time()

    mode = "PyTorch LSTM model"

    with mp_hands.Hands(
        model_complexity=1,
        max_num_hands=1,
        min_detection_confidence=0.7,
        min_tracking_confidence=0.6,
    ) as hands:
        
        always_on_top_set = False

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
                is_left_hand = (handedness == "Left")

                mp_drawing.draw_landmarks(
                    frame,
                    hand_landmarks,
                    mp_hands.HAND_CONNECTIONS,
                    mp_styles.get_default_hand_landmarks_style(),
                    mp_styles.get_default_hand_connections_style(),
                )

                # Append current frame to sliding window buffer
                raw_buffer.append((hand_landmarks.landmark, is_left_hand))

                if cooldown > 0:
                    cooldown -= 1
                    gesture_name = "none"
                elif len(raw_buffer) == SEQ_LEN:
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

                    # Predict using LSTM
                    tensor_in = torch.tensor([normalized_seq], dtype=torch.float32)
                    with torch.no_grad():
                        outputs = model(tensor_in)
                        probs = torch.softmax(outputs, dim=1)
                        confidence, pred_id = torch.max(probs, dim=1)
                        if confidence.item() >= CONFIDENCE_THRESHOLD:
                            gesture_name = id_to_label[pred_id.item()]
                        else:
                            gesture_name = "none"  # below threshold, reject

                    # Dispatch Action with Custom Cooldowns
                    if gesture_name != "none":
                        # Continuous static gestures (Thumbs Up / Down for Volume)
                        if gesture_name in ("thumbs_up", "thumbs_down"):
                            dispatch(gesture_name)
                            cooldown = 4  # Short cooldown to allow continuous smooth trigger

                        # Discrete static gestures (Mute, Play/Pause)
                        elif gesture_name in ("fist", "peace"):
                            dispatch(gesture_name)
                            cooldown = 30  # Medium cooldown (~0.5s)
                            raw_buffer.clear()  # Clear buffer to prevent double-firing

                        # Dynamic motion gestures (Swiping / Scrolling)
                        elif gesture_name in ("swipe_left", "swipe_right", "swipe_up", "swipe_down"):
                            dispatch(gesture_name)
                            cooldown = 30  # 0.6s repositioning cooldown
                            raw_buffer.clear()  # Discard old swipe frames to prevent double-firing
            else:
                raw_buffer.clear()
                if cooldown > 0:
                    cooldown -= 1

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
            if cooldown > 0:
                cv2.putText(frame, f"COOLDOWN ({cooldown})", (10, 120),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 255), 1)

            cv2.imshow("Gesture Assistant (Phase 2 - PyTorch LSTM)", frame)

            if not always_on_top_set:
                setup_always_on_top("Gesture Assistant (Phase 2 - PyTorch LSTM)")
                always_on_top_set = True

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()