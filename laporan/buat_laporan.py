import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

# ---------- diagram arsitektur ----------
fig, ax = plt.subplots(figsize=(10, 5.2)); ax.set_xlim(0, 100); ax.set_ylim(0, 52); ax.axis("off")
def kotak(x, y, w, h, teks, fc="#eef3fb", ec="#2b5aa8", fs=8.5, bold=False):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.4,rounding_size=1.2", fc=fc, ec=ec, lw=1.3))
    ax.text(x + w/2, y + h/2, teks, ha="center", va="center", fontsize=fs, fontweight="bold" if bold else "normal")
def panah(x1, y1, x2, y2, teks="", dua=False, y_teks=1.5):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="<->" if dua else "->", mutation_scale=12, lw=1.3, color="#333"))
    if teks: ax.text((x1+x2)/2, (y1+y2)/2 + y_teks, teks, ha="center", fontsize=7.5, color="#333")

ax.add_patch(FancyBboxPatch((1, 2), 28, 48, boxstyle="round,pad=0.3", fc="#fafafa", ec="#999", ls="--"))
ax.text(15, 47.2, "Mesin / container CLIENT", ha="center", fontsize=9, fontweight="bold")
for i, y in enumerate((33, 21, 9)):
    kotak(4, y, 22, 9, f"Client {chr(65+i)}\n(klien.py / uji_race.py)\ntimeout + retry + request_id", fs=7.5)
ax.add_patch(FancyBboxPatch((38, 2), 61, 48, boxstyle="round,pad=0.3", fc="#fafafa", ec="#999", ls="--"))
ax.text(68, 47.2, "Mesin / container SERVER (server.py)", ha="center", fontsize=9, fontweight="bold")
kotak(41, 33, 20, 9, "Server stub\n(LayananBioskop-\nServicer)\nThreadPoolExecutor", fc="#fff4e0", ec="#c77c00", fs=7.5)
kotak(66, 33, 31, 9, "StoreBioskop (logika.py)\nPesan / Batal / Peta / Ikuti", fc="#e9f7ec", ec="#2e8b57", fs=8, bold=True)
for i, (jid, x) in enumerate((("J1", 41), ("J2", 53), ("J3", 65), ("J9", 77))):
    kotak(x, 12, 10.5, 15, f"Jadwal {jid}\nLock/Cond\nkursi[]\ndedup[]\nevents[]", fc="#e9f7ec", ec="#2e8b57", fs=6.8)
kotak(89, 12, 8.5, 15, "state.json\n(opsional)\nfsync", fc="#f3e9f7", ec="#7a3fa0", fs=6.8)
for y in (37.5, 25.5, 13.5):
    pass
panah(26, 37.5, 41, 37.5, "gRPC / HTTP2\nProtobuf", dua=True, y_teks=2)
panah(26, 25.5, 41, 38, "", dua=True); panah(26, 13.5, 41, 34, "", dua=True)
panah(61, 37.5, 66, 37.5)
for cx in (46.25, 58.25, 70.25, 82.25): panah(81, 32.6, cx, 27.4)
ax.text(63, 30.2, "lock per jadwal", ha="center", fontsize=7.5, color="#333")
panah(94, 27.2, 94, 33)
ax.text(68, 5, "Unary: ListJadwal, GetPetaKursi, PesanKursi*, BatalkanPesanan*\nServer streaming: StreamStatusKursi     (* dilindungi request_id: at-most-once)", ha="center", fontsize=7.5)
fig.savefig("arsitektur.png", dpi=170, bbox_inches="tight")

# ---------- PDF ----------
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, Preformatted, PageBreak

