import unittest

from apm_stats import build_session_summary


class SessionSummaryTests(unittest.TestCase):
    def test_build_session_summary_formats_values(self):
        text = build_session_summary(142.5, 118.4, 12, 7, 320, 3, 3670, 91.0, 198.5)
        self.assertIn('Avg', text)
        self.assertIn('Best', text)
        self.assertIn('Low', text)
        self.assertIn('Actions', text)
        self.assertIn('Sessions', text)


if __name__ == '__main__':
    unittest.main()
