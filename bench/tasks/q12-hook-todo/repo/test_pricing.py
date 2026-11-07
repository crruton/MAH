import unittest

from pricing import gross, net


class PricingTest(unittest.TestCase):
    def test_net(self):
        self.assertEqual(net(100, 0.1), 90)

    def test_gross(self):
        self.assertEqual(gross(100, 0.2), 120)


if __name__ == "__main__":
    unittest.main()
