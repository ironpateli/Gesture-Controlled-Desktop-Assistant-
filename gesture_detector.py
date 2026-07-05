"""
gesture_detector.py

Phase 1: Uses MediaPipe's pretrained hand-landmark model purely for
landmark EXTRACTION (21 3D points per hand). Gesture classification
itself is done with simple geometric rules on those landmarks.

This is intentional: MediaPipe gives you robust hand tracking for free,
but the "gesture logic" here is what you'll later replace with your
own trained classifier (Phase 2) once you have a custom dataset.

Landmark index reference (MediaPipe Hands):
  0  = wrist
  1-4  = thumb (CMC, MCP, IP, TIP)
  5-8  = index finger (MCP, PIP, DIP, TIP)
  9-12 = middle finger
  13-16 = ring finger
  17-20 = pinky
"""

import math
from dataclasses import dataclass
from typing import List, Optional, Tuple

import mediapipe as mp

mp_hands = mp.solutions.hands

# Fingertip and PIP (knuckle) landmark indices for the 4 non-thumb fingers
FINGER_TIPS = {"index": 8, "middle": 12, "ring": 16, "pinky": 20}
FINGER_PIPS = {"index": 6, "middle": 10, "ring": 14, "pinky": 18}
THUMB_TIP, THUMB_IP, THUMB_MCP = 4, 3, 2
WRIST = 0


@dataclass
class GestureResult:
    name: str          # e.g. "thumbs_up", "peace", "point", "rock", "thumbs_down", "none"
    confidence: float  # 0-1, heuristic confidence for rule-based stage
    landmarks: list     # raw landmark list, useful later for logging/training data


def _dist(a, b) -> float:
    return math.hypot(a.x - b.x, a.y - b.y)


def _finger_extended(landmarks, finger: str) -> bool:
    """A non-thumb finger counts as 'extended' if its tip is further from
    the wrist than its PIP joint is (simple, orientation-tolerant heuristic)."""
    tip = landmarks[FINGER_TIPS[finger]]
    pip = landmarks[FINGER_PIPS[finger]]
    wrist = landmarks[WRIST]
    return _dist(wrist, tip) > _dist(wrist, pip) * 1.1


def _thumb_extended(landmarks, handedness: str) -> bool:
    """Thumb extension check uses x-offset relative to the IP joint,
    flipped depending on left/right hand."""
    tip = landmarks[THUMB_TIP]
    ip = landmarks[THUMB_IP]
    if handedness == "Right":
        return tip.x < ip.x
    return tip.x > ip.x


def _thumb_points_up(landmarks) -> bool:
    return landmarks[THUMB_TIP].y < landmarks[WRIST].y - 0.05


def _thumb_points_down(landmarks) -> bool:
    return landmarks[THUMB_TIP].y > landmarks[WRIST].y + 0.05


def classify_gesture(landmarks, handedness: str = "Right") -> GestureResult:
    """Rule-based classifier over 5 gestures + 'none' (rejection class).

    Replace the body of this function with a call to your trained model
    once you have your own dataset (see train_classifier.py in Phase 2).
    """
    fingers_up = {f: _finger_extended(landmarks, f) for f in FINGER_TIPS}
    thumb_out = _thumb_extended(landmarks, handedness)
    n_extended = sum(fingers_up.values())

    # Thumbs up: thumb extended + pointing up, all other fingers curled
    if thumb_out and _thumb_points_up(landmarks) and n_extended == 0:
        return GestureResult("thumbs_up", 0.9, landmarks)

    # Thumbs down: thumb extended + pointing down, all other fingers curled
    if thumb_out and _thumb_points_down(landmarks) and n_extended == 0:
        return GestureResult("thumbs_down", 0.9, landmarks)

    # Peace / victory sign: index + middle extended, ring + pinky curled
    if fingers_up["index"] and fingers_up["middle"] and not fingers_up["ring"] and not fingers_up["pinky"]:
        return GestureResult("peace", 0.85, landmarks)

    # Point (one finger): only index extended
    if fingers_up["index"] and not fingers_up["middle"] and not fingers_up["ring"] and not fingers_up["pinky"]:
        return GestureResult("point", 0.85, landmarks)

    # Rock sign: index + pinky extended, middle + ring curled
    if fingers_up["index"] and fingers_up["pinky"] and not fingers_up["middle"] and not fingers_up["ring"]:
        return GestureResult("rock", 0.8, landmarks)

    return GestureResult("none", 0.0, landmarks)


class Debouncer:
    """Requires a gesture to be stable for N consecutive frames before
    it 'fires'. This is the single most important thing for making a
    gesture UI feel usable instead of jittery/spammy."""

    def __init__(self, stable_frames: int = 8, cooldown_frames: int = 15):
        self.stable_frames = stable_frames
        self.cooldown_frames = cooldown_frames
        self._current = "none"
        self._streak = 0
        self._cooldown = 0

    def update(self, gesture_name: str) -> Optional[str]:
        """Feed in the latest raw gesture per frame. Returns a gesture
        name ONLY on the frame it should trigger an action, else None."""
        if self._cooldown > 0:
            self._cooldown -= 1
            return None

        if gesture_name == self._current:
            self._streak += 1
        else:
            self._current = gesture_name
            self._streak = 1

        if gesture_name != "none" and self._streak == self.stable_frames:
            self._cooldown = self.cooldown_frames
            return gesture_name

        return None
