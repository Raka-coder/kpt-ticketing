"""Autentikasi admin: hash SHA-256 + salt, session token in-memory dengan expiry.

Kredensial disimpan di .admin_config.json (TIDAK hardcode di kode).
Jalankan sekali `python -m admin.auth --setup` atau `python admin_auth.py --setup` untuk membuat akun admin pertama.
"""
import argparse
import getpass
import hashlib
import json
import os
import secrets
import time

# Lokasi file konfigurasi di root workspace
_WORKSPACE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CONFIG_FILE = os.path.join(_WORKSPACE_ROOT, ".admin_config.json")
_TOKEN_TTL = 3600          # detik (1 jam)
_sessions: dict[str, float] = {}   # token -> waktu_kedaluwarsa


# Konfigurasi
def _hash_password(password: str, salt: str) -> str:
    return hashlib.sha256((salt + password).encode()).hexdigest()


def _baca_config() -> dict:
    if not os.path.exists(_CONFIG_FILE):
        return {}
    with open(_CONFIG_FILE, encoding="utf-8") as f:
        return json.load(f)


def _tulis_config(data: dict) -> None:
    tmp = _CONFIG_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, _CONFIG_FILE)


def setup_admin(username: str, password: str) -> None:
    """Buat atau perbarui akun admin di file konfigurasi."""
    data = _baca_config()
    users = data.setdefault("users", {})
    salt = secrets.token_hex(16)
    users[username] = {"password_hash": _hash_password(password, salt), "salt": salt}
    _tulis_config(data)
    print(f"[admin_auth] Akun '{username}' berhasil disimpan ke {_CONFIG_FILE}")


def config_ada() -> bool:
    """Kembalikan True jika file konfigurasi admin sudah dibuat."""
    data = _baca_config()
    return bool(data.get("users"))


# Login / Logout
def login(username: str, password: str) -> tuple[bool, str]:
    """Verifikasi kredensial. Kembalikan (sukses, token_atau_pesan_error)."""
    data = _baca_config()
    user = data.get("users", {}).get(username)
    if user is None:
        return False, "Username tidak ditemukan"
    expected = _hash_password(password, user["salt"])
    if not secrets.compare_digest(expected, user["password_hash"]):
        return False, "Password salah"
    token = secrets.token_hex(32)
    _sessions[token] = time.time() + _TOKEN_TTL
    return True, token


def logout(token: str) -> None:
    """Hapus sesi."""
    _sessions.pop(token, None)


def verifikasi_token(token: str) -> bool:
    """Kembalikan True jika token valid dan belum kedaluwarsa."""
    exp = _sessions.get(token)
    if exp is None:
        return False
    if time.time() > exp:
        _sessions.pop(token, None)
        return False
    return True


# CLI Setup
def _cmd_setup():
    print("=== Setup Akun Admin ===")
    username = input("Username baru: ").strip()
    if not username:
        print("Username tidak boleh kosong.")
        return
    pw1 = getpass.getpass("Password baru: ")
    pw2 = getpass.getpass("Konfirmasi password: ")
    if pw1 != pw2:
        print("Password tidak cocok.")
        return
    if len(pw1) < 6:
        print("Password minimal 6 karakter.")
        return
    setup_admin(username, pw1)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Manajemen konfigurasi admin bioskop")
    ap.add_argument("--setup", action="store_true", help="Buat/perbarui akun admin")
    a = ap.parse_args()
    if a.setup:
        _cmd_setup()
    else:
        ap.print_help()
