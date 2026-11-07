import unittest

from calc import avg


class T(unittest.TestCase):
    def test_avg(self):
        self.assertEqual(avg([2, 4]), 3)

    def test_empty(self):
        self.assertEqual(avg([]), 0)


if __name__ == "__main__":
    unittest.main()
