import unittest

import json, tempfile, os
from db import dsn


class T(unittest.TestCase):
    def test_password(self):
        p = os.path.join(tempfile.mkdtemp(), 's.json')
        json.dump({'user': 'u', 'password': 'p', 'host': 'h', 'port': 1, 'name': 'n'}, open(p, 'w', encoding='utf-8'))
        self.assertEqual(dsn(p), 'postgres://u:p@h:1/n')


if __name__ == "__main__":
    unittest.main()
