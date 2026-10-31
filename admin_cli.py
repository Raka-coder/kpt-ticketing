"""CLI Menu Admin Bioskop.

Jalankan:
  python admin_cli.py
  python admin_cli.py --host localhost:50051

Pastikan server sudah berjalan: python server.py
Pastikan akun admin sudah dibuat: python admin_auth.py --setup
"""
import argparse
import getpass
import os
import sys

import grpc

import admin_pb2 as apb
import admin_pb2_grpc as apb_grpc
from klien import KlienBioskop   # reuse untuk list_jadwal & peta (baca saja)

# ─── Konstanta tampilan ───────────────────────────────────────────────────────

_LEBAR = 44
_JUDUL = "BIOSKOP TICKETING SYSTEM"
_LINE  = "=" * _LEBAR


def _header(subjudul: str = "") -> None:
    print(_LINE)
    print(f"{_JUDUL:^{_LEBAR}}")
    print(_LINE)
    if subjudul:
        print(f"{subjudul:^{_LEBAR}}")
        print(_LINE)


def _jeda() -> None:
    input("\nTekan Enter untuk melanjutkan...")


def _bersih() -> None:
    os.system("cls" if os.name == "nt" else "clear")


# ─── Koneksi ─────────────────────────────────────────────────────────────────

class KoneksiAdmin:
    """Wrapper tipis di atas stub gRPC admin."""

    def __init__(self, target: str):
        self._channel = grpc.insecure_channel(target)
        self._stub    = apb_grpc.LayananAdminStub(self._channel)
        self.token    = ""

    def tutup(self):
        self._channel.close()

    # Auth
    def login(self, username: str, password: str) -> apb.LoginResponse:
        return self._stub.LoginAdmin(apb.LoginRequest(username=username, password=password), timeout=5)

    def logout_rpc(self) -> None:
        """Logout di sisi client (token dihapus dari memory server via admin_auth)."""
        # Tidak ada RPC logout; cukup hapus token lokal dan panggil admin_auth.logout
        pass

    # Dashboard
    def dashboard(self) -> apb.DashboardResponse:
        return self._stub.GetDashboard(apb.AdminRequest(token=self.token), timeout=5)

    # Jadwal
    def tambah_jadwal(self, id, film, studio, waktu, baris, kolom) -> apb.AdminResponse:
        return self._stub.TambahJadwal(apb.TambahJadwalRequest(
            token=self.token, id=id, film=film, studio=studio,
            waktu=waktu, baris=baris, kolom=kolom,
        ), timeout=5)

    def ubah_jadwal(self, jadwal_id, film="", studio="", waktu="") -> apb.AdminResponse:
        return self._stub.UbahJadwal(apb.UbahJadwalRequest(
            token=self.token, jadwal_id=jadwal_id,
            film=film, studio=studio, waktu=waktu,
        ), timeout=5)

    def hapus_jadwal(self, jadwal_id) -> apb.AdminResponse:
        return self._stub.HapusJadwal(apb.HapusJadwalRequest(
            token=self.token, jadwal_id=jadwal_id,
        ), timeout=5)

    # Pesanan
    def list_pesanan(self, jadwal_id="") -> apb.ListPesananResponse:
        return self._stub.ListSemuaPesanan(apb.ListPesananRequest(
            token=self.token, jadwal_id=jadwal_id,
        ), timeout=5)

    def detail_transaksi(self, kode_booking) -> apb.DetailTransaksiResponse:
        return self._stub.GetDetailTransaksi(apb.DetailTransaksiRequest(
            token=self.token, kode_booking=kode_booking,
        ), timeout=5)


# ─── Layar-layar menu ─────────────────────────────────────────────────────────