ss = getSampleStyleSheet()
B = ParagraphStyle("B", parent=ss["BodyText"], fontSize=10, leading=14.5)
H1 = ParagraphStyle("H1", parent=ss["Heading1"], fontSize=15, spaceBefore=12, spaceAfter=6, textColor=colors.HexColor("#1f3d7a"))
H2 = ParagraphStyle("H2", parent=ss["Heading2"], fontSize=11.5, spaceBefore=8, spaceAfter=4)
T = ParagraphStyle("T", parent=ss["Title"], fontSize=21, leading=26)
S = ParagraphStyle("S", parent=B, alignment=1, fontSize=11)
C = ParagraphStyle("C", parent=B, fontSize=8.5, leading=11)
CODE = ParagraphStyle("CODE", fontName="Courier", fontSize=7.3, leading=8.9)
P = lambda t, s=B: Paragraph(t, s)
def tabel(data, widths, head=True):
    data = [[Paragraph(str(c), C) for c in r] for r in data]
    t = Table(data, colWidths=widths, repeatRows=1 if head else 0)
    st = [("GRID", (0, 0), (-1, -1), .5, colors.grey), ("VALIGN", (0, 0), (-1, -1), "TOP"),
          ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]
    if head: st.append(("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dde6f5")))
    t.setStyle(TableStyle(st)); return t

doc = SimpleDocTemplate("Laporan_ProyekRPC.pdf", pagesize=A4, leftMargin=2*cm, rightMargin=2*cm,
                        topMargin=2*cm, bottomMargin=2*cm, title="Laporan Proyek RPC - Reservasi Tiket Bioskop")
W = A4[0] - 4*cm
e = []
e += [Spacer(1, 3*cm), P("Laporan Proyek Mini", S), P("Sistem Reservasi Tiket Bioskop Berbasis gRPC", T), Spacer(1, .5*cm),
      P("Mata Kuliah Komputasi Paralel dan Terdistribusi - Topik Remote Procedure Calls", S), Spacer(1, 1.2*cm),
      tabel([["Kelompok", "[ISI nomor kelompok]"], ["Anggota", "[ISI nama - NIM] (2-3 orang)"],
             ["Kelas", "[ISI]"], ["Studi kasus", "No. 1 - Reservasi tiket bioskop (rebutan kursi yang sama)"],
             ["Teknologi", "Python 3.10+, gRPC, Protocol Buffers"]], [4*cm, W-4*cm], head=False),
      Spacer(1, 1*cm),
      P("<i>Catatan: bagian bertanda [ISI] dilengkapi kelompok setelah menjalankan pengujian pada mesin masing-masing.</i>", S),
      PageBreak()]

e += [P("1. Deskripsi Studi Kasus dan Arsitektur", H1),
      P("Sebuah bioskop memiliki beberapa jadwal tayang, masing-masing dengan denah kursi. Banyak pengguna (client) dapat "
        "memesan kursi pada saat yang sama sehingga terjadi <b>rebutan sumber daya bersama</b>: dua client tidak boleh "
        "sama-sama berhasil memesan kursi yang sama. Layanan juga harus tetap benar ketika jaringan lambat atau balasan hilang "
        "(client mengulang permintaan), dan pengguna dapat memantau perubahan status kursi secara real-time."),
      Image("arsitektur.png", width=W, height=W*0.53),
      P("<i>Gambar 1. Komponen dan alur pemanggilan RPC.</i>", C),
      P("<b>Alur satu pemesanan:</b> (1) program client memanggil <font face='Courier'>pesan_kursi()</font> pada client stub; "
        "(2) stub melakukan marshalling <font face='Courier'>PesanRequest</font> (termasuk <font face='Courier'>request_id</font>) "
        "ke Protobuf; (3) dikirim lewat HTTP/2 dengan deadline; (4) server stub melakukan unmarshalling dan memanggil "
        "<font face='Courier'>StoreBioskop.pesan()</font>; (5) logika bisnis mengunci jadwal, memeriksa dan menulis kursi, mencatat "
        "hasil pada tabel deduplikasi; (6) <font face='Courier'>PesanResponse</font> dikemas dan dikirim kembali. Jika balasan "
        "hilang, client mengulang dengan <font face='Courier'>request_id</font> yang sama dan server menjawab dari tabel dedup."),
      P("2. Antarmuka Layanan (.proto)", H1),
      P("Antarmuka mendefinisikan <b>5 RPC</b> (syarat minimal 4, termasuk minimal 1 streaming):")]
