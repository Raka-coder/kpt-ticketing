"""Pengujian kinerja: latensi rata-rata & throughput untuk 1, 5, dan 20 client bersamaan.
Mode 'baca'  : GetPetaKursi.
Mode 'tulis' : PesanKursi lalu BatalkanPesanan (kursi unik per client, jadi state kembali bersih).
Hasil: hasil/hasil_bench.csv dan hasil/hasil_bench.png
Jalankan: python bench.py --host localhost:50051 --n 100"""
import argparse
import csv
import os
import statistics
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from klien import KlienBioskop


def jalankan(host, jml_klien, n, jadwal, mode):
    lat, galat = [], [0]
    kunci = threading.Lock()
    barrier = threading.Barrier(jml_klien + 1, timeout=60)

    def kerja(i):
        k = KlienBioskop(host, timeout=30, maks_percobaan=1)
        kursi = f"{chr(65 + i % 26)}{1 + i // 26}"
        lokal = []
        barrier.wait()
        for _ in range(n):
            try:
                if mode == "baca":
                    t = time.perf_counter(); k.peta(jadwal); lokal.append(time.perf_counter() - t)
                else:
                    t = time.perf_counter(); r = k.pesan_kursi(jadwal, f"bench{i}", [kursi])
                    lokal.append(time.perf_counter() - t)
                    t = time.perf_counter(); k.batalkan(r.kode_booking, f"bench{i}")
                    lokal.append(time.perf_counter() - t)
            except Exception:  # noqa: BLE001
                with kunci:
                    galat[0] += 1
        with kunci:
            lat.extend(lokal)
        k.tutup()

    ts = [threading.Thread(target=kerja, args=(i,)) for i in range(jml_klien)]
    [t.start() for t in ts]
    barrier.wait()
    t0 = time.perf_counter()
    [t.join() for t in ts]
    total = time.perf_counter() - t0
    lat_ms = sorted(x * 1000 for x in lat)
    return dict(mode=mode, klien=jml_klien, total_op=len(lat_ms), galat=galat[0],
                waktu_s=round(total, 3), throughput=round(len(lat_ms) / total, 1),
                lat_avg_ms=round(statistics.mean(lat_ms), 2),
                lat_p95_ms=round(lat_ms[int(0.95 * (len(lat_ms) - 1))], 2))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="localhost:50051")
    ap.add_argument("--n", type=int, default=100, help="iterasi per client")
    ap.add_argument("--klien", type=int, nargs="+", default=[1, 5, 20])
    ap.add_argument("--jadwal", default="J9")
    ap.add_argument("--keluar", default="hasil")
    a = ap.parse_args()
    os.makedirs(a.keluar, exist_ok=True)

    baris = []
    print(f"{'mode':6s} {'klien':>5s} {'op':>6s} {'waktu(s)':>9s} {'req/s':>8s} {'avg(ms)':>8s} {'p95(ms)':>8s} {'galat':>5s}")
    for mode in ("baca", "tulis"):
        for c in a.klien:
            r = jalankan(a.host, c, a.n, a.jadwal, mode)
            baris.append(r)
            print(f"{r['mode']:6s} {r['klien']:5d} {r['total_op']:6d} {r['waktu_s']:9.3f} "
                  f"{r['throughput']:8.1f} {r['lat_avg_ms']:8.2f} {r['lat_p95_ms']:8.2f} {r['galat']:5d}")

    csv_path = os.path.join(a.keluar, "hasil_bench.csv")
    with open(csv_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(baris[0].keys()))
        w.writeheader(); w.writerows(baris)
    print("Tersimpan:", csv_path)

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(1, 2, figsize=(10, 4))
        for mode in ("baca", "tulis"):
            d = [r for r in baris if r["mode"] == mode]
            ax[0].plot([r["klien"] for r in d], [r["throughput"] for r in d], "o-", label=mode)
            ax[1].plot([r["klien"] for r in d], [r["lat_avg_ms"] for r in d], "o-", label=mode)
        ax[0].set(title="Throughput", xlabel="Jumlah client", ylabel="req/s")
        ax[1].set(title="Latensi rata-rata", xlabel="Jumlah client", ylabel="ms")
        for x in ax:
            x.set_xticks(a.klien); x.grid(alpha=.3); x.legend()
        fig.tight_layout()
        png = os.path.join(a.keluar, "hasil_bench.png")
        fig.savefig(png, dpi=150)
        print("Grafik   :", png)
    except ImportError:
        print("matplotlib tidak terpasang; grafik dilewati (pip install -r requirements-bench.txt)")
