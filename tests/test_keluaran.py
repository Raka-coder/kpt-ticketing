"""Uji helper pencatat keluaran: python -m unittest tests.test_keluaran"""
import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.keluaran import catat_ke


class TesKeluaran(unittest.TestCase):
    def test_menulis_ke_layar_dan_file(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "sub", "hasil.txt")
            with redirect_stdout(io.StringIO()) as layar:
                with catat_ke(path):
                    print("baris uji")
            with open(path, encoding="utf-8") as f:
                self.assertEqual(f.read(), "baris uji\n")
            self.assertEqual(layar.getvalue(), "baris uji\n")

    def test_menimpa_file_lama(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "hasil.txt")
            with open(path, "w", encoding="utf-8") as f:
                f.write("data lama\n")
            with redirect_stdout(io.StringIO()):
                with catat_ke(path):
                    print("data baru")
            with open(path, encoding="utf-8") as f:
                self.assertEqual(f.read(), "data baru\n")

    def test_stdout_dipulihkan_setelah_selesai(self):
        asli = sys.stdout
        with tempfile.TemporaryDirectory() as d:
            with catat_ke(os.path.join(d, "hasil.txt")):
                pass
            self.assertIs(sys.stdout, asli)

    def test_stdout_dipulihkan_saat_galat(self):
        asli = sys.stdout
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(RuntimeError):
                with catat_ke(os.path.join(d, "hasil.txt")):
                    raise RuntimeError("gagal")
            self.assertIs(sys.stdout, asli)


if __name__ == "__main__":
    unittest.main()
