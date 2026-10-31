"""Package admin untuk sistem reservasi bioskop gRPC.
Menyediakan modul autentikasi (auth), logika bisnis admin (logika), dan gRPC servicer (servicer).
"""
from admin.auth import setup_admin, login, logout, verifikasi_token, config_ada
from admin.logika import (
    tambah_jadwal,
    ubah_jadwal,
    hapus_jadwal,
    list_semua_pesanan,
    get_detail_transaksi,
    get_statistik,
)
from admin.servicer import LayananAdminServicer

__all__ = [
    "setup_admin",
    "login",
    "logout",
    "verifikasi_token",
    "config_ada",
    "tambah_jadwal",
    "ubah_jadwal",
    "hapus_jadwal",
    "list_semua_pesanan",
    "get_detail_transaksi",
    "get_statistik",
    "LayananAdminServicer",
]
