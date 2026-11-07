import unittest

from pages import page


class T(unittest.TestCase):
    def test_first_page(self):
        self.assertEqual(page(list(range(25)), 1), list(range(10)))

    def test_last_page(self):
        self.assertEqual(page(list(range(25)), 3), [20, 21, 22, 23, 24])


if __name__ == "__main__":
    unittest.main()
