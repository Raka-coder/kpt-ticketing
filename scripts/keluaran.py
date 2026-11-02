"""Duplikasi stdout ke layar sekaligus ke file bukti pengujian."""
import contextlib
import os
import sys


class _Tee:
    def __init__(self, utama, cadangan):
        self.utama = utama
        self.cadangan = cadangan

    def write(self, teks):
        self.utama.write(teks)
        self.cadangan.write(teks)

    def flush(self):
        self.utama.flush()
        self.cadangan.flush()


@contextlib.contextmanager
def catat_ke(path):
    folder = os.path.dirname(path)
    if folder:
        os.makedirs(folder, exist_ok=True)
    with open(path, "w", encoding="utf-8") as berkas:
        asli = sys.stdout
        sys.stdout = _Tee(asli, berkas)
        try:
            yield berkas
        finally:
            sys.stdout = asli
            berkas.flush()
