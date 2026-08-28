"""N.E.K.O 官方发布合规性检查 — 最终验证。
Run: python _compliance.py
"""
import os, sys, re

ROOT = os.path.dirname(os.path.abspath(__file__))
fails = []
warns = []

def ok(msg): print(f"  [PASS] {msg}")
def fail(msg): fails.append(msg); print(f"  [FAIL] {msg}")
def warn(msg): warns.append(msg); print(f"  [WARN] {msg}")

print("=" * 60)
print("N.E.K.O 插件发布合规性检查")
print("=" * 60)

# --- 1. plugin.toml 字段完整性 ---
print("\n--- 1. plugin.toml 字段 ---")
toml = open(os.path.join(ROOT, "plugin.toml"), encoding="utf-8").read()
required_fields = {
    "id": r'id\s*=\s*"([^"]+)"',
    "name": r'name\s*=\s*"([^"]+)"',
    "description": r'description\s*=',
    "version": r'version\s*=\s*"([^"]+)"',
    "entry": r'entry\s*=\s*"([^"]+)"',
}
for field, pat in required_fields.items():
    m = re.search(pat, toml)
    if m:
        ok(f"plugin.{field} = {m.group(1) if m.lastindex else '(present)'}")
    else:
        fail(f"plugin.toml 缺少 {field}")

# author
if "[plugin.author]" in toml:
    ok("[plugin.author] present")
else:
    fail("plugin.toml 缺少 [plugin.author]")

# sdk version range
if "[plugin.sdk]" in toml:
    ok("[plugin.sdk] present")
else:
    fail("plugin.toml 缺少 [plugin.sdk]")

# ui enabled
if re.search(r'\[plugin\.ui\]\s*enabled\s*=\s*true', toml):
    ok("[plugin.ui] enabled=true")
else:
    fail("[plugin.ui] 未启用或缺失")

# guide entry
if "[[plugin.ui.guide]]" in toml:
    ok("[[plugin.ui.guide]] present")
else:
    fail("plugin.toml 缺少 guide 入口")

# runtime
if re.search(r'\[plugin_runtime\]\s*enabled\s*=\s*true', toml):
    ok("[plugin_runtime] enabled=true")
else:
    fail("[plugin_runtime] 未启用或缺失")

# --- 2. 版本一致性 ---
print("\n--- 2. 版本一致性 ---")
toml_ver = re.search(r'version\s*=\s*"([^"]+)"', toml).group(1)
pyproj = open(os.path.join(ROOT, "pyproject.toml"), encoding="utf-8").read()
pyproj_ver = re.search(r'version\s*=\s*"([^"]+)"', pyproj).group(1)
if toml_ver == pyproj_ver:
    ok(f"plugin.toml == pyproject.toml == {toml_ver}")
else:
    fail(f"版本不一致: plugin.toml={toml_ver} pyproject.toml={pyproj_ver}")

# --- 3. 插件 ID 一致性 ---
print("\n--- 3. 插件 ID 一致性 ---")
plugin_id = re.search(r'id\s*=\s*"([^"]+)"', toml).group(1)
js = open(os.path.join(ROOT, "static", "script.js"), encoding="utf-8").read()
js_id = re.search(r'PLUGIN_ID\s*=\s*"([^"]+)"', js)
if js_id and js_id.group(1) == plugin_id:
    ok(f"plugin.toml == script.js == '{plugin_id}'")
else:
    fail(f"ID 不一致: toml={plugin_id} js={js_id.group(1) if js_id else 'NOT FOUND'}")

# entry 指向的模块名应包含 id
entry = re.search(r'entry\s*=\s*"([^"]+)"', toml).group(1)
if plugin_id in entry:
    ok(f"entry 包含插件 ID: {entry}")
else:
    warn(f"entry '{entry}' 不包含 ID '{plugin_id}' (可能正确但请确认)")

# --- 4. 目录结构 ---
print("\n--- 4. 目录结构 ---")
expected_dirs = ["vendor", "vendor_cp311", "vendor_cp312", "vendor_cp313",
                 "static", "docs", "tests"]
for d in expected_dirs:
    p = os.path.join(ROOT, d)
    if os.path.isdir(p):
        ok(f"{d}/ exists")
    else:
        fail(f"缺少目录: {d}/")

# entry class exists in __init__.py
init_src = open(os.path.join(ROOT, "__init__.py"), encoding="utf-8").read()
entry_class = entry.split(":")[-1] if ":" in entry else ""
if f"class {entry_class}" in init_src:
    ok(f"__init__.py 定义了入口类: {entry_class}")
else:
    fail(f"__init__.py 未找到类 {entry_class}")

