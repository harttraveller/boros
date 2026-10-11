class PkgError(RuntimeError):
    pass


def raise_it(msg):
    raise PkgError(msg)
