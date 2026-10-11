import importlib
import _scope_sysmod
import _scope_reload

print('0', importlib.import_module('json').dumps([1]))
# 1. importlib.import_module of an interpreted module returns the same module object
try:
    m = importlib.import_module('_scope_sysmod')
    print('1', m is _scope_sysmod)
except ImportError as e:
    print('1', type(e).__name__, e)
# 2. importlib.import_module of a not-yet-imported local module (with a package)
try:
    alpha = importlib.import_module('_scope_pkg.alpha')
    print('2', alpha.ALPHA)
    print('2b', importlib.import_module('.beta', '_scope_pkg').BETA)
except ImportError as e:
    print('2', type(e).__name__, e)
# 3. importlib.reload re-executes the module in the same namespace
try:
    r = importlib.reload(_scope_reload)
    print('3', r is _scope_reload, _scope_reload.runs)
except Exception as e:
    print('3', type(e).__name__, e)
