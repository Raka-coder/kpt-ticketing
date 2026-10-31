"""CLI interaktif.
  python klien_cli.py jadwal
  python klien_cli.py peta J1
  python klien_cli.py pesan J1 Andi A1 A2
  python klien_cli.py batal J1-0001 Andi
  python klien_cli.py pantau J1          # tampilkan perubahan kursi real-time (Ctrl+C berhenti)
Gunakan --host IP:PORT untuk server di komputer lain."""
import argparse

import grpc

import bioskop_pb2 as pb
from klien import KlienBioskop


def cetak_peta(peta):
    j = peta.jadwal
    print(f"{j.id} | {j.film} | {j.studio} | {j.waktu} | kosong {j.kursi_kosong}/{j.baris * j.kolom}")
    print("        ====== LAYAR ======")
    baris = {}
    for k in peta.kursi:
        baris.setdefault(k.kode[0], []).append(k)
    for huruf, ks in baris.items():
        print(f"  {huruf:>2} " + " ".join("[X]" if k.status == pb.TERISI else "[ ]" for k in ks))
    print("  [ ] kosong   [X] terisi")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--host", default="localhost:50051")
    sp = ap.add_subparsers(dest="cmd", required=True)
    sp.add_parser("jadwal")
    sp.add_parser("peta").add_argument("jadwal_id")
    p = sp.add_parser("pesan")
    p.add_argument("jadwal_id"); p.add_argument("pemesan"); p.add_argument("kursi", nargs="+")
    b = sp.add_parser("batal")
    b.add_argument("kode_booking"); b.add_argument("pemesan")
    sp.add_parser("pantau").add_argument("jadwal_id")
    a = ap.parse_args()

    k = KlienBioskop(a.host, on_retry=lambda n, p, c, j: print(f"  [retry] {n} percobaan {p} gagal ({c}), ulang {j:.2f}s"))
    try:
        if a.cmd == "jadwal":
            for j in k.list_jadwal().jadwal:
                print(f"{j.id:4s} {j.film:24s} {j.studio:11s} {j.waktu}  kosong {j.kursi_kosong}/{j.baris * j.kolom}")
        elif a.cmd == "peta":
            cetak_peta(k.peta(a.jadwal_id))
        elif a.cmd == "pesan":
            r = k.pesan_kursi(a.jadwal_id, a.pemesan, a.kursi)
            print(("BERHASIL " if r.sukses else "GAGAL ") + r.pesan,
                  f"| kode={r.kode_booking}" if r.sukses else "",
                  "(balasan dari cache dedup)" if r.duplikat else "")
        elif a.cmd == "batal":
            r = k.batalkan(a.kode_booking, a.pemesan)
            print(("BERHASIL " if r.sukses else "GAGAL ") + r.pesan, list(r.kursi_dilepas))
        elif a.cmd == "pantau":
            print("Memantau... (Ctrl+C untuk berhenti)")
            for e in k.pantau(a.jadwal_id):
                tag = "snapshot" if e.snapshot else f"#{e.seq}"
                if e.snapshot and e.kursi.status == pb.KOSONG:
                    continue
                status = f"TERISI oleh {e.kursi.pemesan}" if e.kursi.status == pb.TERISI else "KOSONG"
                print(f"[{tag}] {e.kursi.kode} -> {status}")
    except grpc.RpcError as e:
        print("Error:", e.code().name, "-", e.details())
    except KeyboardInterrupt:
        pass
    finally:
        k.tutup()


if __name__ == "__main__":
    main()