def layar_login(adm: KoneksiAdmin) -> bool:
    _bersih()
    _header("LOGIN ADMIN")
    print()
    username = input("  Username : ").strip()
    password = getpass.getpass("  Password : ")
    try:
        resp = adm.login(username, password)
    except grpc.RpcError as e:
        print(f"\n  [Error] {e.code().name}: {e.details()}")
        _jeda()
        return False
    if resp.sukses:
        adm.token = resp.token
        print(f"\n  ✓ {resp.pesan}")
        _jeda()
        return True
    else:
        print(f"\n  ✗ {resp.pesan}")
        _jeda()
        return False


def layar_dashboard(adm: KoneksiAdmin) -> None:
    _bersih()
    _header("DASHBOARD ADMIN")
    try:
        d = adm.dashboard()
    except grpc.RpcError as e:
        print(f"  [Error] {e.code().name}: {e.details()}")
        _jeda()
        return

    print(f"\n  Total Jadwal      : {d.total_jadwal}")
    print(f"  Total Pesanan Aktif : {d.total_pesanan_aktif}")
    print(f"  Total Kursi Terisi  : {d.total_kursi_terisi}")
    print(f"  Total Kursi Kosong  : {d.total_kursi_kosong}")
    print()
    print(f"  {'ID':<6} {'Film':<24} {'Terisi':>6} {'Kosong':>6} {'Pesanan':>7}")
    print("  " + "-" * 52)
    for s in d.statistik:
        print(f"  {s.jadwal_id:<6} {s.film:<24} {s.kursi_terisi:>6} "
              f"{s.kursi_kosong:>6} {s.total_pesanan:>7}")
    _jeda()


def layar_semua_jadwal(klien_biasa: KlienBioskop) -> None:
    _bersih()
    _header("SELURUH JADWAL FILM")
    try:
        resp = klien_biasa.list_jadwal()
    except grpc.RpcError as e:
        print(f"  [Error] {e.code().name}: {e.details()}")
        _jeda()
        return
    print()
    print(f"  {'ID':<6} {'Film':<26} {'Studio':<12} {'Waktu':<18} {'Kosong':>6}")
    print("  " + "-" * 72)
    for j in resp.jadwal:
        total = j.baris * j.kolom
        print(f"  {j.id:<6} {j.film:<26} {j.studio:<12} {j.waktu:<18} "
              f"{j.kursi_kosong:>3}/{total}")
    _jeda()


def layar_peta_kursi(klien_biasa: KlienBioskop) -> None:
    import bioskop_pb2 as pb
    _bersih()
    _header("PETA KURSI JADWAL")
    jadwal_id = input("\n  Masukkan ID Jadwal: ").strip()
    if not jadwal_id:
        return
    try:
        peta = klien_biasa.peta(jadwal_id)
    except grpc.RpcError as e:
        print(f"\n  [Error] {e.code().name}: {e.details()}")
        _jeda()
        return
    j = peta.jadwal
    print(f"\n  {j.id} | {j.film} | {j.studio} | {j.waktu}")
    print(f"  Kursi kosong: {j.kursi_kosong}/{j.baris * j.kolom}")
    print("\n         ====== LAYAR ======")
    baris: dict = {}
    for k in peta.kursi:
        baris.setdefault(k.kode[0], []).append(k)
    for huruf, ks in baris.items():
        row = " ".join("[X]" if k.status == pb.TERISI else "[ ]" for k in ks)
        pemesan_info = ", ".join(
            f"{k.kode}:{k.pemesan}" for k in ks if k.status == pb.TERISI
        )
        print(f"  {huruf:>2}  {row}")
        if pemesan_info:
            print(f"       ({pemesan_info})")
    print("\n  [ ] kosong   [X] terisi")
    _jeda()


