# from-import of a name that a partially initialised module has not bound yet
try:
    import _scope_circ_x
except ImportError as e:
    print(type(e).__name__, str(e).split(' (')[0], e.name)
import sys
# the failed module is not left half-imported
print('_scope_circ_x' in sys.modules)
try:
    import _scope_circ_x
except ImportError as e:
    print('again:', type(e).__name__, str(e).split(' (')[0])