e += [tabel([["RPC", "Jenis", "Idempoten?", "Penjelasan"],
             ["ListJadwal", "Unary", "Ya", "Daftar jadwal dan jumlah kursi kosong."],
             ["GetPetaKursi", "Unary", "Ya", "Snapshot denah kursi satu jadwal."],
             ["PesanKursi", "Unary", "<b>Tidak</b>", "Memesan 1-6 kursi, semua-atau-tidak-sama-sekali. Wajib request_id."],
             ["BatalkanPesanan", "Unary", "<b>Tidak</b>", "Membatalkan pesanan (hanya pemilik). Wajib request_id."],
             ["StreamStatusKursi", "Server streaming", "Ya", "Snapshot awal lalu setiap perubahan kursi secara real-time."]],
            [3.4*cm, 2.6*cm, 2.2*cm, W-8.2*cm]), Spacer(1, 6),
      P("Penanganan galat memakai kode status gRPC: <font face='Courier'>NOT_FOUND</font> (jadwal/kode tidak ada), "
        "<font face='Courier'>INVALID_ARGUMENT</font> (input tidak valid, request_id dipakai ulang untuk isi berbeda). "
        "Kegagalan bisnis yang deterministik (kursi sudah terisi) dikembalikan sebagai <font face='Courier'>sukses=false</font> "
        "agar ikut tersimpan dalam cache deduplikasi."),
      P("Isi lengkap <font face='Courier'>bioskop.proto</font>:", H2),
      Preformatted(open("../bioskop.proto", encoding="utf-8").read(), CODE), PageBreak()]

e += [P("3. Strategi Concurrency dan Toleransi Kegagalan", H1),
      P("3.1 Concurrency", H2),
      P("Server gRPC memproses permintaan pada <font face='Courier'>ThreadPoolExecutor</font>, sehingga banyak permintaan "
        "mengakses data kursi bersamaan. Pilihan mekanisme:"),
      tabel([["Pilihan", "Alasan"],
             ["Lock per jadwal (threading.Condition)", "Pemesanan pada jadwal berbeda berjalan paralel; pada jadwal yang sama diserialkan. "
              "Lebih baik daripada lock global (bottleneck) dan lebih sederhana serta bebas deadlock dibanding lock per kursi."],
             ["Cek + tulis + catat hasil dalam satu critical section", "Menutup celah check-then-act: tanpa ini dua thread bisa sama-sama melihat kursi kosong."],
             ["Semua-atau-tidak-sama-sekali", "Pemesanan banyak kursi tidak pernah sebagian terisi."],
             ["Condition yang sama untuk streaming", "Pemantau menunggu dengan wait(); setiap perubahan memanggil notify_all(), tanpa polling."]],
            [5.6*cm, W-5.6*cm]),
      P("3.2 Toleransi kegagalan", H2),
      tabel([["Gangguan", "Penanganan"],
             ["Balasan lambat / hilang", "Client memakai deadline (timeout) per panggilan."],
             ["Server sementara tidak tersedia", "Retry hanya untuk DEADLINE_EXCEEDED dan UNAVAILABLE dengan exponential backoff (0,25 x 2^(n-1) s, maks 4 s) dan jitter; maksimal 4 percobaan."],
             ["Retry menyebabkan eksekusi ganda", "request_id (UUID) dibuat sekali per operasi logis; server menyimpan hasil per request_id sehingga permintaan ulang mengembalikan hasil lama (<b>at-most-once</b>). request_id yang dipakai ulang untuk isi berbeda ditolak."],
             ["Server restart", "Opsi --state-file: state dan tabel dedup ditulis atomik (os.replace + fsync) sebelum balasan dikirim, sehingga jaminan at-most-once bertahan."],
             ["Client terputus saat streaming", "Server memeriksa context.is_active() dan menghentikan stream; client dapat menyambung ulang dan menerima snapshot baru."]],
            [5.0*cm, W-5.0*cm]),
      P("Operasi idempoten (ListJadwal, GetPetaKursi) aman diulang tanpa pengaman tambahan; operasi tidak idempoten "
        "(PesanKursi, BatalkanPesanan) wajib memakai request_id sesuai ketentuan tugas.")]

