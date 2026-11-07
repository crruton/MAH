import unittest

from cart import total


class TotalTest(unittest.TestCase):
    def test_two_items(self):
        self.assertEqual(total([{"price": 10, "qty": 2}, {"price": 5, "qty": 1}]), 25)


if __name__ == "__main__":
    unittest.main()
