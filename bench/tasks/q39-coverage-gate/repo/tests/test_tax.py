import unittest

from src.tax import excise, vat


class T(unittest.TestCase):
    def test_vat(self):
        self.assertEqual(vat(10), 2.0)

    def test_excise(self):
        self.assertEqual(excise(100), 5.0)


if __name__ == "__main__":
    unittest.main()
