"""
debug_thumb.py

STANDALONE diagnostic tool — does NOT modify main.py, gesture_detector.py,
or actions.py in any way. Just imports their existing functions and prints
live values to the terminal so we can see exactly which condition fails
when thumbs_up/thumbs_down doesn't fire.

Run this instead of main.py, just for debugging:
    python debug_thumb.py

Press 'q' to quit. Safe to delete this file anytime — it changes nothing
in the rest of the project.
"""

import cv2
import mediapipe as mp

from gesture_detector import (
    _finger_extended,
    _thumb_extended_vertical,
    _thumb_is_vertical,
    _thumb_far_from_index,
    _thumb_points_up,
    _thumb_points_down,
    FINGER_TIPS,
)

mp_hands = mp.solutions.hands


def main():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        raise RuntimeError("Could not open webcam.")

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

            y_offset = 30
            if results.multi_hand_landmarks:
                landmarks = results.multi_hand_landmarks[0].landmark

                thumb_vert = _thumb_extended_vertical(landmarks)
                thumb_aligned = _thumb_is_vertical(landmarks)
                thumb_far = _thumb_far_from_index(landmarks)
                points_up = _thumb_points_up(landmarks)
                points_down = _thumb_points_down(landmarks)
                fingers = {f: _finger_extended(landmarks, f) for f in FINGER_TIPS}
                n_extended = sum(fingers.values())

                lines = [
                    f"thumb_extended_vertical: {thumb_vert}",
                    f"thumb_is_vertical (aligned): {thumb_aligned}",
                    f"thumb_far_from_index: {thumb_far}",
                    f"thumb_points_up: {points_up}",
                    f"thumb_points_down: {points_down}",
                    f"n_extended (other 4 fingers): {n_extended}",
                    f"  index: {fingers['index']}",
                    f"  middle: {fingers['middle']}",
                    f"  ring: {fingers['ring']}",
                    f"  pinky: {fingers['pinky']}",
                ]

                for line in lines:
                    cv2.putText(frame, line, (10, y_offset),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                    y_offset += 25
            else:
                cv2.putText(frame, "No hand detected", (10, y_offset),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

            cv2.imshow("DEBUG - thumb values (standalone, safe)", frame)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()