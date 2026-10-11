"""The _scope_pkg package."""
print('init _scope_pkg', __name__, __package__)
PKG_CONST = 'pkg-const'
from . import alpha
from .alpha import alpha_func as af


def pkg_func():
    return 'pkg_func'
