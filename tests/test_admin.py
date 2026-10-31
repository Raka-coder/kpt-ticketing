"""Uji unit fitur admin (tanpa gRPC, langsung ke logika & auth).

Jalankan: python -m unittest discover -s tests -v
"""
import os
import sys
import tempfile
import threading
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from logika import StoreBioskop, InputTidakValid, JadwalTidakAda
import admin.logika as al
import admin.auth as admin_auth


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _store():
    """StoreBioskop baru (in-memory, tanpa file state)."""
    return StoreBioskop()


# ─── Test: admin_auth ────────────────────────────────────────────────────────

class TesAdminAuth(unittest.TestCase):

    def setUp(self):
        # Gunakan file konfigurasi sementara agar tidak mengganggu konfigurasi nyata
        self._tmpdir = tempfile.TemporaryDirectory()
        self._orig_config = admin_auth._CONFIG_FILE
        admin_auth._CONFIG_FILE = os.path.join(self._tmpdir.name, ".admin_config.json")
        admin_auth._sessions.clear()

    def tearDown(self):
        admin_auth._CONFIG_FILE = self._orig_config
        admin_auth._sessions.clear()
        self._tmpdir.cleanup()

    def test_setup_dan_login_berhasil(self):
        admin_auth.setup_admin("admin", "rahasia123")
        sukses, token = admin_auth.login("admin", "rahasia123")
        self.assertTrue(sukses)
        self.assertTrue(len(token) > 0)

    def test_login_password_salah(self):
        admin_auth.setup_admin("admin", "rahasia123")
        sukses, pesan = admin_auth.login("admin", "salah")
        self.assertFalse(sukses)
        self.assertIn("Password", pesan)

    def test_login_username_tidak_ada(self):
        admin_auth.setup_admin("admin", "rahasia123")
        sukses, pesan = admin_auth.login("bukan_admin", "rahasia123")
        self.assertFalse(sukses)

    def test_verifikasi_token_valid(self):
        admin_auth.setup_admin("admin", "rahasia123")
        _, token = admin_auth.login("admin", "rahasia123")
        self.assertTrue(admin_auth.verifikasi_token(token))

    def test_verifikasi_token_tidak_valid(self):
        self.assertFalse(admin_auth.verifikasi_token("token_palsu"))

    def test_logout_menghapus_token(self):
        admin_auth.setup_admin("admin", "rahasia123")
        _, token = admin_auth.login("admin", "rahasia123")
        admin_auth.logout(token)
        self.assertFalse(admin_auth.verifikasi_token(token))

    def test_config_ada_false_sebelum_setup(self):
        self.assertFalse(admin_auth.config_ada())

    def test_config_ada_true_setelah_setup(self):
        admin_auth.setup_admin("admin", "rahasia123")
        self.assertTrue(admin_auth.config_ada())


# ─── Test: admin_logika - Jadwal ─────────────────────────────────────────────

class TesAdminTambahJadwal(unittest.TestCase):

    def test_tambah_jadwal_baru(self):
        s = _store()
        h = al.tambah_jadwal(s, "J99", "Film Baru", "Studio 9", "2027-01-01 10:00", 5, 8)
        self.assertTrue(h["sukses"])
        self.assertIn("J99", s._jadwal)

    def test_tambah_jadwal_id_duplikat(self):
        s = _store()
        with self.assertRaises(InputTidakValid):
            al.tambah_jadwal(s, "J1", "Duplikat", "Studio 1", "2027-01-01 10:00", 5, 8)

    def test_tambah_jadwal_validasi_baris(self):
        s = _store()
        with self.assertRaises(InputTidakValid):
            al.tambah_jadwal(s, "J99", "Film", "Studio", "2027-01-01", 0, 5)

    def test_tambah_jadwal_validasi_kolom(self):
        s = _store()
        with self.assertRaises(InputTidakValid):
            al.tambah_jadwal(s, "J99", "Film", "Studio", "2027-01-01", 5, 0)

    def test_tambah_jadwal_id_kosong(self):
        s = _store()
        with self.assertRaises(InputTidakValid):
            al.tambah_jadwal(s, "", "Film", "Studio", "2027-01-01", 5, 5)

    def test_tambah_jadwal_film_kosong(self):
        s = _store()
        with self.assertRaises(InputTidakValid):
            al.tambah_jadwal(s, "J99", "", "Studio", "2027-01-01", 5, 5)

    def test_jadwal_baru_punya_kursi_kosong(self):
        s = _store()
        al.tambah_jadwal(s, "J99", "Film", "Studio", "2027-01-01", 3, 4)
        info, kursi = s.peta("J99")
        self.assertEqual(info["kursi_kosong"], 12)
        self.assertEqual(len(kursi), 12)


