import unittest
from collections import deque
import time

from apm import APMMonitor


class InputModeTests(unittest.TestCase):
    def setUp(self):
        self.monitor = APMMonitor.__new__(APMMonitor)
        self.monitor.input_mode = 'both'
        self.monitor.paused = False
        self.monitor.events = deque()
        self.monitor.total_actions = 0
        self.monitor.alert_enabled = False
        self.monitor.overlay = False
        self.monitor.alert_state = None
        self.monitor.last_action_time = time.time()
        self.monitor.action_times = []
        self.monitor.high_apm = 0
        self.monitor.low_apm = None
        self.monitor.session_seconds = 300
        self.monitor.smooth_window = 5.0
        self.monitor.session_start = time.time()
        self.monitor.root = None

    def test_keyboard_only_counts_keyboard_events(self):
        self.monitor.input_mode = 'keyboard'
        self.monitor.handle_input_event('mouse', None)
        self.assertEqual(self.monitor.total_actions, 0)

        self.monitor.handle_input_event('keyboard', None)
        self.assertEqual(self.monitor.total_actions, 1)

    def test_mouse_only_counts_mouse_events(self):
        self.monitor.input_mode = 'mouse'
        self.monitor.handle_input_event('keyboard', None)
        self.assertEqual(self.monitor.total_actions, 0)

        self.monitor.handle_input_event('mouse', None)
        self.assertEqual(self.monitor.total_actions, 1)


if __name__ == '__main__':
    unittest.main()
