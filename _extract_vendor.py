"""Extract pywin32 wheels into vendor/ + vendor_cpXY/ structure.

Layout after extraction:
  vendor/
    pythoncom.py            <- root redirector (pure Python)
    pywintypes.py           <- win32/lib/pywintypes.py (pure Python redirector)
    win32com/               <- pure-Python COM client (entire tree)
  vendor_cp311/
    _win32sysloader.pyd     <- compiled loader (ABI-specific)
    pywin32_system32/
      pythoncom311.dll
      pywintypes311.dll
  vendor_cp312/ ... (same shape)
  vendor_cp313/ ... (same shape)

Run: python _extract_vendor.py
"""
import os, shutil, zipfile, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
WHEELS = os.path.join(ROOT, "_wheels")

VENDOR = os.path.join(ROOT, "vendor")
# pure-python redirector files to hoist to vendor/ root (from wheel path -> vendor path)
PURE_FILES = {
    "pythoncom.py": "pythoncom.py",
    "win32/lib/pywintypes.py": "pywintypes.py",
}
# pure-python directories to copy whole into vendor/
PURE_DIRS = ["win32com"]
# pure-python files to flatten from win32/lib/ to vendor/ root (top-level modules)
# These are constants/utils like winerror.py, win32con.py, win32timezone.py etc.
WIN32_LIB_PREFIX = "win32/lib/"

VERSIONS = ["cp311", "cp312", "cp313"]
# version-specific .pyd files: wheel path (relative) -> vendor_cpXY path
# These are the compiled C extensions needed by the import chain of
# win32com.client.Dispatch:
#   win32com/__init__.py        -> win32api
#   win32com/client/__init__.py -> gencache -> win32event
#   pywintypes.py/pythoncom.py  -> _win32sysloader (loads pywin32_system32 DLLs)
VERSION_FILES = [
    ("win32/_win32sysloader.pyd", "_win32sysloader.pyd"),
    ("win32/win32api.pyd", "win32api.pyd"),
    ("win32/win32event.pyd", "win32event.pyd"),
]
# pywin32_system32 DLLs directory
SYSTEM32_DIR = "pywin32_system32"


def reset_dir(path):
    if os.path.isdir(path):
        shutil.rmtree(path)
    os.makedirs(path)


def extract_one(wheel_path, cp_tag):
    """Extract pure-Python (once, into vendor/) + version-specific binaries."""
    target_cp = os.path.join(ROOT, "vendor_" + cp_tag)
    reset_dir(target_cp)
    sys32_out = os.path.join(target_cp, SYSTEM32_DIR)
    os.makedirs(sys32_out, exist_ok=True)

    with zipfile.ZipFile(wheel_path) as z:
        names = z.namelist()

        # --- version-specific binaries ---
        # _win32sysloader.pyd
        for wpath, vpath in VERSION_FILES:
            if wpath in names:
                with z.open(wpath) as f:
                    data = f.read()
                with open(os.path.join(target_cp, vpath), "wb") as out:
                    out.write(data)
                print(f"  [{cp_tag}] {wpath} -> {vpath} ({len(data)} bytes)")
            else:
                print(f"  [{cp_tag}] WARNING: {wpath} not found in wheel")

        # pywin32_system32/*.dll
        dll_count = 0
        for n in names:
            # e.g. pywin32_system32/pythoncom311.dll
            if n.startswith(SYSTEM32_DIR + "/") and n.endswith(".dll"):
                fname = n.split("/")[-1]
                with z.open(n) as f:
                    data = f.read()
                with open(os.path.join(sys32_out, fname), "wb") as out:
                    out.write(data)
                print(f"  [{cp_tag}] {n} -> {SYSTEM32_DIR}/{fname} ({len(data)} bytes)")
                dll_count += 1
        if dll_count == 0:
            print(f"  [{cp_tag}] WARNING: no DLLs found in {SYSTEM32_DIR}/")

    return target_cp