def layar_daftar_pesanan(adm: KoneksiAdmin) -> None:
    _bersih()
    _header("DAFTAR SELURUH PESANAN")
    filter_id = input("\n  Filter Jadwal ID (kosong = semua): ").strip()
    try:
        resp = adm.list_pesanan(filter_id)
    except grpc.RpcError as e:
        print(f"\n  [Error] {e.code().name}: {e.details()}")
        _jeda()
        return
    if not resp.pesanan:
        print("\n  Tidak ada pesanan ditemukan.")
        _jeda()
        return
    print()
    print(f"  {'Kode Booking':<14} {'Jadwal':<8} {'Film':<20} {'Pemesan':<14} {'Status':<8} Kursi")
    print("  " + "-" * 80)
    for p in resp.pesanan:
        status = "AKTIF " if p.aktif else "BATAL "
        kursi_str = ", ".join(p.kursi)
        print(f"  {p.kode_booking:<14} {p.jadwal_id:<8} {p.film:<20} "
              f"{p.pemesan:<14} {status:<8} {kursi_str}")
    print(f"\n  Total: {len(resp.pesanan)} pesanan")
    _jeda()


def layar_detail_transaksi(adm: KoneksiAdmin) -> None:
    _bersih()
    _header("DETAIL TRANSAKSI")
    kode = input("\n  Masukkan Kode Booking: ").strip()
    if not kode:
        return
    try:
        resp = adm.detail_transaksi(kode)
    except grpc.RpcError as e:
        print(f"\n  [Error] {e.code().name}: {e.details()}")
        _jeda()
        return
    if not resp.sukses:
        print(f"\n  ✗ {resp.pesan}")
        _jeda()
        return
    p = resp.pesanan
    print(f"\n  Kode Booking : {p.kode_booking}")
    print(f"  Jadwal ID    : {p.jadwal_id}")
    print(f"  Film         : {p.film}")
    print(f"  Pemesan      : {p.pemesan}")
    print(f"  Kursi        : {', '.join(p.kursi)}")
    print(f"  Status       : {'AKTIF' if p.aktif else 'DIBATALKAN'}")
    _jeda()


# ─── Submenu Kelola Jadwal ────────────────────────────────────────────────────

def submenu_tambah_jadwal(adm: KoneksiAdmin) -> None:
    _bersih()
    _header("TAMBAH JADWAL BARU")
    print()
    id_jadwal = input("  ID Jadwal (contoh: J5) : ").strip()
    film      = input("  Nama Film              : ").strip()
    studio    = input("  Studio                 : ").strip()
    waktu     = input("  Waktu (YYYY-MM-DD HH:MM): ").strip()
    try:
        baris = int(input("  Jumlah Baris (1-26)   : ").strip())
        kolom = int(input("  Jumlah Kolom (1-50)   : ").strip())
    except ValueError:
        print("\n  ✗ Baris/Kolom harus berupa angka.")
        _jeda()
        return
    try:
        resp = adm.tambah_jadwal(id_jadwal, film, studio, waktu, baris, kolom)
    except grpc.RpcError as e:
        print(f"\n  [Error] {e.code().name}: {e.details()}")
        _jeda()
        return
    ikon = "✓" if resp.sukses else "✗"
    print(f"\n  {ikon} {resp.pesan}")
    _jeda()


def submenu_ubah_jadwal(adm: KoneksiAdmin) -> None:
    _bersih()
    _header("UBAH INFORMASI JADWAL")
    print()
    jadwal_id = input("  ID Jadwal yang akan diubah: ").strip()
    print("  (Kosongkan field yang tidak ingin diubah)")
    film   = input("  Nama Film baru  : ").strip()
    studio = input("  Studio baru     : ").strip()
    waktu  = input("  Waktu baru      : ").strip()
    try:
        resp = adm.ubah_jadwal(jadwal_id, film, studio, waktu)
    except grpc.RpcError as e:
        print(f"\n  [Error] {e.code().name}: {e.details()}")
        _jeda()
        return
    ikon = "✓" if resp.sukses else "✗"
    print(f"\n  {ikon} {resp.pesan}")
    _jeda()