e += [PageBreak(), P("4. Hasil Pengujian dan Analisis", H1),
      P("4.1 Uji unit logika bisnis (tanpa jaringan)", H2),
      P("<font face='Courier'>python -m unittest -v test_logika</font> - <b>11 uji, semuanya lulus</b>:"),
      tabel([["Uji", "Yang dibuktikan"],
             ["race_satu_kursi_hanya_satu_pemenang", "200 thread serentak merebut A1 -> tepat 1 pemenang."],
             ["beban_acak_tidak_ada_kursi_ganda", "150 thread masing-masing meminta 3 kursi acak -> tidak ada kursi ganda, jumlah terisi konsisten."],
             ["tanpa_lock_terjadi_pemesanan_ganda", "Kontrol negatif: tanpa lock, lebih dari satu pemenang."],
             ["dedup_request_id_sama / dedup_retry_serentak", "Permintaan ulang (juga serentak, 30 thread) hanya dieksekusi sekali."],
             ["request_id_dipakai_untuk_permintaan_lain", "request_id yang sama untuk isi berbeda ditolak."],
             ["semua_atau_tidak_sama_sekali", "Pesanan A1+A2 saat A1 terisi -> A2 tetap kosong."],
             ["batal", "Hanya pemilik; batal ganda ditolak; retry batal aman."],
             ["stream_snapshot_dan_perubahan", "Snapshot 80 kursi lalu perubahan diterima berurutan."],
             ["persistensi_dedup_setelah_restart", "Setelah 'restart', request_id lama tetap dikenali."],
             ["input_tidak_valid", "Validasi request_id, kode kursi, jadwal."]],
            [6.3*cm, W-6.3*cm]),
      P("4.2 Eksperimen lock vs tanpa lock", H2),
      P("<font face='Courier'>python eksperimen_lokal.py</font>: 100 thread merebut kursi A1, 10 ronde (hasil percobaan nyata):"),
      tabel([["Konfigurasi", "Pemenang per ronde", "Ronde dengan pemesanan ganda"],
             ["Dengan lock", "1, 1, 1, 1, 1, 1, 1, 1, 1, 1", "0 / 10"],
             ["Tanpa lock", "97, 100, 100, 100, 100, 100, 100, 100, 100, 100", "10 / 10"]],
            [3.2*cm, 9*cm, W-12.2*cm]),
      P("<b>Analisis:</b> tanpa lock, interval antara pemeriksaan 'kursi kosong' dan penulisan pemilik adalah celah race "
        "condition: hampir semua thread melihat kursi kosong sebelum ada yang menulis, sehingga satu kursi 'terjual' ke "
        "puluhan orang. Dengan lock, pemeriksaan dan penulisan atomik sehingga tepat satu thread menang. (Angka tanpa "
        "lock sengaja diperbesar dengan jeda 1 ms di dalam celah agar mudah diamati; pada beban nyata celahnya lebih sempit "
        "tetapi tetap ada.)"),
      P("4.3 Uji race condition melalui gRPC (dua mesin)", H2),
      P("Jalankan <font face='Courier'>python uji_race.py --host IP:50051 --klien 50</font> dan tempel keluarannya:"),
      tabel([["Tes", "Hasil yang diharapkan", "Hasil kelompok"],
             ["Tes 1: 50 client rebut J1/A1", "pemenang = 1", "[ISI]"],
             ["Tes 2: 100 client x 3 kursi acak (J2)", "kursi ganda = tidak ada; jumlah konsisten", "[ISI]"],
             ["Pembanding: server --tanpa-lock", "pemenang > 1 / kursi ganda ada", "[ISI]"]],
            [6.2*cm, 6*cm, W-12.2*cm]),
      P("4.4 Demo timeout, retry, dan deduplikasi", H2),
      tabel([["Skenario (server --lambat-prob 0.5)", "Retry", "Sukses (client)", "Terisi (server)", "Konsisten?"],
             ["demo_retry.py (id tetap)", "[ISI]", "[ISI]", "[ISI]", "[ISI] (harapan: ya)"],
             ["demo_retry.py --tanpa-dedup", "[ISI]", "[ISI]", "[ISI]", "[ISI] (harapan: tidak)"]],
            [5.6*cm, 1.8*cm, 3*cm, 3*cm, W-13.4*cm]),
      P("4.5 Kinerja: latensi dan throughput", H2),
      P("<font face='Courier'>python bench.py --host IP:50051 --n 100</font> menghasilkan <font face='Courier'>hasil/hasil_bench.csv</font> "
        "dan grafik <font face='Courier'>hasil/hasil_bench.png</font> (sisipkan di bawah). Mode baca = GetPetaKursi; "
        "mode tulis = PesanKursi + BatalkanPesanan."),
      tabel([["Mode", "Client", "Total op", "Waktu (s)", "Throughput (req/s)", "Latensi rata-rata (ms)", "p95 (ms)"]] +
            [[m, str(c), "[ISI]", "[ISI]", "[ISI]", "[ISI]", "[ISI]"] for m in ("baca", "tulis") for c in (1, 5, 20)],
            [1.8*cm, 1.8*cm, 2*cm, 2.2*cm, 3.2*cm, 3.6*cm, W-14.6*cm]),
      P("<b>Panduan analisis (isi dengan data sendiri):</b> bandingkan throughput 1 vs 5 vs 20 client; jelaskan mengapa "
        "throughput tidak naik linear (GIL Python membatasi paralelisme CPU; lock per jadwal menyerialkan penulisan pada jadwal "
        "yang sama; jumlah thread server <font face='Courier'>--workers</font>; latensi jaringan). Bandingkan latensi baca "
        "(tanpa kontensi) dengan tulis (ada kontensi lock). Ulangi dengan <font face='Courier'>--workers 1/4/32</font> untuk "
        "melihat pengaruh thread."),
      P("[ISI: sisipkan grafik hasil_bench.png dan analisis penyebab]")]

e += [P("5. Pembagian Tugas Anggota", H1),
      tabel([["Anggota", "Tugas", "Commit utama"],
             ["[ISI]", "[ISI contoh: desain .proto, server, logika concurrency]", "[ISI]"],
             ["[ISI]", "[ISI contoh: client, retry/dedup, demo]", "[ISI]"],
             ["[ISI]", "[ISI contoh: pengujian kinerja, laporan, video]", "[ISI]"]], [3.5*cm, 9*cm, W-12.5*cm]),
      P("6. Tautan dan Referensi", H1),
      tabel([["Item", "Tautan / keterangan"],
             ["Repositori Git", "[ISI URL repositori; riwayat commit setiap anggota]"],
             ["Video demo (maks. 5 menit)", "[ISI URL video]"],
             ["Cara menjalankan", "Lihat README.md (instalasi, generate stub, menjalankan server/client, Docker)"],
             ["Alat bantu", "Kerangka kode dan dokumen dibuat dengan bantuan asisten AI Claude (Anthropic); kelompok telah menelaah, menjalankan, dan menyesuaikan kode. Referensi: dokumentasi gRPC Python (grpc.io) dan modul praktikum RPC."]],
            [4*cm, W-4*cm])]
doc.build(e)
print("PDF ok")
