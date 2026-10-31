"""Ekstensi additive pada StoreBioskop untuk kebutuhan admin.

Modul ini TIDAK mengubah logika.py. Ia menyediakan fungsi-fungsi tambahan
yang bekerja pada instance StoreBioskop yang sudah ada dengan cara yang aman
(thread-safe, tidak merusak data pemesanan yang ada).
"""
import threading

from logika import Jadwal, StoreBioskop, InputTidakValid, JadwalTidakAda, _buat_kursi


# ─── Tambah / Ubah / Hapus Jadwal ────────────────────────────────────────────

def tambah_jadwal(store: StoreBioskop,
                  id: str, film: str, studio: str, waktu: str,
                  baris: int, kolom: int) -> dict:
    """Tambah jadwal baru ke store. Thread-safe via _persist_lock."""
    id = id.strip()
    if not id:
        raise InputTidakValid("ID jadwal tidak boleh kosong")
    if not film.strip():
        raise InputTidakValid("Nama film tidak boleh kosong")
    if not studio.strip():
        raise InputTidakValid("Nama studio tidak boleh kosong")
    if not waktu.strip():
        raise InputTidakValid("Waktu tidak boleh kosong")
    if baris < 1 or baris > 26:
        raise InputTidakValid("Jumlah baris harus antara 1–26")
    if kolom < 1 or kolom > 50:
        raise InputTidakValid("Jumlah kolom harus antara 1–50")

    with store._persist_lock:
        if id in store._jadwal:
            raise InputTidakValid(f"Jadwal dengan ID '{id}' sudah ada")
        j = Jadwal(id, film.strip(), studio.strip(), waktu.strip(), baris, kolom)
        store._jadwal[id] = j

    store._simpan()
    return {"sukses": True, "pesan": f"Jadwal '{id}' berhasil ditambahkan"}


def ubah_jadwal(store: StoreBioskop, jadwal_id: str,
                film: str = "", studio: str = "", waktu: str = "") -> dict:
    """Ubah metadata jadwal (film/studio/waktu). Tidak mengubah data kursi/pesanan."""
    j = store._get(jadwal_id)   # raise JadwalTidakAda jika tidak ada

    if not film.strip() and not studio.strip() and not waktu.strip():
        raise InputTidakValid("Tidak ada field yang diubah")

    with j.cond:
        if film.strip():
            j.film = film.strip()
        if studio.strip():
            j.studio = studio.strip()
        if waktu.strip():
            j.waktu = waktu.strip()

    store._simpan()
    return {"sukses": True, "pesan": f"Jadwal '{jadwal_id}' berhasil diperbarui"}


def hapus_jadwal(store: StoreBioskop, jadwal_id: str) -> dict:
    """Hapus jadwal. Ditolak jika masih ada pesanan aktif."""
    j = store._get(jadwal_id)

    with j.cond:
        pesanan_aktif = [k for k, p in j.pesanan.items() if p.get("aktif")]
        if pesanan_aktif:
            raise InputTidakValid(
                f"Jadwal '{jadwal_id}' masih memiliki {len(pesanan_aktif)} pesanan aktif. "
                "Batalkan semua pesanan terlebih dahulu."
            )

    with store._persist_lock:
        store._jadwal.pop(jadwal_id, None)

    store._simpan()
    return {"sukses": True, "pesan": f"Jadwal '{jadwal_id}' berhasil dihapus"}


# ─── Data Pemesanan ───────────────────────────────────────────────────────────

def list_semua_pesanan(store: StoreBioskop, jadwal_id: str = "") -> list[dict]:
    """Kembalikan semua pesanan; saring per jadwal jika jadwal_id diisi."""
    hasil = []
    for jid, j in store._jadwal.items():
        if jadwal_id and jid != jadwal_id:
            continue
        with j.cond:
            for kode, p in j.pesanan.items():
                hasil.append(dict(
                    kode_booking=kode,
                    jadwal_id=jid,
                    film=j.film,
                    pemesan=p["pemesan"],
                    kursi=list(p["kursi"]),
                    aktif=p["aktif"],
                ))
    return hasil


def get_detail_transaksi(store: StoreBioskop, kode_booking: str) -> dict | None:
    """Kembalikan detail satu transaksi, atau None jika tidak ditemukan."""
    if "-" not in kode_booking:
        return None
    jadwal_id = kode_booking.rsplit("-", 1)[0]
    j = store._jadwal.get(jadwal_id)
    if j is None:
        return None
    with j.cond:
        p = j.pesanan.get(kode_booking)
        if p is None:
            return None
        return dict(
            kode_booking=kode_booking,
            jadwal_id=jadwal_id,
            film=j.film,
            pemesan=p["pemesan"],
            kursi=list(p["kursi"]),
            aktif=p["aktif"],
        )


# ─── Statistik / Dashboard ───────────────────────────────────────────────────

def get_statistik(store: StoreBioskop) -> dict:
    """Kumpulkan statistik seluruh jadwal untuk dashboard admin."""
    stats = []
    total_terisi = 0
    total_kosong = 0
    total_pesanan_aktif = 0

    for jid, j in store._jadwal.items():
        with j.cond:
            info = j.info()
            terisi = info["baris"] * info["kolom"] - info["kursi_kosong"]
            n_aktif = sum(1 for p in j.pesanan.values() if p.get("aktif"))
        stats.append(dict(
            jadwal_id=jid,
            film=info["film"],
            studio=info["studio"],
            waktu=info["waktu"],
            total_kursi=info["baris"] * info["kolom"],
            kursi_terisi=terisi,
            kursi_kosong=info["kursi_kosong"],
            total_pesanan=n_aktif,
        ))
        total_terisi += terisi
        total_kosong += info["kursi_kosong"]
        total_pesanan_aktif += n_aktif

    return dict(
        total_jadwal=len(store._jadwal),
        total_pesanan_aktif=total_pesanan_aktif,
        total_kursi_terisi=total_terisi,
        total_kursi_kosong=total_kosong,
        statistik=stats,
    )
