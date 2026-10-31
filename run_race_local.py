"""Jalankan uji race condition lokal (server + client) dengan satu perintah: python run_race_local.py"""
import os
import subprocess
import sys
import time

root = os.path.dirname(os.path.abspath(__file__))
os.chdir(root)
server = subprocess.Popen([sys.executable, "server.py", "--port", "50051", "--workers", "32"],
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
try:
    time.sleep(2)
    r = subprocess.run([sys.executable, "scripts/uji_race.py", "--host", "localhost:50051", "--klien", "50"])
    raise SystemExit(r.returncode)
finally:
    server.terminate()
    try:
        server.wait(timeout=5)
    except subprocess.TimeoutExpired:
        server.kill()
