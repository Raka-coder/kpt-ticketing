"""Server gRPC reservasi tiket bioskop.
Contoh: python server.py --port 50051 --workers 32 --state-file state.json
Opsi demo kegagalan: --lambat-prob 0.5 --lambat-detik 3  (balasan terlambat SETELAH commit)
Opsi demo race    : --tanpa-lock                         (menonaktifkan lock; hanya untuk demo)"""
import argparse
import logging
import random
import time
from concurrent import futures

import grpc

import admin_pb2_grpc as _apb_grpc
import bioskop_pb2 as pb
import bioskop_pb2_grpc as pb_grpc
from admin import LayananAdminServicer
from logika import InputTidakValid, JadwalTidakAda, StoreBioskop

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("server")


class LayananBioskop(pb_grpc.LayananBioskopServicer):
    def __init__(self, store, lambat_prob=0.0, lambat_detik=3.0):
        self.store = store
        self.lambat_prob = lambat_prob
        self.lambat_detik = lambat_detik

    @staticmethod
    def _galat(context, e):
        kode = grpc.StatusCode.NOT_FOUND if isinstance(e, JadwalTidakAda) \
            else grpc.StatusCode.INVALID_ARGUMENT
        context.abort(kode, str(e))

    def _mungkin_lambat(self):
        # Simulasi balasan hilang/terlambat: operasi SUDAH dieksekusi, client kena timeout.
        if self.lambat_prob and random.random() < self.lambat_prob:
            time.sleep(self.lambat_detik)

    def ListJadwal(self, request, context):
        return pb.ListJadwalResponse(jadwal=[pb.Jadwal(**j) for j in self.store.list_jadwal()])

    def GetPetaKursi(self, request, context):
        try:
            info, kursi = self.store.peta(request.jadwal_id)
        except (JadwalTidakAda, InputTidakValid) as e:
            self._galat(context, e)
        return pb.PetaKursi(
            jadwal=pb.Jadwal(**info),
            kursi=[pb.Kursi(kode=k, status=pb.TERISI if p else pb.KOSONG, pemesan=p)
                   for k, p in kursi])

    def PesanKursi(self, request, context):
        try:
            h = self.store.pesan(request.request_id, request.jadwal_id,
                                 request.pemesan, request.kursi)
        except (JadwalTidakAda, InputTidakValid) as e:
            self._galat(context, e)
        self._mungkin_lambat()
        return pb.PesanResponse(**h)

    def BatalkanPesanan(self, request, context):
        try:
            h = self.store.batal(request.request_id, request.kode_booking, request.pemesan)
        except (JadwalTidakAda, InputTidakValid) as e:
            self._galat(context, e)
        self._mungkin_lambat()
        return pb.BatalResponse(**h)

    def StreamStatusKursi(self, request, context):
        try:
            for seq, kode, pemesan, snap in self.store.ikuti(request.jadwal_id,
                                                              aktif=context.is_active):
                yield pb.PerubahanKursi(
                    seq=seq, snapshot=snap,
                    kursi=pb.Kursi(kode=kode, pemesan=pemesan,
                                   status=pb.TERISI if pemesan else pb.KOSONG))
        except (JadwalTidakAda, InputTidakValid) as e:
            self._galat(context, e)


def serve():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--port", type=int, default=50051)
    ap.add_argument("--workers", type=int, default=32,
                    help="jumlah thread pekerja (setiap stream pemantau memakai 1 thread)")
    ap.add_argument("--state-file", default=None, help="simpan state+dedup ke JSON (tahan restart)")
    ap.add_argument("--lambat-prob", type=float, default=0.0)
    ap.add_argument("--lambat-detik", type=float, default=3.0)
    ap.add_argument("--tanpa-lock", action="store_true")
    ap.add_argument("--simulasi-beban", action="store_true",
                    help="simulasi beban validasi gateway pembayaran (0.2-0.5 detik)")
    a = ap.parse_args()

    # Deteksi dan simpan IP Lokal untuk demo 2 laptop
    try:
        from scripts.find_master import get_local_ip
        local_ip = get_local_ip()
    except Exception:
        local_ip = "127.0.0.1"

    try:
        with open("master_ip.txt", "w", encoding="utf-8") as f:
            f.write(local_ip.strip())
    except Exception:
        pass

    store = StoreBioskop(state_file=a.state_file, tanpa_lock=a.tanpa_lock, simulasi_beban=a.simulasi_beban)
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=a.workers))
    pb_grpc.add_LayananBioskopServicer_to_server(
        LayananBioskop(store, a.lambat_prob, a.lambat_detik), server)
    # Admin service didaftarkan di server yang sama
    _apb_grpc.add_LayananAdminServicer_to_server(LayananAdminServicer(store), server)
    server.add_insecure_port(f"[::]:{a.port}")
    server.start()

    logger.info("TICKET_MASTER_IP=%s", local_ip)
    logger.info("Server bioskop berjalan di %s:%d (workers=%d, state=%s, lambat=%.1f, tanpa_lock=%s, simulasi_beban=%s)",
                local_ip, a.port, a.workers, a.state_file, a.lambat_prob, a.tanpa_lock, a.simulasi_beban)
    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        server.stop(2)


if __name__ == "__main__":
    serve()
