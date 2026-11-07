import unittest
from datetime import date

from dates import days_between, parse_day


class DatesTest(unittest.TestCase):
    def test_parse(self):
        self.assertEqual(parse_day("2026-03-01"), date(2026, 3, 1))

    def test_parse_late_day(self):
        self.assertEqual(parse_day("2026-01-31"), date(2026, 1, 31))

    def test_between(self):
        self.assertEqual(days_between("2026-02-27", "2026-03-02"), 3)


if __name__ == "__main__":
    unittest.main()