# --- 5. vendor/ 纯 Python（无 .pyd/.dll）---
print("\n--- 5. vendor/ 纯 Python 检查 ---")
bad = []
vendor_dir = os.path.join(ROOT, "vendor")
for dirpath, dirs, files in os.walk(vendor_dir):
    for f in files:
        if f.endswith((".pyd", ".dll")):
            bad.append(os.path.relpath(os.path.join(dirpath, f), ROOT))
if not bad:
    ok("vendor/ 无 .pyd/.dll 文件（纯 Python）")
else:
    fail(f"vendor/ 包含编译文件: {bad[:5]}{'...' if len(bad)>5 else ''}")

# --- 6. vendor_cpXXX/ 包含正确的二进制 ---
print("\n--- 6. vendor_cpXXX/ 二进制检查 ---")
for cp in ["cp311", "cp312", "cp313"]:
    d = os.path.join(ROOT, "vendor_" + cp)
    pyd = [f for f in os.listdir(d) if f.endswith(".pyd")]
    sys32 = os.path.join(d, "pywin32_system32")
    dlls = sorted(os.listdir(sys32)) if os.path.isdir(sys32) else []
    # expect: _win32sysloader.pyd, win32api.pyd, win32event.pyd
    expected_pyd = {"_win32sysloader.pyd", "win32api.pyd", "win32event.pyd"}
    got_pyd = set(pyd)
    if expected_pyd.issubset(got_pyd):
        ok(f"{cp}/: pyd={pyd}, dlls={len(dlls)} files")
    else:
        fail(f"{cp}/ 缺少 .pyd: {expected_pyd - got_pyd}")
    # check DLLs match version
    major, minor = cp[2:5], cp[5:]  # e.g. "311" -> "3","11"? no: cp311 -> 3,11
    vtag = cp[2:]  # "311"
    expected_dlls = {f"pythoncom{vtag}.dll", f"pywintypes{vtag}.dll"}
    got_dlls = set(f for f in dlls if f.endswith(".dll"))
    if expected_dlls.issubset(got_dlls):
        ok(f"  {cp}/ DLLs: {sorted(expected_dlls & got_dlls)}")
    else:
        fail(f"  {cp}/ 缺少 DLL: {expected_dlls - got_dlls}")

# --- 7. 零系统依赖验证（在干净 Python 上）---
print("\n--- 7. 零系统依赖验证 ---")
# Check that _bootstrap.py injects vendor paths before any pywin32 import
boot = open(os.path.join(ROOT, "_bootstrap.py"), encoding="utf-8").read()
if "setup_vendor_paths()" in boot and "sys.path.insert(0" in boot:
    ok("_bootstrap.py 在导入前注入 vendor 路径")
else:
    fail("_bootstrap.py 未正确注入 vendor 路径")
if "add_dll_directory" in boot:
    ok("_bootstrap.py 注册 DLL 搜索路径 (Python 3.8+)")
else:
    warn("_bootstrap.py 未调用 add_dll_directory (可能影响 3.8+ DLL 加载)")
# controller imports _bootstrap first
ctrl = open(os.path.join(ROOT, "autocad_controller.py"), encoding="utf-8").read()
if re.search(r'import _bootstrap\b', ctrl):
    ok("autocad_controller.py 在 win32com 之前导入 _bootstrap")
else:
    fail("autocad_controller.py 未在 win32com 之前导入 _bootstrap")

# --- 8. .gitignore ---
print("\n--- 8. .gitignore ---")
gi = open(os.path.join(ROOT, ".gitignore"), encoding="utf-8").read()
for pat in ["__pycache__/", "_wheels/", ".venv/"]:
    if pat in gi:
        ok(f".gitignore 排除 {pat}")
    else:
        fail(f".gitignore 未排除 {pat}")

# --- 9. docs/guide.md ---
print("\n--- 9. 使用指南 ---")
guide = os.path.join(ROOT, "docs", "guide.md")
if os.path.isfile(guide):
    ok("docs/guide.md 存在")
else:
    fail("缺少 docs/guide.md")

# --- 10. config.example.toml ---
print("\n--- 10. 示例配置 ---")
cfg = os.path.join(ROOT, "config.example.toml")
if os.path.isfile(cfg):
    ok("config.example.toml 存在")
else:
    fail("缺少 config.example.toml")

# --- Summary ---
print("\n" + "=" * 60)
total = len(fails) + len(warns)
if not fails:
    print(f"合规性检查: PASS ({len(warns)} warnings)")
else:
    print(f"合规性检查: FAIL ({len(fails)} failures, {len(warns)} warnings)")
    for f in fails:
        print(f"  - {f}")
for w in warns:
    print(f"  ~ {w}")
print("=" * 60)
sys.exit(1 if fails else 0)
