"""Utilitas deteksi IP lokal server master pada jaringan LAN/Wi-Fi."""
import socket
import sys


def get_local_ip():
    """Mendeteksi IP lokal device saat ini yang aktif di routing table."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Tidak perlu koneksi nyata ke internet, cukup memicu OS memilih IP interface aktif
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


if __name__ == "__main__":
    ip = get_local_ip()
    if len(sys.argv) > 1:
        with open(sys.argv[1], "w", encoding="utf-8") as f:
            f.write(ip.strip())
    print(ip)
