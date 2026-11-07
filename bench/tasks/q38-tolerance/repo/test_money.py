import unittest

from money import split


class T(unittest.TestCase):
    def test_sum(self):
        parts = split(100, 3)
        self.assertAlmostEqual(sum(parts), 100, places=6)
        self.assertEqual(parts, [33.34, 33.33, 33.33])


if __name__ == "__main__":
    unittest.main()
