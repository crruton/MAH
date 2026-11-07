import unittest

from shop.cart import subtotal, total


class CartTest(unittest.TestCase):
    def test_subtotal(self):
        self.assertEqual(subtotal([{"price": 10, "qty": 2}, {"price": 5, "qty": 1}]), 25)

    def test_total_eu(self):
        self.assertEqual(total([{"price": 100, "qty": 1}], "SAVE10", "EU"), 108.0)


if __name__ == "__main__":
    unittest.main()