class TesAdminUbahJadwal(unittest.TestCase):

    def test_ubah_film(self):
        s = _store()
        al.ubah_jadwal(s, "J1", film="Film Baru")
        self.assertEqual(s._jadwal["J1"].film, "Film Baru")

    def test_ubah_studio(self):
        s = _store()
        al.ubah_jadwal(s, "J1", studio="Studio X")
        self.assertEqual(s._jadwal["J1"].studio, "Studio X")

    def test_ubah_waktu(self):
        s = _store()
        al.ubah_jadwal(s, "J1", waktu="2028-12-31 23:00")
        self.assertEqual(s._jadwal["J1"].waktu, "2028-12-31 23:00")

    def test_ubah_tidak_merusak_kursi(self):
        s = _store()
        kode = s.pesan("r1", "J1", "andi", ["A1", "A2"])["kode_booking"]
        al.ubah_jadwal(s, "J1", film="Film Diubah")
        # Data kursi tetap aman
        self.assertEqual(s._jadwal["J1"].kursi["A1"], "andi")
        self.assertEqual(s._jadwal["J1"].pesanan[kode]["pemesan"], "andi")

    def test_ubah_jadwal_tidak_ada(self):
        s = _store()
        with self.assertRaises(JadwalTidakAda):
            al.ubah_jadwal(s, "J_TIDAK_ADA", film="Film")

    def test_ubah_tanpa_field(self):
        s = _store()
        with self.assertRaises(InputTidakValid):
            al.ubah_jadwal(s, "J1")


class TesAdminHapusJadwal(unittest.TestCase):

    def test_hapus_jadwal_kosong(self):
        s = _store()
        al.tambah_jadwal(s, "J_TMP", "Film", "Studio", "2027-01-01", 2, 2)
        h = al.hapus_jadwal(s, "J_TMP")
        self.assertTrue(h["sukses"])
        self.assertNotIn("J_TMP", s._jadwal)

    def test_hapus_jadwal_ada_pesanan_aktif(self):
        s = _store()
        s.pesan("r1", "J1", "andi", ["A1"])
        with self.assertRaises(InputTidakValid):
            al.hapus_jadwal(s, "J1")

    def test_hapus_jadwal_pesanan_dibatalkan_boleh_hapus(self):
        s = _store()
        al.tambah_jadwal(s, "J_TMP2", "Film", "Studio", "2027-01-01", 2, 2)
        kode = s.pesan("r1", "J_TMP2", "andi", ["A1"])["kode_booking"]
        s.batal("r2", kode, "andi")
        h = al.hapus_jadwal(s, "J_TMP2")
        self.assertTrue(h["sukses"])

    def test_hapus_jadwal_tidak_ada(self):
        s = _store()
        with self.assertRaises(JadwalTidakAda):
            al.hapus_jadwal(s, "J_TIDAK_ADA")


# ─── Test: admin_logika - Pesanan ────────────────────────────────────────────

class TesAdminPesanan(unittest.TestCase):

    def setUp(self):
        self.s = _store()
        self.s.pesan("r1", "J1", "andi", ["A1", "A2"])
        self.s.pesan("r2", "J2", "budi", ["B1"])
        kode = self.s.pesan("r3", "J1", "cici", ["A3"])["kode_booking"]
        self.s.batal("r4", kode, "cici")   # dibatalkan

    def test_list_semua_pesanan(self):
        hasil = al.list_semua_pesanan(self.s)
        self.assertGreaterEqual(len(hasil), 3)

    def test_list_pesanan_filter_jadwal(self):
        hasil = al.list_semua_pesanan(self.s, "J2")
        self.assertTrue(all(p["jadwal_id"] == "J2" for p in hasil))

    def test_list_pesanan_berisi_field_lengkap(self):
        hasil = al.list_semua_pesanan(self.s)
        for p in hasil:
            self.assertIn("kode_booking", p)
            self.assertIn("jadwal_id", p)
            self.assertIn("film", p)
            self.assertIn("pemesan", p)
            self.assertIn("kursi", p)
            self.assertIn("aktif", p)

    def test_detail_transaksi_ditemukan(self):
        kode = self.s.pesan("r5", "J1", "dedi", ["B1"])["kode_booking"]
        detail = al.get_detail_transaksi(self.s, kode)
        self.assertIsNotNone(detail)
        self.assertEqual(detail["pemesan"], "dedi")
        self.assertEqual(detail["kode_booking"], kode)

    def test_detail_transaksi_tidak_ditemukan(self):
        detail = al.get_detail_transaksi(self.s, "J1-9999")
        self.assertIsNone(detail)

    def test_detail_transaksi_format_salah(self):
        detail = al.get_detail_transaksi(self.s, "INVALID")
        self.assertIsNone(detail)


# ─── Test: admin_logika - Statistik ─────────────────────────────────────────

class TesAdminStatistik(unittest.TestCase):

    def test_statistik_semua_jadwal(self):
        s = _store()
        stat = al.get_statistik(s)
        self.assertIn("total_jadwal", stat)
        self.assertIn("statistik", stat)
        self.assertEqual(stat["total_jadwal"], len(s._jadwal))

    def test_statistik_kursi_setelah_pesan(self):
        s = _store()
        s.pesan("r1", "J1", "andi", ["A1", "A2", "A3"])
        stat = al.get_statistik(s)
        j1_stat = next(x for x in stat["statistik"] if x["jadwal_id"] == "J1")
        self.assertEqual(j1_stat["kursi_terisi"], 3)

    def test_statistik_pesanan_aktif(self):
        s = _store()
        kode = s.pesan("r1", "J1", "andi", ["A1"])["kode_booking"]
        s.batal("r2", kode, "andi")   # dibatalkan, tidak dihitung
        stat = al.get_statistik(s)
        self.assertEqual(stat["total_pesanan_aktif"], 0)

    def test_statistik_thread_safe(self):
        """Akses statistik dari banyak thread tidak menyebabkan error."""
        s = _store()
        errors = []

        def baca():
            try:
                al.get_statistik(s)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=baca) for _ in range(20)]
        [t.start() for t in threads]
        [t.join() for t in threads]
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
