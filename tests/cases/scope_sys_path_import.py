import os
import sys

here = os.path.dirname(os.path.abspath(__file__))
# sys.path[0] is the directory of the script being run
print('1', os.path.abspath(sys.path[0]) == here)
# a directory added to sys.path is searched by the import statement, and modules
# imported from there share the already-loaded modules
import _scope_mod
sys.path.insert(0, os.path.join(here, '_scope_extra'))
try:
    import _scope_extmod
    print('2', _scope_extmod.EXT, _scope_extmod._scope_mod is _scope_mod)
except ImportError as e:
    print('2', type(e).__name__, e)
