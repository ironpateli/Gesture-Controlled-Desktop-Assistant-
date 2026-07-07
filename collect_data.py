"""
collect_data.py

Phase 2, step 1: record YOUR OWN labeled landmark sequences.

How it works:
- Live webcam feed, MediaPipe extracts 21 landmarks per frame.
- Press a number/letter key to trigger a 20-frame sequence recording for that gesture.
- Hold your gesture still while the progress bar fills (for static gestures).
- Perform the motion naturally during the progress bar (for dynamic swipe gestures).
- Press '0' to record "none" (resting hand / rejection class) — IMPORTANT.
- Press 'q' to quit.

Each row in gesture_data.csv = one 20-frame sequence = [label, 1260 normalized floats]
(20 frames × 21 landmarks × 3 coordinates = 1260 values)

Keys:
  0 = none          1 = thumbs_up     2 = thumbs_down
  3 = fist          4 = peace
  a = swipe_left    b = swipe_right
  c = swipe_up      d = swipe_down

Run:
    python collect_data.py
"""

import csv
import os
import time

import cv2
import mediapipe as mp

mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
mp_styles = mp.solutions.drawing_styles

CSV_PATH = "gesture_data.csv"

# Map keyboard keys to gesture labels.
# Static gestures: hold the pose during the 20-frame recording window.
# Dynamic gestures: perform the full motion during the 20-frame window.
KEY_TO_LABEL = {
    ord("0"): "none",
    ord("1"): "thumbs_up",
    ord("2"): "thumbs_down",
    ord("3"): "fist",
    ord("4"): "peace",
    ord("a"): "swipe_left",
    ord("b"): "swipe_right",
    ord("c"): "swipe_up",
    ord("d"): "swipe_down",
}


import math

def ensure_csv_header():
    """Create the CSV with a header row if it doesn't already exist.
    If it exists, we append to it instead — preserves data across sessions.
    Now supports sequences of 20 frames."""
    if not os.path.exists(CSV_PATH):
        header = ["label"]
        for f in range(20):
            for i in range(21):
                header += [f"f{f}_x{i}", f"f{f}_y{i}", f"f{f}_z{i}"]
        with open(CSV_PATH, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(header)


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


def main():
    ensure_csv_header()

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        raise RuntimeError("Could not open webcam.")

    current_label = None
    recording_sequence = False
    temp_sequence = []
    
    # Counts represents the number of recorded sequences
    counts = {label: 0 for label in KEY_TO_LABEL.values()}

    # Read existing CSV to load counts of already recorded sequences
    if os.path.exists(CSV_PATH):
        with open(CSV_PATH, "r") as f:
            reader = csv.reader(f)
            next(reader, None)  # skip header
            for row in reader:
                if row and row[0] in counts:
                    counts[row[0]] += 1

    # Keep track of when we last saved to display a temporary "SUCCESS!" visual feedback
    feedback_end_time = 0

    with mp_hands.Hands(
        model_complexity=1,
        max_num_hands=1,
        min_detection_confidence=0.7,
        min_tracking_confidence=0.6,
    ) as hands, open(CSV_PATH, "a", newline="") as f:
        writer = csv.writer(f)

        while True:
            ok, frame = cap.read()
            if not ok:
                break

            frame = cv2.flip(frame, 1)
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = hands.process(rgb)

            h, w, _ = frame.shape
            hand_detected = False

            if results.multi_hand_landmarks and results.multi_handedness:
                hand_detected = True
                hand_landmarks = results.multi_hand_landmarks[0]
                handedness = results.multi_handedness[0].classification[0].label
                
                # Draw standard hand skeleton
                mp_drawing.draw_landmarks(
                    frame, hand_landmarks, mp_hands.HAND_CONNECTIONS,
                    mp_styles.get_default_hand_landmarks_style(),
                    mp_styles.get_default_hand_connections_style(),
                )

                if recording_sequence and current_label is not None:
                    # Append raw landmarks and handedness classification
                    temp_sequence.append((hand_landmarks.landmark, handedness))
                    
                    # If we have collected 20 frames, process and save the sequence
                    if len(temp_sequence) == 20:
                        # Frame 0 landmarks and handedness
                        landmarks_0 = temp_sequence[0][0]
                        hand_type = temp_sequence[0][1] # "Left" or "Right"
                        wrist_0 = landmarks_0[0]
                        
                        scale_factor = calculate_scale_factor(landmarks_0)
                        
                        # Normalize each frame
                        flat_sequence = []
                        for lm_list, h_type in temp_sequence:
                            flat_frame = normalize_sequence_frame(
                                lm_list, wrist_0, scale_factor, is_left_hand=(h_type == "Left")
                            )
                            flat_sequence.extend(flat_frame)
                            
                        # Write labeled sequence
                        writer.writerow([current_label] + flat_sequence)
                        f.flush() # Ensure it's written immediately
                        
                        counts[current_label] += 1
                        recording_sequence = False
                        temp_sequence = []
                        feedback_end_time = time.time() + 0.8  # show feedback for 0.8s

            # --- Visual Feedback on Successful Record ---
            if time.time() < feedback_end_time:
                # Draw a green border around frame to signal success
                cv2.rectangle(frame, (0, 0), (w, h), (0, 255, 0), 10)
                cv2.putText(frame, "SEQUENCE SAVED!", (w // 2 - 120, h // 2),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 3)

            # --- Overlay UI ---
            if recording_sequence:
                status = "RECORDING"
                color = (0, 0, 255)  # Red
                # Progress bar
                prog = len(temp_sequence)
                cv2.putText(frame, f"[{status}] Label: {current_label} ({prog}/20)", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.75, color, 2)
                # Draw progress bar rect
                cv2.rectangle(frame, (10, 45), (10 + (prog * 15), 55), (0, 0, 255), cv2.FILLED)
            else:
                status = "READY"
                color = (0, 255, 255)  # Yellow
                cv2.putText(frame, f"[{status}] Press key to record sequence", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.75, color, 2)

            y = 80
            for key_code, label in KEY_TO_LABEL.items():
                key_char = chr(key_code)
                cv2.putText(frame, f"[{key_char}] {label}: {counts[label]} sequences",
                            (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)
                y += 22

            cv2.putText(frame, "[q] quit", (10, y + 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 200), 1)

            cv2.imshow("Sequence Data Collection", frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
            elif key in KEY_TO_LABEL and not recording_sequence and hand_detected:
                # Trigger a sequence collection
                current_label = KEY_TO_LABEL[key]
                recording_sequence = True
                temp_sequence = []

    cap.release()
    cv2.destroyAllWindows()
    print(f"\nSaved to {CSV_PATH}. Final sequence counts: {counts}")


if __name__ == "__main__":
    main()
