"""Runner proxy lokal untuk scripts/run_race_local.py"""
import subprocess
import sys

if __name__ == "__main__":
    cmd = [sys.executable, "scripts/run_race_local.py"] + sys.argv[1:]
    raise SystemExit(subprocess.call(cmd))
