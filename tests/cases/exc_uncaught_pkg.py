# Uncaught exception raised in a submodule of a helper package.
import _exc_pkg

print(_exc_pkg.PkgError.__module__, issubclass(_exc_pkg.PkgError, RuntimeError))
_exc_pkg.explode()
