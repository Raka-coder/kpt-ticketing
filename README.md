# Proyek Mini RPC — Reservasi Tiket Bioskop (gRPC)

Mata kuliah Komputasi Paralel dan Terdistribusi · Studi kasus 1: *beberapa client memesan kursi
yang sama secara bersamaan*.

Layanan reservasi tiket bioskop berbasis **gRPC + Protocol Buffers** (Python 3.10+). Server menjamin
satu kursi tidak pernah terjual dua kali walau diperebutkan banyak client; client memakai
**timeout + retry (exponential backoff)**, dan operasi yang tidak idempoten dilindungi
**request_id (at-most-once)**.

## Struktur berkas

| Berkas / Folder | Fungsi |
|---|---|
| `proto/bioskop.proto` | Kontrak layanan (IDL): 5 RPC (4 unary + 1 server streaming) |
| `logika.py` | Logika bisnis thread-safe: lock per jadwal, deduplikasi, streaming, persistensi (tanpa gRPC) |
| `server.py` | Server gRPC (servicer tipis di atas `logika.py`) |
| `klien.py` | Pustaka client: timeout, retry + backoff + jitter, request_id otomatis |
| `klien_cli.py` | CLI: `jadwal`, `peta`, `pesan`, `batal`, `pantau` |
| `scripts/uji_race.py` | Uji beban race condition via gRPC (rebutan 1 kursi; rebutan kursi acak) |
| `scripts/demo_retry.py` | Demo timeout + retry, dengan/tanpa deduplikasi |
| `scripts/bench.py` | Pengukuran latensi & throughput untuk 1, 5, 20 client → CSV + grafik |
| `tests/test_logika.py` | 11 uji unit logika bisnis (tanpa gRPC) |
| `scripts/eksperimen_lokal.py` | Eksperimen dengan lock vs tanpa lock (tanpa gRPC) |
| `laporan/Laporan_ProyekRPC.pdf` | Laporan proyek |
| `generate_stubs.py` | Membuat `bioskop_pb2.py` dan `bioskop_pb2_grpc.py` dari proto |
| `run_tests.py` | Menjalankan seluruh uji lokal dengan satu perintah |
| `run_race_local.py` | Menjalankan uji race condition lokal (server + client) dengan satu perintah |

Catatan: berkas `bioskop_pb2.py` dan `bioskop_pb2_grpc.py` dihasilkan otomatis (diabaikan oleh
`.gitignore`) dan tidak disimpan di repositori.

## Instalasi

```bash
python -m venv venv
# Windows: venv\Scripts\activate   |   Linux/macOS: source venv/bin/activate
pip install -r requirements-bench.txt     # grpcio, grpcio-tools, matplotlib
python generate_stubs.py                  # Windows
# atau: ./generate_stub.sh                # Linux/macOS
```

Perintah terakhir menghasilkan `bioskop_pb2.py` dan `bioskop_pb2_grpc.py`
(kelas `LayananBioskopStub` dan `LayananBioskopServicer`).

## Menjalankan

### Satu komputer (dua terminal)

```bash
# Terminal 1
python server.py

# Terminal 2
python klien_cli.py jadwal
python klien_cli.py peta J1
python klien_cli.py pesan J1 Andi A1 A2
python klien_cli.py pesan J1 Budi A2        # GAGAL: A2 sudah terisi (semua-atau-tidak-sama-sekali)
python klien_cli.py batal J1-0001 Andi
```

Pemantauan real-time (server streaming) — buka di terminal ketiga lalu pesan dari terminal lain:

```bash
python klien_cli.py pantau J1
```

### Dua laptop (server dan client, tanpa Docker)

1. Di laptop **server**: jalankan `python server.py`, lalu cek IP-nya (`ipconfig` di Windows /
   `ip a` di Linux/macOS); buka port **50051** di firewall.
2. Di laptop **client**: jalankan skrip client dengan `--host <IP-SERVER>:50051`, misalnya
   `python scripts/uji_race.py --host 192.168.1.10:50051` (semua skrip client menerima
   `--host IP:PORT`).

## Skenario demo (disarankan untuk presentasi)

**1. Race condition dibuktikan teratasi** (server normal)

```bash
python run_race_local.py
# atau manual: python server.py (terminal 1) + python scripts/uji_race.py --host localhost:50051 --klien 50 (terminal 2)
# [Tes 1] 50 client rebut J1/A1: pemenang=1 ... LULUS
# [Tes 2] 100 client x 3 kursi acak di J2: kursi ganda=tidak ada ... LULUS
```

