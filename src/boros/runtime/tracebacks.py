"""The traceback module as interpreted programs see it.

The host's traceback module cannot format interpreted exceptions: it is
given Instance objects, or the host exceptions standing for them (whose type
is the host base class), and it shows the host's frames, which are the
interpreter's.  So `import traceback` in an interpreted program gives a copy
of the host module whose functions that format and print exceptions use the
interpreter's own formatting (runtime.exceptions): the interpreted class
names and the interpreted traceback.  Its other functions are the host's.
"""

from __future__ import annotations

import importlib
import sys
import types
from typing import Any

from . import exceptions
from .errors import INST_KEY, exc_value
from .objects import MISSING, Instance


def host_exception(exc: Any, value: Any) -> Any:
    """The exception that a call such as format_exception(exc) or
    format_exception(type, value, tb) is about, as a host object (the native
    part of an interpreted exception); value is MISSING if not given."""
    v: Any = exc if value is MISSING else value
    if type(v) is Instance and isinstance(v.native, BaseException):
        return v.native
    return v


def host_formats(e: Any) -> bool:
    """Whether the host's formatting is right for e: not an exception at
    all (None), or a host SyntaxError, whose report shows the source line."""
    return not isinstance(e, BaseException) or (isinstance(e, SyntaxError) and getattr(e, INST_KEY, None) is None)


def tb_format_exception_only(exc: Any, /, value: Any = MISSING, *, show_group: bool = False) -> list[str]:
    """traceback.format_exception_only: the exception's final traceback
    line, followed by its notes."""
    e: Any = host_exception(exc, value)
    if host_formats(e):
        return importlib.import_module('traceback').format_exception_only(e, show_group=show_group)
    return [exceptions.exception_line(exc_value(e)) + '\n', *exceptions.format_notes(e)]


def tb_format_exception(exc: Any, /, value: Any = MISSING, tb: Any = MISSING, limit: int | None = None,
                        chain: bool = True) -> list[str]:
    """traceback.format_exception: what an uncaught exception prints."""
    e: Any = host_exception(exc, value)
    if not isinstance(e, BaseException):
        return tb_format_exception_only(e)
    return exceptions.format_exception(e)


def tb_print_exception(exc: Any, /, value: Any = MISSING, tb: Any = MISSING, limit: int | None = None,
                       file: Any = None, chain: bool = True) -> None:
    """traceback.print_exception, to sys.stderr by default."""
    (sys.stderr if file is None else file).write(''.join(tb_format_exception(exc, value)))


def tb_format_exc(limit: int | None = None, chain: bool = True) -> str:
    """traceback.format_exc: format the exception being handled."""
    e: BaseException | None = sys.exception()
    if e is None:
        return 'NoneType: None\n'
    return ''.join(exceptions.format_exception(e))


def tb_print_exc(limit: int | None = None, file: Any = None, chain: bool = True) -> None:
    """traceback.print_exc: print the exception being handled."""
    (sys.stderr if file is None else file).write(tb_format_exc())


def traceback_module() -> types.ModuleType:
    """A new module like the host's traceback module, with the functions
    that format exceptions replaced by the interpreter's."""
    host: types.ModuleType = importlib.import_module('traceback')
    m: types.ModuleType = types.ModuleType('traceback', host.__doc__)
    m.__dict__.update(host.__dict__)
    m.__dict__.update({'format_exception_only': tb_format_exception_only, 'format_exception': tb_format_exception,
                       'print_exception': tb_print_exception, 'format_exc': tb_format_exc,
                       'print_exc': tb_print_exc})
    return m
