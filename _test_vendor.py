"""Smoke test: vendored pywin32 import + controller dependency check.
Run with: py -3.11 _test_vendor.py  /  py -3.13 _test_vendor.py
"""
import sys, os
print(f"Python {sys.version}")
print(f"  prefix={sys.prefix}")

import _bootstrap
print(f"  sys.path[0:3]={sys.path[:3]}")

import win32com.client
import pythoncom
import pywintypes
print(f"  win32com.client: OK")
print(f"  pythoncom file: {getattr(pythoncom, '__file__', '?')}")
print(f"  pywintypes file: {getattr(pywintypes, '__file__', '?')}")

import win32api
import win32event
print(f"  win32api file: {getattr(win32api, '__file__', '?')}")
print(f"  win32event file: {getattr(win32event, '__file__', '?')}")

# Verify the ACTUAL attributes autocad_controller.py uses
assert hasattr(pythoncom, "CoInitialize"), "pythoncom missing CoInitialize"
assert hasattr(pythoncom, "VT_ARRAY"), "pythoncom missing VT_ARRAY"
assert hasattr(pythoncom, "VT_R8"), "pythoncom missing VT_R8"
print("  pythoncom.CoInitialize / VT_ARRAY / VT_R8: present")

# Verify win32com.client Dispatch / GetActiveObject
assert hasattr(win32com.client, "Dispatch"), "win32com.client missing Dispatch"
print("  win32com.client.Dispatch: present")
# GetActiveObject may not exist in all pywin32 versions; controller guards it
print(f"  win32com.client.GetActiveObject: {hasattr(win32com.client, 'GetActiveObject')}")

# Import the plugin's own controller (no CAD connection, just import)
import autocad_controller
ctrl = autocad_controller.AutoCADController()
print(f"  controller: HAS_WIN32={autocad_controller.HAS_WIN32}, "
      f"connected={ctrl.connected}, catalog={len(autocad_controller.COMMAND_CATALOG)} cmds")

# Check vendored: are pythoncom/pywintypes/win32api from vendor dirs?
vendored_root = os.path.join(os.path.dirname(__file__), "vendor_cp" +
    f"{sys.version_info.major}{sys.version_info.minor}")
for name, mod in [("pythoncom", pythoncom), ("pywintypes", pywintypes),
                  ("win32api", win32api), ("win32event", win32event)]:
    f = getattr(mod, "__file__", "")
    ok = vendored_root in f if f else False
    print(f"  {name} vendored: {ok}")

print("\nVENDOR IMPORT TEST: PASS")
