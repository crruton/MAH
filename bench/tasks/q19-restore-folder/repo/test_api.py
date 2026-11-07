import unittest

from src.api.routes import route


class T(unittest.TestCase):
    def test_route(self):
        self.assertEqual(route('/a'), '/v1/a')


if __name__ == "__main__":
    unittest.main()
