import unittest

from cart import old_total, total


class T(unittest.TestCase):
    def test_total(self):
        self.assertEqual(total([{'price': 2}, {'price': 3}]), 5)

    def test_total_empty(self):
        self.assertEqual(total([]), 0)

    def test_old_total(self):
        self.assertEqual(old_total([{'price': 1}]), 1)


if __name__ == "__main__":
    unittest.main()
