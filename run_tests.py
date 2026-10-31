"""Jalankan seluruh uji lokal dengan satu perintah: python run_tests.py"""
import os
import subprocess
import sys

root = os.path.dirname(os.path.abspath(__file__))
os.chdir(root)
cmd = [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"]
raise SystemExit(subprocess.call(cmd))