**2. Pembanding: server tanpa lock** → jalankan `python server.py --tanpa-lock`, lalu ulangi `scripts/uji_race.py`.
Pemenang >1 dan/atau kursi ganda = data rusak (bukti perlunya lock). Hasil tanpa jaringan:
`python scripts/eksperimen_lokal.py`.

**3. Timeout + retry + deduplikasi**

```bash
python server.py --lambat-prob 0.5 --lambat-detik 3        # balasan terlambat SETELAH pemesanan terjadi
python scripts/demo_retry.py                               # id tetap  → "KONSISTEN"
# restart server (Ctrl+C lalu jalankan lagi dengan opsi yang sama)
python scripts/demo_retry.py --tanpa-dedup                 # id baru tiap percobaan → "pesanan hantu"
```

Tanpa deduplikasi, balasan yang terlambat membuat client mengulang; kursinya *sudah* terisi oleh
percobaan pertama sehingga client menerima "gagal" padahal pesanannya tercatat di server.

**4. Server restart** (jaminan at-most-once tahan restart):
`python server.py --state-file state.json` → pesan kursi → hentikan & jalankan ulang server →
kirim ulang dengan `request_id` yang sama (lihat `test_persistensi_dedup_setelah_restart`).

## Pengujian

```bash
python run_tests.py                            # 11 uji, tanpa gRPC, ~0,4 detik
# atau: python -m unittest discover -s tests -v
python scripts/eksperimen_lokal.py             # lock vs tanpa lock
python run_race_local.py                       # race condition end-to-end lokal
python scripts/bench.py --host localhost:50051 --n 100     # kinerja 1/5/20 client → hasil/hasil_bench.{csv,png}
```

Untuk hasil benchmark yang adil, jalankan server dengan `--workers 32` (bawaan) dan, jika ingin
mengukur pengaruh thread, ulangi dengan `--workers 1`, `4`, `10` (lihat Praktikum 3 L3.4).

## Desain singkat

**Antarmuka (`proto/bioskop.proto`)** — `ListJadwal`, `GetPetaKursi` (unary, idempoten); `PesanKursi`,
`BatalkanPesanan` (unary, tidak idempoten, wajib `request_id`); `StreamStatusKursi` (server streaming:
snapshot awal + setiap perubahan kursi).

**Concurrency** — satu `threading.Condition` (RLock) per jadwal. Cek ketersediaan, penulisan kursi,
dan pencatatan hasil deduplikasi berada dalam satu critical section (atomik). Dipilih lock per jadwal
(bukan lock global) agar jadwal berbeda tidak saling menunggu, dan bukan lock per kursi agar
pemesanan banyak kursi tetap atomik tanpa risiko deadlock. `Condition` yang sama membangunkan stream
pemantau. Server gRPC memakai `ThreadPoolExecutor`.

**Toleransi kegagalan** — client: deadline per panggilan, retry hanya untuk `DEADLINE_EXCEEDED` dan
`UNAVAILABLE`, jeda `0,25·2^(n−1)` detik dengan jitter. Server: hasil tiap `request_id` disimpan →
permintaan ulang mengembalikan hasil lama tanpa eksekusi ulang (at-most-once); `request_id` yang
dipakai ulang untuk isi permintaan berbeda ditolak (`INVALID_ARGUMENT`). Dengan `--state-file`, state
dan tabel dedup ditulis ke disk (atomik via `os.replace` + `fsync`) *sebelum* balasan dikirim.

## Batasan yang diketahui

* Tabel dedup dan daftar event tumbuh tanpa batas (produksi: TTL / kompaksi).
* `--state-file` menulis seluruh state setiap perubahan (cukup untuk demo; produksi: database / WAL).
* Satu server (tanpa replikasi); koneksi `insecure` (tanpa TLS).
* Setiap stream `pantau` memakai satu thread pekerja; atur `--workers` > jumlah pemantau.

## Catatan integritas akademik

Kerangka kode proyek ini dihasilkan dengan bantuan asisten AI (Claude, Anthropic) sesuai ketentuan
tugas bahwa alat bantu wajib dicantumkan. Mahasiswa wajib memahami, menjalankan, dan menjelaskan
seluruh kode saat presentasi, serta melengkapi bagian yang ditandai `[ISI]` di laporan
(identitas, hasil benchmark, pembagian tugas, tautan repositori & video).
