"""Logika bisnis reservasi tiket bioskop (murni Python, tanpa dependensi gRPC).

Strategi concurrency
--------------------
* Satu Condition (berisi RLock) per jadwal tayang -> lock granular: pemesanan pada
  jadwal berbeda tidak saling menunggu, pemesanan pada jadwal yang sama diserialkan.
* Pengecekan kursi + penulisan + pencatatan hasil deduplikasi dilakukan dalam SATU
  critical section sehingga atomik (tidak ada celah check-then-act).
* Pemesanan banyak kursi bersifat semua-atau-tidak-sama-sekali.
* Condition yang sama dipakai untuk membangunkan stream pemantau saat ada perubahan.

Toleransi kegagalan
-------------------
* Operasi tidak idempoten (pesan, batal) memerlukan request_id. Hasil setiap request_id
  disimpan; permintaan ulang dengan ID sama mengembalikan hasil lama tanpa eksekusi
  ulang (at-most-once). Opsional: state disimpan ke berkas JSON (write-before-reply)
  sehingga jaminan tetap berlaku setelah server restart.
"""
import contextlib
import copy
import json
import os
import random
import threading
import time

MAKS_KURSI_PER_PESANAN = 6


class JadwalTidakAda(Exception):
    pass


class InputTidakValid(Exception):
    pass


def _buat_kursi(baris, kolom):
    return {f"{chr(65 + b)}{k + 1}": "" for b in range(baris) for k in range(kolom)}


class Jadwal:
    def __init__(self, id, film, studio, waktu, baris, kolom):
        self.id, self.film, self.studio, self.waktu = id, film, studio, waktu
        self.baris, self.kolom = baris, kolom
        self.kursi = _buat_kursi(baris, kolom)   # kode -> nama pemesan ("" = kosong)
        self.cond = threading.Condition()        # RLock di dalamnya
        self.events = []                         # (seq, kode, pemesan)
        self.hasil = {}                          # request_id -> (signature, hasil)
        self.pesanan = {}                        # kode_booking -> {pemesan, kursi, aktif}
        self.counter = 0

    def info(self):  # panggil di dalam lock
        return dict(id=self.id, film=self.film, studio=self.studio, waktu=self.waktu,
                    baris=self.baris, kolom=self.kolom,
                    kursi_kosong=sum(1 for v in self.kursi.values() if not v))


JADWAL_AWAL = [
    ("J1", "Petualangan Si Kancil", "Studio 1", "2026-11-07 19:00", 8, 10),
    ("J2", "Misteri Kota Tua", "Studio 2", "2026-11-07 21:00", 8, 10),
    ("J3", "Galaksi Terakhir", "Studio 3", "2026-11-08 14:00", 6, 8),
    ("J9", "Jadwal Uji Beban", "Studio Uji", "2026-12-31 00:00", 26, 30),
]


