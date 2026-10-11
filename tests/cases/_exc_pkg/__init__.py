from .errors import PkgError


def explode():
    from . import errors
    errors.raise_it('package explosion')
