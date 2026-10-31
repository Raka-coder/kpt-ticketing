"""Uji unit logika bisnis (tidak butuh gRPC): python -m unittest discover -s tests"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import random
import tempfile
import threading
import time
import unittest
import uuid

from logika import StoreBioskop, InputTidakValid, JadwalTidakAda


def serentak(n, fungsi):
    """Jalankan fungsi(i) di n thread sekaligus (dilepas bersamaan lewat Barrier)."""
    barrier = threading.Barrier(n)
    hasil = [None] * n

    def kerja(i):
        barrier.wait()
        hasil[i] = fungsi(i)

    ts = [threading.Thread(target=kerja, args=(i,)) for i in range(n)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    return hasil


class TesBioskop(unittest.TestCase):
    def test_race_satu_kursi_hanya_satu_pemenang(self):
        s = StoreBioskop()
        hasil = serentak(200, lambda i: s.pesan(str(uuid.uuid4()), "J1", f"user{i}", ["A1"]))
        menang = [i for i, h in enumerate(hasil) if h["sukses"]]
        self.assertEqual(len(menang), 1)
        _, kursi = s.peta("J1")
        self.assertEqual(dict(kursi)["A1"], f"user{menang[0]}")

    def test_tanpa_lock_terjadi_pemesanan_ganda(self):
        s = StoreBioskop(tanpa_lock=True)
        hasil = serentak(50, lambda i: s.pesan(str(uuid.uuid4()), "J1", f"user{i}", ["A1"]))
        self.assertGreater(sum(h["sukses"] for h in hasil), 1)   # bukti race condition

    def test_dedup_request_id_sama(self):
        s = StoreBioskop()
        h1 = s.pesan("r1", "J1", "andi", ["B2", "B3"])
        h2 = s.pesan("r1", "J1", "andi", ["B2", "B3"])
        self.assertTrue(h1["sukses"] and not h1["duplikat"])
        self.assertTrue(h2["sukses"] and h2["duplikat"])
        self.assertEqual(h1["kode_booking"], h2["kode_booking"])
        info, _ = s.peta("J1")
        self.assertEqual(info["kursi_kosong"], 78)

    def test_dedup_retry_serentak(self):
        s = StoreBioskop()
        hasil = serentak(30, lambda i: s.pesan("rid-sama", "J1", "andi", ["C1"]))
        self.assertEqual(len({h["kode_booking"] for h in hasil}), 1)
        self.assertEqual(sum(not h["duplikat"] for h in hasil), 1)

    def test_request_id_dipakai_untuk_permintaan_lain(self):
        s = StoreBioskop()
        s.pesan("r1", "J1", "andi", ["A1"])
        with self.assertRaises(InputTidakValid):
            s.pesan("r1", "J1", "andi", ["A2"])

    def test_semua_atau_tidak_sama_sekali(self):
        s = StoreBioskop()
        s.pesan("r1", "J1", "x", ["A1"])
        h = s.pesan("r2", "J1", "y", ["A1", "A2"])
        self.assertFalse(h["sukses"])
        self.assertEqual(h["kursi_gagal"], ["A1"])
        self.assertEqual(dict(s.peta("J1")[1])["A2"], "")

    def test_batal(self):
        s = StoreBioskop()
        kode = s.pesan("r1", "J1", "andi", ["A1", "A2"])["kode_booking"]
        self.assertFalse(s.batal("r2", kode, "budi")["sukses"])       # bukan pemilik
        self.assertTrue(s.batal("r3", kode, "andi")["sukses"])
        self.assertTrue(s.batal("r3", kode, "andi")["duplikat"])       # retry aman
        self.assertFalse(s.batal("r4", kode, "andi")["sukses"])        # sudah batal
        self.assertEqual(s.peta("J1")[0]["kursi_kosong"], 80)

    def test_input_tidak_valid(self):
        s = StoreBioskop()
        with self.assertRaises(InputTidakValid):
            s.pesan("", "J1", "a", ["A1"])
        with self.assertRaises(InputTidakValid):
            s.pesan("r", "J1", "a", ["Z99"])
        with self.assertRaises(JadwalTidakAda):
            s.pesan("r", "NONE", "a", ["A1"])

    def test_beban_acak_tidak_ada_kursi_ganda(self):
        s = StoreBioskop()
        semua = [k for k, _ in s.peta("J2")[1]]
        rnd = random.Random(1)
        pilihan = [rnd.sample(semua, 3) for _ in range(150)]
        hasil = serentak(150, lambda i: s.pesan(str(uuid.uuid4()), "J2", f"u{i}", pilihan[i]))
        terpakai = [k for h in hasil if h["sukses"] for k in h["kursi_dipesan"]]
        self.assertEqual(len(terpakai), len(set(terpakai)))            # tidak ada kursi ganda
        self.assertEqual(80 - s.peta("J2")[0]["kursi_kosong"], len(terpakai))

    def test_stream_snapshot_dan_perubahan(self):
        s = StoreBioskop()
        stop, diterima = threading.Event(), []

        def pemantau():
            for e in s.ikuti("J1", aktif=lambda: not stop.is_set(), tunggu=0.1):
                diterima.append(e)

        t = threading.Thread(target=pemantau)
        t.start()
        time.sleep(0.2)
        s.pesan("r1", "J1", "andi", ["A1", "A2"])
        for _ in range(50):
            if len(diterima) >= 82:
                break
            time.sleep(0.05)
        stop.set()
        t.join()
        self.assertEqual(sum(e[3] for e in diterima), 80)              # snapshot
        baru = [e for e in diterima if not e[3]]
        self.assertEqual([(e[1], e[2]) for e in baru], [("A1", "andi"), ("A2", "andi")])

    def test_persistensi_dedup_setelah_restart(self):
        with tempfile.TemporaryDirectory() as d:
            f = os.path.join(d, "state.json")
            s1 = StoreBioskop(state_file=f)
            kode = s1.pesan("r1", "J1", "andi", ["A1"])["kode_booking"]
            s2 = StoreBioskop(state_file=f)                            # "restart"
            h = s2.pesan("r1", "J1", "andi", ["A1"])
            self.assertTrue(h["duplikat"])
            self.assertEqual(h["kode_booking"], kode)
            self.assertEqual(dict(s2.peta("J1")[1])["A1"], "andi")


# --- Format pengujian pytest standar (sesuai instruksi Bagian 3 plan.md) ---
from concurrent.futures import ThreadPoolExecutor


def test_race_condition_kursi_sama():
    """Uji race condition standar menggunakan ThreadPoolExecutor (dijalankan via pytest atau test runner)."""
    sistem = StoreBioskop()
    results = []

    def booking(user):
        r = sistem.pesan(f"req-{user}", "J1", user, ["A1"])
        return r["sukses"]

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(booking, f"user{i}") for i in range(5)]
        results = [f.result() for f in futures]

    # Hanya 1 yang boleh True, sisanya False
    assert results.count(True) == 1
    assert results.count(False) == 4


if __name__ == "__main__":
    unittest.main()
