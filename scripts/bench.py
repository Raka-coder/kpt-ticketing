"""Pengujian kinerja dan visualisasi skalabilitas (Skenario A - Komputasi Paralel).
Mengukur:
1. Waktu total pemrosesan N transaksi dengan variasi thread worker/client (1, 5, 20).
2. Throughput (req/s) dan latensi rata-rata.
3. Otomatis menghasilkan grafik scaling batang dan garis ke folder hasil/grafik_scaling.png & hasil/hasil_bench.png.

Jalankan:
  python scripts/bench.py --host localhost:50051 --n 20 --klien 1 5 20
"""
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
    barrier = threading.Barrier(jml_klien + 1, timeout=120)

    def kerja(i):
        k = KlienBioskop(host, timeout=30, maks_percobaan=1)
        kursi = f"{chr(65 + i % 26)}{1 + i // 26}"
        lokal = []
        barrier.wait()
        for _ in range(n):
            try:
                if mode == "baca":
                    t = time.perf_counter()
                    k.peta(jadwal)
                    lokal.append(time.perf_counter() - t)
                else:
                    t = time.perf_counter()
                    r = k.pesan_kursi(jadwal, f"bench{i}", [kursi])
                    lokal.append(time.perf_counter() - t)
                    t = time.perf_counter()
                    k.batalkan(r.kode_booking, f"bench{i}")
                    lokal.append(time.perf_counter() - t)
            except Exception:  # noqa: BLE001
                with kunci:
                    galat[0] += 1
        with kunci:
            lat.extend(lokal)
        k.tutup()

    ts = [threading.Thread(target=kerja, args=(i,)) for i in range(jml_klien)]
    for t in ts:
        t.start()
    barrier.wait()
    t0 = time.perf_counter()
    for t in ts:
        t.join()
    total = time.perf_counter() - t0
    lat_ms = sorted(x * 1000 for x in lat) if lat else [0.0]
    total_op = len(lat_ms)
    return dict(mode=mode, klien=jml_klien, total_op=total_op, galat=galat[0],
                waktu_s=round(total, 3),
                throughput=round(total_op / total, 1) if total > 0 else 0.0,
                lat_avg_ms=round(statistics.mean(lat_ms), 2) if lat_ms else 0.0,
                lat_p95_ms=round(lat_ms[int(0.95 * (len(lat_ms) - 1))], 2) if lat_ms else 0.0)


def buat_grafik(baris, klien_list, keluar_dir):
    """Menghasilkan grafik scaling sesuai instruksi plan.md Bagian 2 & 4."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        # 1. Grafik Scaling Batang Skenario A (Waktu Total Pemrosesan vs Jumlah Worker)
        tulis_rows = [r for r in baris if r["mode"] == "tulis"]
        if tulis_rows:
            fig_bar, ax_bar = plt.subplots(figsize=(7, 5))
            workers = [str(r["klien"]) for r in tulis_rows]
            waktu_total = [r["waktu_s"] for r in tulis_rows]
            bars = ax_bar.bar(workers, waktu_total, color="#2b5c8f", width=0.5, edgecolor="black")
            ax_bar.set_title("Skalabilitas Server Ticketing (Simulasi Validasi Pembayaran)", fontsize=12, fontweight="bold")
            ax_bar.set_xlabel("Jumlah Thread Worker / Client", fontsize=10)
            ax_bar.set_ylabel("Waktu Total Pemrosesan (detik)", fontsize=10)
            ax_bar.grid(axis="y", linestyle="--", alpha=0.5)

            for b in bars:
                h = b.get_height()
                ax_bar.annotate(f"{h:.2f}s",
                                xy=(b.get_x() + b.get_width() / 2, h),
                                xytext=(0, 3), textcoords="offset points",
                                ha="center", va="bottom", fontsize=9, fontweight="bold")

            fig_bar.tight_layout()
            path_scaling = os.path.join(keluar_dir, "grafik_scaling.png")
            fig_bar.savefig(path_scaling, dpi=150)
            plt.close(fig_bar)
            print(f"Grafik tersimpan di {path_scaling}")

        # 2. Grafik Detail Throughput & Latensi
        fig, ax = plt.subplots(1, 2, figsize=(11, 4.5))
        for mode in ("baca", "tulis"):
            d = [r for r in baris if r["mode"] == mode]
            if d:
                ax[0].plot([r["klien"] for r in d], [r["throughput"] for r in d], "o-", label=mode, linewidth=2)
                ax[1].plot([r["klien"] for r in d], [r["lat_avg_ms"] for r in d], "s-", label=mode, linewidth=2)

        ax[0].set_title("Throughput Sistem", fontsize=11, fontweight="bold")
        ax[0].set_xlabel("Jumlah Thread Worker / Client", fontsize=9)
        ax[0].set_ylabel("Throughput (req/s)", fontsize=9)
        ax[0].set_xticks(klien_list)
        ax[0].grid(alpha=0.3)
        ax[0].legend()

        ax[1].set_title("Latensi Rata-Rata", fontsize=11, fontweight="bold")
        ax[1].set_xlabel("Jumlah Thread Worker / Client", fontsize=9)
        ax[1].set_ylabel("Latensi (ms)", fontsize=9)
        ax[1].set_xticks(klien_list)
        ax[1].grid(alpha=0.3)
        ax[1].legend()

        fig.tight_layout()
        path_bench = os.path.join(keluar_dir, "hasil_bench.png")
        fig.savefig(path_bench, dpi=150)
        plt.close(fig)
        print(f"Grafik throughput & latensi tersimpan di {path_bench}")

    except ImportError:
        print("[bench] matplotlib tidak terpasang; pembuatan grafik dilewati.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--host", default="localhost:50051")
    ap.add_argument("--n", type=int, default=10, help="iterasi transaksi per client")
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

    # Simpan CSV hasil_bench.csv
    csv_path = os.path.join(a.keluar, "hasil_bench.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(baris[0].keys()))
        w.writeheader()
        w.writerows(baris)
    print("CSV tersimpan di:", csv_path)

    # Simpan juga format benchmark_scaling.csv sesuai plan.md
    scaling_csv_path = os.path.join(a.keluar, "benchmark_scaling.csv")
    tulis_data = [dict(workers=r["klien"], waktu_total=r["waktu_s"], throughput=r["throughput"])
                  for r in baris if r["mode"] == "tulis"]
    if tulis_data:
        with open(scaling_csv_path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["workers", "waktu_total", "throughput"])
            w.writeheader()
            w.writerows(tulis_data)
        print("CSV scaling tersimpan di:", scaling_csv_path)

    # Buat visualisasi grafik otomatis
    buat_grafik(baris, a.klien, a.keluar)
