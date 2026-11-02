"""Benchmark lintas jaringan (2 laptop) — dijalankan di LAPTOP CLIENT.

Membungkus scripts/bench.py dan scripts/uji_race.py, lalu otomatis menyimpan
semua bukti ke folder hasil/ dengan akhiran _jaringan (tanpa perintah tee/mv):

  hasil/hasil_bench_jaringan.csv
  hasil/hasil_bench.png      -> hasil/hasil_bench_jaringan.png
  hasil/grafik_scaling.png   -> hasil/grafik_scaling_jaringan.png
  hasil/bench_log_jaringan.txt   (log console benchmark, calon bukti)
  hasil/uji_race_jaringan.txt    (bukti race lintas mesin)

Hasil LOKAL di hasil/ tidak disentuh (bench dijalankan ke folder sementara
hasil_jaringan/, lalu dihapus setelah dipindah).

Jalankan:
  python scripts/jaringan.py --host 192.168.1.28:50051
  python scripts/jaringan.py                 (host otomatis dari master_ip.txt)
"""
import argparse
import csv
import os
import shutil
import subprocess
import sys

AKAR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR_FUGU = os.path.join(AKAR, "hasil_jaringan")
DIR_HASIL = os.path.join(AKAR, "hasil")
LOG_BENCH = os.path.join(DIR_HASIL, "bench_log_jaringan.txt")
LOG_RACE = os.path.join(DIR_HASIL, "uji_race_jaringan.txt")
CSV_JARINGAN = os.path.join(DIR_HASIL, "hasil_bench_jaringan.csv")
PNG_BENCH_JARINGAN = os.path.join(DIR_HASIL, "hasil_bench_jaringan.png")
PNG_SCALING_JARINGAN = os.path.join(DIR_HASIL, "grafik_scaling_jaringan.png")

PINDAH = [
    ("hasil_bench.csv", CSV_JARINGAN),
    ("hasil_bench.png", PNG_BENCH_JARINGAN),
    ("grafik_scaling.png", PNG_SCALING_JARINGAN),
]


def baca_host_default():
    path = os.path.join(AKAR, "master_ip.txt")
    if os.path.isfile(path):
        isi = open(path, encoding="utf-8").read().strip()
        if isi:
            return f"{isi}:50051"
    return "localhost:50051"


def jalankan_dan_catat(cmd, tujuan_log=None):
    """Menjalankan subproses; output dialirkan ke console dan (opsional) file log."""
    if tujuan_log is None:
        proses = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace", cwd=AKAR, bufsize=1,
        )
        for baris in proses.stdout:
            sys.stdout.write(baris)
            sys.stdout.flush()
        proses.wait()
        return proses.returncode

    with open(tujuan_log, "w", encoding="utf-8") as log:
        proses = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace", cwd=AKAR, bufsize=1,
        )
        for baris in proses.stdout:
            sys.stdout.write(baris)
            sys.stdout.flush()
            log.write(baris)
            log.flush()
        proses.wait()
    return proses.returncode


def verifikasi():
    print("\n=== VERIFIKASI ===")
    if not os.path.isfile(CSV_JARINGAN):
        print("GAGAL: hasil/hasil_bench_jaringan.csv tidak ada.")
        return 1
    with open(CSV_JARINGAN, newline="", encoding="utf-8") as f:
        baris = list(csv.DictReader(f))
    ok = True
    galat_total = sum(int(r["galat"]) for r in baris)
    print(f"Baris CSV jaringan : {len(baris)} (harus 6), galat={galat_total} (harus 0)")
    ok &= len(baris) == 6 and galat_total == 0

    csv_lokal = os.path.join(DIR_HASIL, "hasil_bench.csv")
    if os.path.isfile(csv_lokal):
        with open(csv_lokal, newline="", encoding="utf-8") as f:
            lokal = {(r["mode"], int(r["klien"])): r for r in csv.DictReader(f)}
        lebih_lambat = all(
            float(r["lat_avg_ms"]) >= float(lokal.get((r["mode"], int(r["klien"])), {}).get("lat_avg_ms", "0"))
            for r in baris
        )
        print(f"Latensi jaringan >= lokal (semua kombinasi): {lebih_lambat}")
        if not lebih_lambat:
            print("PERINGATAN: latensi jaringan tidak konsisten lebih besar dari lokal —")
            print("curigai benchmark tertukar dengan localhost dan ulangi dengan host benar.")
            ok = False

    for path, nama in ((LOG_BENCH, "bench_log_jaringan.txt"),):
        print(f"{nama:28s}: {'ADA' if os.path.isfile(path) else 'TIDAK ADA'}")
        ok &= os.path.isfile(path)
    for path, nama in ((PNG_BENCH_JARINGAN, "hasil_bench_jaringan.png"),
                       (PNG_SCALING_JARINGAN, "grafik_scaling_jaringan.png")):
        ada = os.path.isfile(path)
        print(f"{nama:28s}: {'ADA' if ada else 'TIDAK ADA'}")
        ok &= ada

    if os.path.isfile(LOG_RACE):
        isi = open(LOG_RACE, encoding="utf-8", errors="replace").read()
        lulus = "SEMUA LULUS" in isi
        print(f"uji_race_jaringan.txt       : {'SEMUA LULUS' if lulus else 'belum SEMUA LULUS'}")
        ok &= lulus
    print("HASIL AKHIR:", "LULUS" if ok else "PERIKSA KEMBALI")
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--host", default=None, help="mis. 192.168.1.28:50051 (default: master_ip.txt)")
    ap.add_argument("--n", type=int, default=10)
    ap.add_argument("--klien", type=int, nargs="+", default=[1, 5, 20])
    ap.add_argument("--lewati-race", action="store_true", help="lewati uji_race lintas mesin")
    a = ap.parse_args()

    host = a.host or baca_host_default()
    os.makedirs(DIR_HASIL, exist_ok=True)
    print(f"Host server : {host}")
    print(f"Log console -> {os.path.relpath(LOG_BENCH, AKAR)}\n")

    cmd_bench = [sys.executable, os.path.join(AKAR, "scripts", "bench.py"),
                 "--host", host, "--n", str(a.n),
                 "--klien", *[str(k) for k in a.klien],
                 "--keluar", DIR_FUGU]
    kode = jalankan_dan_catat(cmd_bench, LOG_BENCH)
    if kode != 0 or not os.path.isfile(os.path.join(DIR_FUGU, "hasil_bench.csv")):
        print(f"\n[!] Benchmark gagal (kode={kode}). Periksa host/firewall; log tetap disimpan.")
        return 1

    for sumber, tujuan in PINDAH:
        if os.path.isfile(os.path.join(DIR_FUGU, os.path.basename(sumber))):
            shutil.move(os.path.join(DIR_FUGU, sumber), tujuan)
            print(f"Pindah -> {os.path.relpath(tujuan, AKAR)}")
    shutil.rmtree(DIR_FUGU, ignore_errors=True)

    if not a.lewati_race:
        print(f"\n=== Uji race lintas mesin -> {os.path.relpath(LOG_RACE, AKAR)} ===")
        cmd_race = [sys.executable, os.path.join(AKAR, "scripts", "uji_race.py"),
                    "--host", host, "--klien", "50", "--keluar", LOG_RACE]
        kode_race = jalankan_dan_catat(cmd_race)
        if kode_race != 0:
            print("[!] uji_race gagal, tapi bukti benchmark benchmark tetap tersimpan.")

    return verifikasi()


if __name__ == "__main__":
    raise SystemExit(main())
