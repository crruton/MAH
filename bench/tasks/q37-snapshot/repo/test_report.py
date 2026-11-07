import unittest

from pathlib import Path
from report import render


class T(unittest.TestCase):
    def test_snapshot(self):
        self.assertEqual(render([('alpha', 12.5), ('beta', 3)]), Path('snapshots/report.txt').read_text(encoding='utf-8'))


if __name__ == "__main__":
    unittest.main()
