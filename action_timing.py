"""Time-based gesture action gating, independent of camera frame rate."""

CONTINUOUS_INTERVAL_SECONDS = 0.20
MOTION_INTERVAL_SECONDS = 0.80
ONE_SHOT_INTERVAL_SECONDS = 0.80
LAUNCH_INTERVAL_SECONDS = 2.00
RELEASE_TO_REARM_SECONDS = 0.35

MOTION_GESTURES = {"swipe_left", "swipe_right", "swipe_up", "swipe_down"}
CONTINUOUS_TARGETS = {"volume_up", "volume_down", "scroll_up", "scroll_down"}
LAUNCH_ACTION_TYPES = {"path", "uri", "script"}


class GestureActionGate:
    def __init__(self):
        self._next_allowed = {}
        self._latched = set()
        self._release_started = {}

    def _update_rearming(self, current_gesture: str, now: float) -> None:
        for gesture in tuple(self._latched):
            if gesture == current_gesture:
                release_started = self._release_started.get(gesture)
                if (
                    release_started is not None
                    and now - release_started >= RELEASE_TO_REARM_SECONDS
                ):
                    self._latched.remove(gesture)
                self._release_started.pop(gesture, None)
                continue

            release_started = self._release_started.setdefault(gesture, now)
            if now - release_started >= RELEASE_TO_REARM_SECONDS:
                self._latched.remove(gesture)
                self._release_started.pop(gesture, None)

    @staticmethod
    def _behavior(gesture: str, action_entry: dict) -> tuple[str, float]:
        action_type = action_entry.get("type")
        target = action_entry.get("target")

        if gesture in MOTION_GESTURES:
            interval = (
                LAUNCH_INTERVAL_SECONDS
                if action_type in LAUNCH_ACTION_TYPES
                else MOTION_INTERVAL_SECONDS
            )
            return "motion", interval

        if action_type in LAUNCH_ACTION_TYPES:
            return "one_shot", LAUNCH_INTERVAL_SECONDS

        if isinstance(target, str) and target in CONTINUOUS_TARGETS:
            return "continuous", CONTINUOUS_INTERVAL_SECONDS

        return "one_shot", ONE_SHOT_INTERVAL_SECONDS

    def should_fire(self, gesture: str, action_entry: dict, now: float) -> bool:
        """Return whether this recognized gesture may dispatch at `now`."""
        if gesture == "none" or not action_entry or not action_entry.get("enabled", True):
            self._update_rearming("none", now)
            return False

        self._update_rearming(gesture, now)

        behavior, interval = self._behavior(gesture, action_entry)
        if now < self._next_allowed.get(gesture, 0.0):
            return False
        if behavior == "one_shot" and gesture in self._latched:
            return False

        self._next_allowed[gesture] = now + interval
        if behavior == "one_shot":
            self._latched.add(gesture)
            self._release_started.pop(gesture, None)
        return True

    def observe(self, gesture: str, now: float) -> None:
        """Update release-to-rearm state when no action candidate is dispatched."""
        self._update_rearming(gesture, now)

    def hand_left_frame(self) -> None:
        """A missing hand is an explicit release, but time deadlines remain."""
        self._latched.clear()
        self._release_started.clear()

    def cooldown_remaining(self, gesture: str, now: float) -> float:
        return max(0.0, self._next_allowed.get(gesture, 0.0) - now)

    def waiting_for_release(self, gesture: str) -> bool:
        return gesture in self._latched
