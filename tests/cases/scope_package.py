import os
import _scope_pkg
print(_scope_pkg.__name__, _scope_pkg.__package__)
print(os.path.basename(_scope_pkg.__file__))
print([os.path.basename(p) for p in _scope_pkg.__path__])
print(_scope_pkg.PKG_CONST, _scope_pkg.pkg_func(), _scope_pkg.af())
print(_scope_pkg.alpha.ALPHA, _scope_pkg.alpha.__name__, _scope_pkg.alpha.__package__)
print(hasattr(_scope_pkg, 'beta'))
print(_scope_pkg.alpha.lazy_beta())
print(hasattr(_scope_pkg, 'beta'), _scope_pkg.beta.BETA)
import _scope_pkg.sub.deep
print(_scope_pkg.sub.deep.DEEP)
print(_scope_pkg.sub.__name__, _scope_pkg.sub.deep.__name__, _scope_pkg.sub.deep.__package__)
import _scope_pkg.sub.deep as dp
print(dp is _scope_pkg.sub.deep)
from _scope_pkg import sub
from _scope_pkg.sub import sibling, SUB_CONST
print(sub.SUB_CONST, sibling.SIB, SUB_CONST)
from _scope_pkg.sub.deep import DEEP as D2
print(D2 == dp.DEEP)
print(os.path.basename(os.path.dirname(dp.__file__)), os.path.basename(dp.__file__))
# __import__ with and without fromlist
top = __import__('_scope_pkg.sub.sibling')
leaf = __import__('_scope_pkg.sub.sibling', fromlist=['SIB'])
print(top is _scope_pkg, leaf is _scope_pkg.sub.sibling, leaf.SIB)
rel = __import__('sibling', globals={'__name__': '_scope_pkg.sub.x', '__package__': '_scope_pkg.sub'}, fromlist=['SIB'], level=1)
print(rel is leaf)
here = os.path.dirname(os.path.abspath(__file__)) + os.sep
print(repr(_scope_pkg).replace(here, ''), repr(dp).replace(here, ''))
print(repr(os.path).startswith("<module 'posixpath'") or repr(os.path).startswith("<module 'ntpath'"))
