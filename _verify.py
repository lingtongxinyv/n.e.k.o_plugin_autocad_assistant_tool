import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import autocad_controller as m

ctrl = m.AutoCADController()
print("catalog size:", len(m.COMMAND_CATALOG))

# action -> controller method name (only when they differ from the action key)
_METHOD_ALIAS = {
    "clear": "clear_modelspace",
    "dimension": "dimension_linear",
    "hatch": "hatched_area",
}

missing_methods = [a for a in m.COMMAND_CATALOG
                   if not hasattr(ctrl, _METHOD_ALIAS.get(a, a))]
print("missing controller methods:", missing_methods)

src = open(os.path.join(os.path.dirname(__file__), "__init__.py"), encoding="utf-8").read()
missing_dispatch = [a for a in m.COMMAND_CATALOG if ('"%s"' % a) not in src]
print("missing in dispatch table:", missing_dispatch)

toml = open(os.path.join(os.path.dirname(__file__), "plugin.toml"), encoding="utf-8").read()
js = open(os.path.join(os.path.dirname(__file__), "static", "script.js"), encoding="utf-8").read()
print("plugin id consistent:", 'id = "autocad_assistant_tool"' in toml
      and '"autocad_assistant_tool"' in js)

# verify the dispatch table actually maps every catalog action
import importlib.util
# Parse _DISPATCH keys from __init__ source without importing plugin.sdk
import re
keys = re.findall(r'"([a-z0-9_]+)":\s*lambda', src)
catalog_actions = set(m.COMMAND_CATALOG)
dispatch_actions = set(keys)
print("dispatch covers catalog:", catalog_actions.issubset(dispatch_actions))
if not catalog_actions.issubset(dispatch_actions):
    print("  NOT covered:", catalog_actions - dispatch_actions)

ok = (not missing_methods and not missing_dispatch
      and catalog_actions.issubset(dispatch_actions))
print("\nALL CHECKS:", "PASS" if ok else "FAIL")
