"""Eksperimen race condition pada logika bisnis (tanpa jaringan/gRPC).
Membandingkan penyimpanan DENGAN lock vs TANPA lock: N thread memesan kursi yang sama.
Jalankan: python eksperimen_lokal.py"""
import os
import sys
import threading
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from logika import StoreBioskop


def satu_ronde(tanpa_lock, n):
    s = StoreBioskop(tanpa_lock=tanpa_lock)
    barrier = threading.Barrier(n)
    sukses = []

    def kerja(i):
        barrier.wait()
        h = s.pesan(str(uuid.uuid4()), "J1", f"user{i}", ["A1"])
        if h["sukses"]:
            sukses.append(i)

    ts = [threading.Thread(target=kerja, args=(i,)) for i in range(n)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    return len(sukses)


if __name__ == "__main__":
    N, RONDE = 100, 10
    for nama, tanpa in (("DENGAN lock", False), ("TANPA lock", True)):
        hasil = [satu_ronde(tanpa, N) for _ in range(RONDE)]
        print(f"{nama:12s}: {N} thread rebut kursi A1, {RONDE} ronde -> pemenang per ronde = {hasil}")
        print(f"{'':12s}  ronde dengan pemesanan ganda: {sum(h > 1 for h in hasil)}/{RONDE}")
