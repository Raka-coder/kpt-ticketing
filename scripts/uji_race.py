"""Uji beban race condition lewat gRPC.
Tes 1: N client rebut SATU kursi yang sama serentak -> harus tepat 1 pemenang.
Tes 2: N client masing-masing meminta 3 kursi acak dari satu studio -> tidak boleh ada
       kursi dimiliki dua pesanan, dan jumlah kursi terisi harus konsisten.
Semua pesanan dibatalkan di akhir sehingga tes bisa diulang.
Jalankan: python uji_race.py --host localhost:50051 --klien 50"""
import argparse
import os
import random
import sys
import threading

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from klien import KlienBioskop


def serentak(n, host, fungsi):
    barrier = threading.Barrier(n, timeout=60)
    hasil, galat = [None] * n, []

    def kerja(i):
        k = KlienBioskop(host, timeout=15, maks_percobaan=1)
        try:
            barrier.wait()
            hasil[i] = fungsi(i, k)
        except Exception as e:  # noqa: BLE001
            galat.append(repr(e))
        finally:
            k.tutup()

    ts = [threading.Thread(target=kerja, args=(i,)) for i in range(n)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    return hasil, galat


def tes_satu_kursi(host, n, jadwal, kursi):
    hasil, galat = serentak(n, host, lambda i, k: k.pesan_kursi(jadwal, f"user{i}", [kursi]))
    menang = [(i, r) for i, r in enumerate(hasil) if r is not None and r.sukses]
    ok = len(menang) == 1 and not galat
    print(f"[Tes 1] {n} client rebut {jadwal}/{kursi}: pemenang={len(menang)}, "
          f"galat={len(galat)} -> {'LULUS' if ok else 'GAGAL'}")
    k = KlienBioskop(host)
    for i, r in menang:
        k.batalkan(r.kode_booking, f"user{i}")
    k.tutup()
    return ok


def tes_acak(host, n, jadwal, jml_kursi=3):
    k = KlienBioskop(host)
    peta0 = k.peta(jadwal)
    semua = [x.kode for x in peta0.kursi]
    kosong0 = peta0.jadwal.kursi_kosong
    rnd = random.Random(42)
    pilihan = [rnd.sample(semua, jml_kursi) for _ in range(n)]
    hasil, galat = serentak(n, host, lambda i, c: c.pesan_kursi(jadwal, f"user{i}", pilihan[i]))
    sukses = [(i, r) for i, r in enumerate(hasil) if r is not None and r.sukses]
    terpakai = [x for _, r in sukses for x in r.kursi_dipesan]
    kosong1 = k.peta(jadwal).jadwal.kursi_kosong
    tanpa_ganda = len(terpakai) == len(set(terpakai))
    konsisten = (kosong0 - kosong1) == len(terpakai)
    ok = tanpa_ganda and konsisten and not galat
    print(f"[Tes 2] {n} client x {jml_kursi} kursi acak di {jadwal}: pesanan sukses={len(sukses)}, "
          f"kursi terpakai={len(terpakai)}, kursi ganda={'tidak ada' if tanpa_ganda else 'ADA'}, "
          f"jumlah konsisten={'ya' if konsisten else 'TIDAK'}, galat={len(galat)} "
          f"-> {'LULUS' if ok else 'GAGAL'}")
    for i, r in sukses:
        k.batalkan(r.kode_booking, f"user{i}")
    k.tutup()
    return ok


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="localhost:50051")
    ap.add_argument("--klien", type=int, default=50)
    ap.add_argument("--jadwal1", default="J1")
    ap.add_argument("--kursi", default="A1")
    ap.add_argument("--jadwal2", default="J2")
    a = ap.parse_args()
    hasil = [tes_satu_kursi(a.host, a.klien, a.jadwal1, a.kursi),
             tes_acak(a.host, a.klien * 2, a.jadwal2)]
    print("SEMUA LULUS" if all(hasil) else "ADA YANG GAGAL")
    sys.exit(0 if all(hasil) else 1)
