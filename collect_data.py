"""
collect_data.py

Phase 2, step 1: record YOUR OWN labeled landmark data.

How it works:
- Live webcam feed, MediaPipe extracts 21 landmarks per frame (same as
  Phase 1 — we're not replacing landmark extraction, only replacing the
  classification step with something trained on data instead of rules).
- Press a number key to set the CURRENT LABEL (what gesture you're about
  to show). While a label is active, every frame's landmarks are saved
  to gesture_data.csv along with that label.
- Press '0' to record "none" (no gesture / resting hand) — IMPORTANT,
  without this the model never learns to say "nothing is happening."
- Press SPACE to pause/resume recording without losing your current label.
- Press 'q' to quit.

Each row in gesture_data.csv = one frame = [label, x0,y0,z0, x1,y1,z1, ... x20,y20,z20]
63 numeric feature columns (21 landmarks × 3 coordinates) + 1 label column.

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

# Map keyboard keys to gesture labels. '0' is the crucial "none"/rejection class.
KEY_TO_LABEL = {
    ord("0"): "none",
    ord("1"): "thumbs_up",
    ord("2"): "thumbs_down",
    ord("3"): "peace",
    ord("4"): "point",
    ord("5"): "rock",
}


def ensure_csv_header():
    """Create the CSV with a header row if it doesn't already exist.
    If it exists, we append to it instead — preserves data across sessions."""
    if not os.path.exists(CSV_PATH):
        header = ["label"]
        for i in range(21):
            header += [f"x{i}", f"y{i}", f"z{i}"]
        with open(CSV_PATH, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(header)


def landmarks_to_row(label, landmarks):
    """Flatten MediaPipe's 21 landmark objects into one flat list of
    63 numbers, prefixed with the label."""
    row = [label]
    for lm in landmarks:
        row += [lm.x, lm.y, lm.z]
    return row


def main():
    ensure_csv_header()

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        raise RuntimeError("Could not open webcam.")

    current_label = None
    recording = False
    counts = {label: 0 for label in KEY_TO_LABEL.values()}
    
    # Save interval in seconds to limit data rate (0.066s = ~15 FPS, halving the standard 30 FPS)
    SAVE_INTERVAL = 0.066
    last_save_time = 0

    # If the CSV already has data from a previous session, show accurate
    # starting counts instead of resetting to 0 (helps you see total progress).
    if os.path.exists(CSV_PATH):
        with open(CSV_PATH, "r") as f:
            reader = csv.reader(f)
            next(reader, None)  # skip header
            for row in reader:
                if row and row[0] in counts:
                    counts[row[0]] += 1

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

            if results.multi_hand_landmarks:
                hand_landmarks = results.multi_hand_landmarks[0]
                mp_drawing.draw_landmarks(
                    frame, hand_landmarks, mp_hands.HAND_CONNECTIONS,
                    mp_styles.get_default_hand_landmarks_style(),
                    mp_styles.get_default_hand_connections_style(),
                )

                if recording and current_label is not None:
                    now = time.time()
                    if now - last_save_time >= SAVE_INTERVAL:
                        row = landmarks_to_row(current_label, hand_landmarks.landmark)
                        writer.writerow(row)
                        counts[current_label] += 1
                        last_save_time = now

            # --- overlay UI ---
            status = "RECORDING" if recording else "PAUSED"
            color = (0, 0, 255) if recording else (0, 255, 255)
            cv2.putText(frame, f"[{status}] label: {current_label}", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)

            y = 60
            for key_code, label in KEY_TO_LABEL.items():
                key_char = chr(key_code)
                cv2.putText(frame, f"[{key_char}] {label}: {counts[label]} samples",
                            (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)
                y += 22

            cv2.putText(frame, "[space] pause/resume   [q] quit", (10, y + 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 200), 1)

            cv2.imshow("Data Collection", frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
            elif key == ord(" "):
                recording = not recording
            elif key in KEY_TO_LABEL:
                current_label = KEY_TO_LABEL[key]
                recording = True

    cap.release()
    cv2.destroyAllWindows()
    print(f"\nSaved to {CSV_PATH}. Final counts: {counts}")


if __name__ == "__main__":
    main()
