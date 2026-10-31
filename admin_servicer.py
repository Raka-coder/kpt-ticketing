"""Servicer gRPC untuk LayananAdmin.

Didaftarkan ke server gRPC yang sama dengan LayananBioskop (port 50051).
Seluruh operasi tulis dilindungi verifikasi token admin.
"""
import grpc

import admin_pb2 as apb
import admin_pb2_grpc as apb_grpc
import admin_auth as auth
import admin_logika as al
from logika import StoreBioskop, JadwalTidakAda, InputTidakValid


class LayananAdminServicer(apb_grpc.LayananAdminServicer):
    """Implementasi semua RPC admin."""

    def __init__(self, store: StoreBioskop):
        self.store = store

    # ─── Helper ──────────────────────────────────────────────────────────────

    @staticmethod
    def _tolak(context, pesan: str,
               kode: grpc.StatusCode = grpc.StatusCode.PERMISSION_DENIED):
        context.abort(kode, pesan)

    def _cek_token(self, token: str, context) -> bool:
        if not auth.verifikasi_token(token):
            self._tolak(context, "Token tidak valid atau sesi telah kedaluwarsa. Silakan login ulang.")
            return False
        return True

    # ─── Autentikasi ─────────────────────────────────────────────────────────

    def LoginAdmin(self, request, context):
        sukses, hasil = auth.login(request.username, request.password)
        if sukses:
            return apb.LoginResponse(sukses=True, pesan="Login berhasil", token=hasil)
        return apb.LoginResponse(sukses=False, pesan=hasil, token="")

    # ─── Dashboard ───────────────────────────────────────────────────────────

    def GetDashboard(self, request, context):
        if not self._cek_token(request.token, context):
            return
        data = al.get_statistik(self.store)
        stats = [
            apb.StatistikJadwal(**s) for s in data["statistik"]
        ]
        return apb.DashboardResponse(
            sukses=True, pesan="",
            total_jadwal=data["total_jadwal"],
            total_pesanan_aktif=data["total_pesanan_aktif"],
            total_kursi_terisi=data["total_kursi_terisi"],
            total_kursi_kosong=data["total_kursi_kosong"],
            statistik=stats,
        )

    # ─── Manajemen Jadwal ─────────────────────────────────────────────────────

    def TambahJadwal(self, request, context):
        if not self._cek_token(request.token, context):
            return
        try:
            h = al.tambah_jadwal(
                self.store, request.id, request.film,
                request.studio, request.waktu,
                request.baris, request.kolom,
            )
        except (InputTidakValid, JadwalTidakAda) as e:
            return apb.AdminResponse(sukses=False, pesan=str(e))
        return apb.AdminResponse(**h)

    def UbahJadwal(self, request, context):
        if not self._cek_token(request.token, context):
            return
        try:
            h = al.ubah_jadwal(
                self.store, request.jadwal_id,
                request.film, request.studio, request.waktu,
            )
        except (InputTidakValid, JadwalTidakAda) as e:
            return apb.AdminResponse(sukses=False, pesan=str(e))
        return apb.AdminResponse(**h)

    def HapusJadwal(self, request, context):
        if not self._cek_token(request.token, context):
            return
        try:
            h = al.hapus_jadwal(self.store, request.jadwal_id)
        except (InputTidakValid, JadwalTidakAda) as e:
            return apb.AdminResponse(sukses=False, pesan=str(e))
        return apb.AdminResponse(**h)

    # ─── Pemesanan ────────────────────────────────────────────────────────────

    def ListSemuaPesanan(self, request, context):
        if not self._cek_token(request.token, context):
            return
        pesanan = al.list_semua_pesanan(self.store, request.jadwal_id)
        return apb.ListPesananResponse(
            sukses=True, pesan="",
            pesanan=[apb.InfoPesanan(**p) for p in pesanan],
        )

    def GetDetailTransaksi(self, request, context):
        if not self._cek_token(request.token, context):
            return
        p = al.get_detail_transaksi(self.store, request.kode_booking)
        if p is None:
            return apb.DetailTransaksiResponse(
                sukses=False, pesan=f"Kode booking '{request.kode_booking}' tidak ditemukan"
            )
        return apb.DetailTransaksiResponse(sukses=True, pesan="", pesanan=apb.InfoPesanan(**p))
