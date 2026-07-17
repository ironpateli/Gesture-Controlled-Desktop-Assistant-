import unittest

from action_timing import GestureActionGate


VOLUME = {"type": "builtin", "target": "volume_up"}
PLAY_PAUSE = {"type": "builtin", "target": "play_pause"}
HOTKEY = {"type": "hotkey", "target": ["alt", "tab"]}
APP = {"type": "path", "target": "example.exe"}
DISABLED_VOLUME = {"type": "builtin", "target": "volume_up", "enabled": False}


class GestureActionGateTests(unittest.TestCase):
    def test_continuous_action_uses_elapsed_time(self):
        gate = GestureActionGate()
        self.assertTrue(gate.should_fire("thumbs_up", VOLUME, 10.00))
        self.assertFalse(gate.should_fire("thumbs_up", VOLUME, 10.19))
        self.assertTrue(gate.should_fire("thumbs_up", VOLUME, 10.20))

    def test_one_shot_requires_release_even_after_cooldown(self):
        gate = GestureActionGate()
        self.assertTrue(gate.should_fire("peace", PLAY_PAUSE, 1.0))
        self.assertFalse(gate.should_fire("peace", PLAY_PAUSE, 5.0))

        gate.observe("none", 5.10)
        gate.observe("none", 5.44)
        self.assertTrue(gate.waiting_for_release("peace"))
        gate.observe("none", 5.45)
        self.assertTrue(gate.should_fire("peace", PLAY_PAUSE, 5.46))

    def test_motion_gesture_has_repositioning_interval(self):
        gate = GestureActionGate()
        self.assertTrue(gate.should_fire("swipe_left", HOTKEY, 2.0))
        self.assertFalse(gate.should_fire("swipe_left", HOTKEY, 2.79))
        self.assertTrue(gate.should_fire("swipe_left", HOTKEY, 2.80))

    def test_launch_action_uses_longer_interval(self):
        gate = GestureActionGate()
        self.assertTrue(gate.should_fire("swipe_right", APP, 3.0))
        self.assertFalse(gate.should_fire("swipe_right", APP, 4.99))
        self.assertTrue(gate.should_fire("swipe_right", APP, 5.0))

    def test_remapped_static_gesture_is_not_forced_to_repeat(self):
        gate = GestureActionGate()
        self.assertTrue(gate.should_fire("thumbs_up", HOTKEY, 1.0))
        self.assertFalse(gate.should_fire("thumbs_up", HOTKEY, 3.0))

    def test_hand_leaving_rearms_one_shot_but_preserves_deadline(self):
        gate = GestureActionGate()
        self.assertTrue(gate.should_fire("fist", APP, 1.0))
        gate.hand_left_frame()
        self.assertFalse(gate.should_fire("fist", APP, 2.9))
        self.assertTrue(gate.should_fire("fist", APP, 3.0))

    def test_disabled_gesture_does_not_fire_or_start_cooldown(self):
        gate = GestureActionGate()
        self.assertFalse(gate.should_fire("thumbs_up", DISABLED_VOLUME, 1.0))
        self.assertTrue(gate.should_fire("thumbs_up", VOLUME, 1.0))


if __name__ == "__main__":
    unittest.main()
