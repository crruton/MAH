import unittest

import os, tempfile
from scripts.download import credentials


class T(unittest.TestCase):
    def test_host(self):
        p = os.path.join(tempfile.mkdtemp(), 'n')
        open(p, 'w', encoding='utf-8').write('machine files.example.com login u password p\n')
        self.assertEqual(credentials(p), ('u', 'p'))


if __name__ == "__main__":
    unittest.main()