def submenu_hapus_jadwal(adm: KoneksiAdmin) -> None:
    _bersih()
    _header("HAPUS JADWAL FILM")
    print()
    jadwal_id = input("  ID Jadwal yang akan dihapus: ").strip()
    konfirmasi = input(f"  Yakin hapus jadwal '{jadwal_id}'? (ketik 'ya' untuk konfirmasi): ").strip().lower()
    if konfirmasi != "ya":
        print("\n  Penghapusan dibatalkan.")
        _jeda()
        return
    try:
        resp = adm.hapus_jadwal(jadwal_id)
    except grpc.RpcError as e:
        print(f"\n  [Error] {e.code().name}: {e.details()}")
        _jeda()
        return
    ikon = "✓" if resp.sukses else "✗"
    print(f"\n  {ikon} {resp.pesan}")
    _jeda()


def submenu_kelola_jadwal(adm: KoneksiAdmin, klien_biasa: KlienBioskop) -> None:
    while True:
        _bersih()
        _header("KELOLA JADWAL FILM")
        print()
        print("  1. Lihat Semua Jadwal")
        print("  2. Tambah Jadwal Baru")
        print("  3. Ubah Informasi Jadwal")
        print("  4. Hapus Jadwal")
        print("  5. Kembali ke Menu Utama")
        print(_LINE)
        pilih = input("  Pilih menu [1-5]: ").strip()
        if pilih == "1":
            layar_semua_jadwal(klien_biasa)
        elif pilih == "2":
            submenu_tambah_jadwal(adm)
        elif pilih == "3":
            submenu_ubah_jadwal(adm)
        elif pilih == "4":
            submenu_hapus_jadwal(adm)
        elif pilih == "5":
            break
        else:
            print("  Pilihan tidak valid.")


# ─── Menu Utama Admin ─────────────────────────────────────────────────────────

def menu_utama(adm: KoneksiAdmin, klien_biasa: KlienBioskop) -> None:
    while True:
        _bersih()
        _header("ADMIN MENU")
        print()
        print("  1. Dashboard")
        print("  2. Kelola Jadwal Film")
        print("  3. Daftar Seluruh Pesanan")
        print("  4. Peta & Status Kursi")
        print("  5. Detail Transaksi")
        print("  6. Logout")
        print(_LINE)
        pilih = input("  Pilih menu [1-6]: ").strip()

        if pilih == "1":
            layar_dashboard(adm)
        elif pilih == "2":
            submenu_kelola_jadwal(adm, klien_biasa)
        elif pilih == "3":
            layar_daftar_pesanan(adm)
        elif pilih == "4":
            layar_peta_kursi(klien_biasa)
        elif pilih == "5":
            layar_detail_transaksi(adm)
        elif pilih == "6":
            import admin_auth
            admin_auth.logout(adm.token)
            adm.token = ""
            print("\n  Anda telah logout.")
            break
        else:
            print("  Pilihan tidak valid.")


# ─── Entry point ─────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    ap.add_argument("--host", default="localhost:50051",
                    help="Alamat server gRPC (default: localhost:50051)")
    a = ap.parse_args()

    # Cek apakah config admin sudah ada
    import admin_auth
    if not admin_auth.config_ada():
        print(_LINE)
        print("  PERINGATAN: Belum ada akun admin yang dibuat.")
        print("  Jalankan terlebih dahulu:")
        print("    python admin_auth.py --setup")
        print(_LINE)
        sys.exit(1)

    adm = KoneksiAdmin(a.host)
    klien_biasa = KlienBioskop(a.host)
    try:
        # Loop login
        while True:
            _bersih()
            _header("LOGIN ADMIN")
            if layar_login(adm):
                menu_utama(adm, klien_biasa)
                # Setelah logout kembali ke layar login
                lanjut = input("\n  Login kembali? (y/n): ").strip().lower()
                if lanjut != "y":
                    break
            else:
                lanjut = input("\n  Coba lagi? (y/n): ").strip().lower()
                if lanjut != "y":
                    break
    except KeyboardInterrupt:
        print("\n\n  Program dihentikan.")
    finally:
        adm.tutup()
        klien_biasa.tutup()


if __name__ == "__main__":
    main()
