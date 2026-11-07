import unittest

from services.api.client import headers


class T(unittest.TestCase):
    def test_bearer(self):
        h = headers()
        self.assertIn('Authorization', h)
        self.assertTrue(h['Authorization'].startswith('Bearer '))


if __name__ == "__main__":
    unittest.main()
