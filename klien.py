"""Pustaka client: timeout + retry (exponential backoff + jitter) + request_id otomatis."""
import random
import time
import uuid

import grpc

import bioskop_pb2 as pb
import bioskop_pb2_grpc as pb_grpc

DAPAT_DIULANG = (grpc.StatusCode.DEADLINE_EXCEEDED, grpc.StatusCode.UNAVAILABLE)


class KlienBioskop:
    def __init__(self, target="localhost:50051", timeout=2.0, maks_percobaan=4, on_retry=None):
        self.channel = grpc.insecure_channel(target)
        self.stub = pb_grpc.LayananBioskopStub(self.channel)
        self.timeout = timeout
        self.maks = maks_percobaan
        self.on_retry = on_retry          # callback(nama_rpc, percobaan, kode_status, jeda)

    def tutup(self):
        self.channel.close()

    def _panggil(self, nama, buat_req):
        fn = getattr(self.stub, nama)
        for p in range(1, self.maks + 1):
            try:
                return fn(buat_req(p), timeout=self.timeout)
            except grpc.RpcError as e:
                if e.code() not in DAPAT_DIULANG or p == self.maks:
                    raise
                jeda = min(0.25 * 2 ** (p - 1), 4.0) * random.uniform(0.5, 1.0)
                if self.on_retry:
                    self.on_retry(nama, p, e.code().name, jeda)
                time.sleep(jeda)

    # Operasi idempoten: aman diulang tanpa pengaman tambahan
    def list_jadwal(self):
        return self._panggil("ListJadwal", lambda p: pb.ListJadwalRequest())

    def peta(self, jadwal_id):
        return self._panggil("GetPetaKursi", lambda p: pb.PetaRequest(jadwal_id=jadwal_id))

    # Operasi TIDAK idempoten: request_id dibuat SEKALI per operasi logis
    def pesan_kursi(self, jadwal_id, pemesan, kursi, request_id=None, id_baru_tiap_percobaan=False):
        """id_baru_tiap_percobaan=True hanya untuk demo 'tanpa deduplikasi' (SALAH di produksi)."""
        rid = request_id or str(uuid.uuid4())

        def buat(p):
            r = str(uuid.uuid4()) if id_baru_tiap_percobaan else rid
            return pb.PesanRequest(request_id=r, jadwal_id=jadwal_id, pemesan=pemesan,
                                   kursi=list(kursi))
        return self._panggil("PesanKursi", buat)

    def batalkan(self, kode_booking, pemesan, request_id=None):
        rid = request_id or str(uuid.uuid4())
        return self._panggil("BatalkanPesanan", lambda p: pb.BatalRequest(
            request_id=rid, kode_booking=kode_booking, pemesan=pemesan))

    # Streaming (tanpa deadline; pemanggil menangani RpcError/putus koneksi)
    def pantau(self, jadwal_id):
        return self.stub.StreamStatusKursi(pb.PetaRequest(jadwal_id=jadwal_id))
