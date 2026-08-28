"""Vendor path bootstrap for self-contained pywin32 dependency.

N.E.K.O host runs on Python 3.11. To make the plugin truly plug-and-play
(zero system dependency on pywin32), the compiled pywin32 binaries (.pyd/.dll)
are vendored into version-specific ``vendor_cpXY`` directories, and the pure
Python parts into ``vendor/``. This module injects them onto ``sys.path`` in
the correct order *before* ``win32com``/``pythoncom`` are imported.

Order matters: version-specific vendor_cpXY must come before the general
``vendor/`` so the right ABI-matching extension modules win import resolution.
"""
from __future__ import annotations

import os
import sys

_VENDORED = False


def _plugin_root() -> str:
    return os.path.dirname(os.path.abspath(__file__))


def setup_vendor_paths() -> None:
    """Insert vendored pywin32 directories onto sys.path (idempotent).

    Also registers the version-specific DLL directory with the OS loader so
    that ``pythoncomXY.dll`` / ``pywintypesXY.dll`` are findable by
    ``_win32sysloader.LoadModule`` on Python 3.8+ (restricted DLL search).
    """
    global _VENDORED
    if _VENDORED:
        return
    _VENDORED = True

    root = _plugin_root()
    # Build candidate cp-tag from running interpreter, e.g. cp311 / cp312 / cp313.
    cp_tag = "cp{0}{1}".format(sys.version_info.major, sys.version_info.minor)

    # Version-specific directory first (holds _win32sysloader.pyd, win32api.pyd,
    # win32event.pyd, and pywin32_system32/ with pythoncomXY.dll + pywintypesXY.dll).
    cp_dir = os.path.join(root, "vendor_" + cp_tag)
    if os.path.isdir(cp_dir) and cp_dir not in sys.path:
        sys.path.insert(0, cp_dir)
        # Make the bundled DLLs discoverable by the Windows loader (Python 3.8+).
        dll_dir = os.path.join(cp_dir, "pywin32_system32")
        if os.path.isdir(dll_dir) and hasattr(os, "add_dll_directory"):
            try:
                os.add_dll_directory(dll_dir)
            except (OSError, FileNotFoundError):
                pass  # directory may not exist on some installs; non-fatal

    # General pure-Python vendor second (win32com/, pywintypes.py, pythoncom.py).
    vendor_dir = os.path.join(root, "vendor")
    if os.path.isdir(vendor_dir) and vendor_dir not in sys.path:
        # Keep it right after the version-specific dir when possible.
        try:
            sys.path.insert(1, vendor_dir)
        except IndexError:
            sys.path.append(vendor_dir)


# Run at import time so a plain ``import _bootstrap`` is enough.
setup_vendor_paths()
