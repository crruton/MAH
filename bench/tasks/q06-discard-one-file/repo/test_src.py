import unittest

from src.a import greet
from src.b import double


class SrcTest(unittest.TestCase):
    def test_greet(self):
        self.assertEqual(greet("Ann"), "Hello, Ann")

    def test_double(self):
        self.assertEqual(double(4), 8)


if __name__ == "__main__":
    unittest.main()