def extract_pure(wheel_path):
    """Extract pure-Python parts into vendor/. Called once (from cp311 wheel)."""
    reset_dir(VENDOR)
    with zipfile.ZipFile(wheel_path) as z:
        names = z.namelist()

        # Hoist redirector .py files to vendor/ root
        for wpath, vpath in PURE_FILES.items():
            if wpath in names:
                with z.open(wpath) as f:
                    data = f.read()
                with open(os.path.join(VENDOR, vpath), "wb") as out:
                    out.write(data)
                print(f"  [pure] {wpath} -> {vpath} ({len(data)} bytes)")
            else:
                print(f"  [pure] WARNING: {wpath} not found in wheel")

        # Copy pure-Python directories wholesale
        for d in PURE_DIRS:
            prefix = d + "/"
            members = [n for n in names if n.startswith(prefix)]
            # verify all are .py (pure python) — warn on .pyd/.dll
            non_py = [n for n in members if n.endswith((".pyd", ".dll"))]
            if non_py:
                print(f"  [pure] WARNING: {d}/ contains compiled files: {non_py}")
            count = 0
            for n in members:
                rel = n[len(prefix):]
                if not rel:
                    continue  # the dir entry itself
                out_path = os.path.join(VENDOR, d, rel.replace("/", os.sep))
                if n.endswith("/"):
                    os.makedirs(out_path, exist_ok=True)
                    continue
                os.makedirs(os.path.dirname(out_path), exist_ok=True)
                with z.open(n) as f:
                    data = f.read()
                with open(out_path, "wb") as out:
                    out.write(data)
                count += 1
            print(f"  [pure] {d}/ -> vendor/{d}/ ({count} files)")

        # Flatten win32/lib/*.py to vendor/ root (top-level importable modules)
        lib_count = 0
        for n in names:
            if n.startswith(WIN32_LIB_PREFIX) and n.endswith(".py"):
                fname = n.split("/")[-1]
                # pywintypes.py already hoisted by PURE_FILES — skip to avoid overwrite noise
                if fname == "pywintypes.py":
                    continue
                with z.open(n) as f:
                    data = f.read()
                with open(os.path.join(VENDOR, fname), "wb") as out:
                    out.write(data)
                lib_count += 1
        print(f"  [pure] win32/lib/*.py -> vendor/ ({lib_count} modules)")


def main():
    print("=== Extracting vendored pywin32 ===\n")
    wheels = {}
    for cp in VERSIONS:
        wp = os.path.join(WHEELS, cp)
        # find the .whl inside
        whls = [f for f in os.listdir(wp) if f.endswith(".whl")] if os.path.isdir(wp) else []
        if not whls:
            print(f"ERROR: no wheel found in {wp}")
            sys.exit(1)
        wheels[cp] = os.path.join(wp, whls[0])
        print(f"  wheel {cp}: {whls[0]}")

    print("\n--- Pure Python (from cp311 wheel) ---")
    extract_pure(wheels["cp311"])

    for cp in VERSIONS:
        print(f"\n--- Version-specific binaries ({cp}) ---")
        extract_one(wheels[cp], cp)

    # create __init__.py for pywin32_system32 namespace packages so import is reliable
    for cp in VERSIONS:
        init = os.path.join(ROOT, "vendor_" + cp, SYSTEM32_DIR, "__init__.py")
        with open(init, "w", encoding="utf-8") as f:
            f.write("# namespace placeholder for pywin32_system32 DLLs\n")
        print(f"  [{cp}] wrote {SYSTEM32_DIR}/__init__.py")

    print("\n=== Done ===")
    # quick sanity: list top-level of each vendor dir
    for d in ["vendor"] + ["vendor_" + cp for cp in VERSIONS]:
        p = os.path.join(ROOT, d)
        if os.path.isdir(p):
            entries = sorted(os.listdir(p))
            print(f"  {d}/: {entries[:8]}{' ...' if len(entries) > 8 else ''}")


if __name__ == "__main__":
    main()
