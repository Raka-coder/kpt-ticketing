"""Shim backward compatibility untuk admin_servicer -> admin.servicer"""
from admin.servicer import LayananAdminServicer

__all__ = ["LayananAdminServicer"]
