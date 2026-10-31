"""Shim backward compatibility untuk admin_auth -> admin.auth"""
from admin.auth import *
from admin.auth import _CONFIG_FILE, _sessions, _hash_password, _baca_config, _tulis_config

if __name__ == "__main__":
    import admin.auth as _target
    _target._cmd_setup()
