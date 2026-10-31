"""Jalankan seluruh uji lokal dengan satu perintah: python run_tests.py (mendukung pytest dan unittest)."""
import os
import subprocess
import sys

root = os.path.dirname(os.path.abspath(__file__))
os.chdir(root)

# Cek apakah pytest tersedia di lingkungan sistem
try:
    import pytest
    cmd = [sys.executable, "-m", "pytest", "tests/", "-v"]
    print("[run_tests] Menggunakan pytest runner...")
    raise SystemExit(subprocess.call(cmd))
except ImportError:
    print("[run_tests] pytest belum terpasang, menjalankan unittest + uji pytest standalone...")
    # Jalankan unittest
    res1 = subprocess.call([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"])
    # Jalankan standalone pytest test functions
    from tests.test_logika import test_race_condition_kursi_sama
    try:
        test_race_condition_kursi_sama()
        print("test_race_condition_kursi_sama (standalone pytest format) ... ok")
    except AssertionError as e:
        print(f"test_race_condition_kursi_sama GAGAL: {e}")
        raise SystemExit(1)
    raise SystemExit(res1)

