"""Demo toleransi kegagalan: timeout + retry + deduplikasi.
1) Jalankan server dengan balasan lambat acak (balasan terlambat SETELAH commit):
       python server.py --lambat-prob 0.5 --lambat-detik 3
2) Jalankan (server harus baru/bersih untuk jadwal J3; restart server untuk mengulang):
       python demo_retry.py                   # DENGAN request_id tetap  -> konsisten
       (restart server)
       python demo_retry.py --tanpa-dedup     # request_id baru tiap percobaan -> pesanan 'hantu'"""
import argparse
import os
import sys

import grpc

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from klien import KlienBioskop

PEMESAN = "demo-retry"

ap = argparse.ArgumentParser()
ap.add_argument("--host", default="localhost:50051")
ap.add_argument("--jumlah", type=int, default=20)
ap.add_argument("--timeout", type=float, default=1.0)
ap.add_argument("--jadwal", default="J3")
ap.add_argument("--tanpa-dedup", action="store_true")
a = ap.parse_args()

retry = {"n": 0}


def catat(nama, p, kode, jeda):
    retry["n"] += 1
    print(f"   [retry] {nama} percobaan {p} gagal ({kode}); ulang {jeda:.2f}s")


k = KlienBioskop(a.host, timeout=a.timeout, maks_percobaan=4, on_retry=catat)
peta = k.peta(a.jadwal)
if peta.jadwal.kursi_kosong != peta.jadwal.baris * peta.jadwal.kolom:
    raise SystemExit("Jadwal tidak kosong. Restart server dulu agar demo bersih.")
daftar = [x.kode for x in peta.kursi][: a.jumlah]

ok = gagal_semu = timeout = 0
dari_cache = 0
mode = "TANPA deduplikasi (id baru tiap percobaan)" if a.tanpa_dedup else "DENGAN deduplikasi (id tetap)"
print(f"Mode: {mode}; timeout client {a.timeout}s\n")
for kode in daftar:
    try:
        r = k.pesan_kursi(a.jadwal, PEMESAN, [kode], id_baru_tiap_percobaan=a.tanpa_dedup)
    except grpc.RpcError as e:
        timeout += 1
        print(f"{kode}: ERROR {e.code().name} setelah semua percobaan")
        continue
    if r.sukses:
        ok += 1
        dari_cache += r.duplikat
        print(f"{kode}: BERHASIL {'(balasan ulang dari cache dedup)' if r.duplikat else ''}")
    else:
        gagal_semu += 1
        print(f"{kode}: client menerima GAGAL -> '{r.pesan}'")

terisi = sum(1 for x in k.peta(a.jadwal).kursi if x.pemesan == PEMESAN)
print("\n=== Ringkasan ===")
print(f"Permintaan logis           : {len(daftar)}")
print(f"Total retry                : {retry['n']}")
print(f"Dilaporkan sukses (client) : {ok} (di antaranya dari cache dedup: {dari_cache})")
print(f"Dilaporkan gagal  (client) : {gagal_semu}   error timeout: {timeout}")
print(f"Kursi terisi di SERVER     : {terisi}")
print("KONSISTEN: pandangan client == server" if terisi == ok else
      f"TIDAK KONSISTEN: {terisi - ok} kursi terisi di server tetapi client mengira gagal (pesanan hantu)")
k.tutup()