class StoreBioskop:
    def __init__(self, jadwal=JADWAL_AWAL, state_file=None, tanpa_lock=False, simulasi_beban=False, simulasi_durasi=(0.2, 0.5)):
        self._jadwal = {j[0]: Jadwal(*j) for j in jadwal}
        self.state_file = state_file
        self.tanpa_lock = tanpa_lock            # HANYA untuk demo race condition
        self.simulasi_beban = simulasi_beban    # Simulasi beban komputasi paralel/validasi gateway
        self.simulasi_durasi = simulasi_durasi
        self._persist_lock = threading.Lock()
        if state_file and os.path.exists(state_file):
            self._muat()

    # ---------------------------------------------------------------- util
    def _get(self, jadwal_id):
        j = self._jadwal.get(jadwal_id)
        if j is None:
            raise JadwalTidakAda(f"Jadwal '{jadwal_id}' tidak ditemukan")
        return j

    def _guard(self, j):
        return contextlib.nullcontext() if self.tanpa_lock else j.cond

    def _catat(self, j, perubahan):
        with j.cond:
            for kode, pemesan in perubahan:
                j.events.append((len(j.events) + 1, kode, pemesan))
            j.cond.notify_all()

    # --------------------------------------------------------------- baca
    def list_jadwal(self):
        hasil = []
        for j in self._jadwal.values():
            with j.cond:
                hasil.append(j.info())
        return hasil

    def peta(self, jadwal_id):
        j = self._get(jadwal_id)
        with j.cond:
            return j.info(), list(j.kursi.items())

    # -------------------------------------------------------------- tulis
    def pesan(self, request_id, jadwal_id, pemesan, kursi):
        if not request_id:
            raise InputTidakValid("request_id wajib diisi")
        if not pemesan or not pemesan.strip():
            raise InputTidakValid("Nama pemesan wajib diisi")
        kursi = list(kursi)
        if not kursi:
            raise InputTidakValid("Pilih minimal satu kursi")
        if len(set(kursi)) != len(kursi):
            raise InputTidakValid("Ada kursi ganda dalam satu permintaan")
        if len(kursi) > MAKS_KURSI_PER_PESANAN:
            raise InputTidakValid(f"Maksimal {MAKS_KURSI_PER_PESANAN} kursi per pesanan")
        j = self._get(jadwal_id)
        asing = [k for k in kursi if k not in j.kursi]   # kunci dict tidak pernah berubah
        if asing:
            raise InputTidakValid("Kode kursi tidak dikenal: " + ", ".join(asing))
        sig = ["pesan", jadwal_id, pemesan, sorted(kursi)]

        with self._guard(j):
            if request_id in j.hasil:
                sig_lama, hasil = j.hasil[request_id]
                if sig_lama != sig:
                    raise InputTidakValid("request_id sudah dipakai untuk permintaan lain")
                return dict(hasil, duplikat=True)
            gagal = [k for k in kursi if j.kursi[k]]
            if self.tanpa_lock:
                time.sleep(0.001)   # melebarkan celah race agar mudah didemokan
            if gagal:
                hasil = dict(sukses=False, pesan="Kursi sudah terisi: " + ", ".join(gagal),
                             kode_booking="", kursi_dipesan=[], kursi_gagal=gagal,
                             duplikat=False)
            else:
                # SIMULASI BEBAN VALIDASI PEMBAYARAN (Wajib untuk Skenario A Komputasi Paralel)
                # Merepresentasikan komunikasi eksternal / verifikasi payment gateway
                if self.simulasi_beban:
                    time.sleep(random.uniform(*self.simulasi_durasi))

                j.counter += 1
                kode = f"{j.id}-{j.counter:04d}"
                for k in kursi:
                    j.kursi[k] = pemesan
                j.pesanan[kode] = dict(pemesan=pemesan, kursi=list(kursi), aktif=True)
                self._catat(j, [(k, pemesan) for k in kursi])
                hasil = dict(sukses=True, pesan="Pemesanan berhasil", kode_booking=kode,
                             kursi_dipesan=list(kursi), kursi_gagal=[], duplikat=False)
            j.hasil[request_id] = (sig, hasil)
        self._simpan()
        return dict(hasil)

    def batal(self, request_id, kode_booking, pemesan):
        if not request_id:
            raise InputTidakValid("request_id wajib diisi")
        if not pemesan or not pemesan.strip():
            raise InputTidakValid("Nama pemesan wajib diisi")
        if "-" not in kode_booking:
            raise InputTidakValid("Format kode booking tidak valid")
        j = self._get(kode_booking.rsplit("-", 1)[0])
        sig = ["batal", kode_booking, pemesan]

        with self._guard(j):
            if request_id in j.hasil:
                sig_lama, hasil = j.hasil[request_id]
                if sig_lama != sig:
                    raise InputTidakValid("request_id sudah dipakai untuk permintaan lain")
                return dict(hasil, duplikat=True)
            p = j.pesanan.get(kode_booking)
            if p is None:
                hasil = dict(sukses=False, pesan="Kode booking tidak ditemukan",
                             kursi_dilepas=[], duplikat=False)
            elif p["pemesan"] != pemesan:
                hasil = dict(sukses=False, pesan="Anda bukan pemilik pesanan ini",
                             kursi_dilepas=[], duplikat=False)
            elif not p["aktif"]:
                hasil = dict(sukses=False, pesan="Pesanan sudah dibatalkan",
                             kursi_dilepas=[], duplikat=False)
            else:
                for k in p["kursi"]:
                    j.kursi[k] = ""
                p["aktif"] = False
                self._catat(j, [(k, "") for k in p["kursi"]])
                hasil = dict(sukses=True, pesan="Pesanan dibatalkan",
                             kursi_dilepas=list(p["kursi"]), duplikat=False)
            j.hasil[request_id] = (sig, hasil)
        self._simpan()
        return dict(hasil)

    # ------------------------------------------------------------- stream
    def ikuti(self, jadwal_id, aktif=lambda: True, tunggu=1.0):
        """Generator: (seq, kode, pemesan, snapshot). Snapshot dulu, lalu perubahan baru."""
        j = self._get(jadwal_id)
        with j.cond:
            snapshot = list(j.kursi.items())
            terakhir = len(j.events)
        for kode, pemesan in snapshot:
            yield (0, kode, pemesan, True)
        while aktif():
            with j.cond:
                if len(j.events) <= terakhir:
                    j.cond.wait(timeout=tunggu)
                baru = j.events[terakhir:]
                terakhir = len(j.events)
            for seq, kode, pemesan in baru:
                yield (seq, kode, pemesan, False)

    # ---------------------------------------------------------- persisten
    def _simpan(self):
        if not self.state_file:
            return
        with self._persist_lock:
            data = {}
            for jid, j in self._jadwal.items():
                with j.cond:
                    data[jid] = dict(
                        kursi=dict(j.kursi),
                        hasil={r: [s, h] for r, (s, h) in j.hasil.items()},
                        pesanan=copy.deepcopy(j.pesanan),
                        counter=j.counter)
            tmp = self.state_file + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, self.state_file)

    def _muat(self):
        with open(self.state_file, encoding="utf-8") as f:
            data = json.load(f)
        for jid, d in data.items():
            j = self._jadwal.get(jid)
            if j is None:
                continue
            j.kursi.update(d["kursi"])
            j.hasil = {r: (s, h) for r, (s, h) in d["hasil"].items()}
            j.pesanan = d["pesanan"]
            j.counter = d["counter"]
