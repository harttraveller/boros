"""Low-level exception support: mapping host exceptions to interpreted values and
recording interpreted traceback lines.

Interpreted programs raise and catch real host exceptions.  When an interpreted
class derives from Exception, its Instance carries a native host exception
object (`Instance.native`) which is what is actually raised; that object points
back to its Instance through the attribute INST_KEY.  As an exception
propagates out of interpreted frames, each frame appends its current line to a
list stored on the exception under TB_KEY, from which the runtime prints an
interpreted traceback.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .objects import MISSING

if TYPE_CHECKING:
    from collections.abc import Callable

    from ..core_types import Frame
    from .objects import Function

    TracebackLine = tuple[Frame, int, str, str]
    """One interpreted traceback entry: (frame, line, function name, filename)."""

# Attribute names used to attach interpreter data to host exception objects.
# They include an id so that nested copies of the interpreter (which share
# the host's exception objects) do not see each other's annotations.
LEVEL: str = f'{id(MISSING):x}'


INST_KEY: str = '_boros_inst_' + LEVEL


TB_KEY: str = '_boros_tb_' + LEVEL


def annotate_call(e: BaseException, fr: Frame, f: Function) -> None:
    """annotate() for an exception leaving the body of interpreted function f."""
    code: Any = f.code
    annotate(e, fr, code.line, code.name, code.filename)


def exc_value(e: BaseException) -> Any:
    """The interpreted value of a host exception: the Instance it stands for
    if it is the native part of an interpreted exception, else itself."""
    v: Any = getattr(e, INST_KEY, None)
    if v is None:
        return e
    return v


def exc_triple(args: tuple[Any, ...]) -> tuple[Any, ...]:
    """The (exc_type, exc, traceback) arguments that host code passes to an
    exit callback (contextlib.ExitStack), with a host exception standing for
    an interpreted one replaced by that Instance and its host type by the
    Instance's class."""
    e: Any = args[1]
    v: Any = exc_value(e)
    if v is e:
        return args
    t: Any = v.cls if args[0] is type(e) else args[0]
    return (t, v, args[2])


NATIVE_EXC_ATTRS: dict[str, int] = {'__cause__': 1, '__context__': 1, 'exceptions': 1, 'with_traceback': 1}
"""Attributes of host exceptions whose values involve other host exceptions
(or the exception itself), which interpreted code must see as the
interpreted exceptions they stand for (used as a set; see exc_attr_value)."""


def exc_attr_value(name: str, r: Any) -> Any:
    """The interpreted view of the value r of attribute `name` (one of
    NATIVE_EXC_ATTRS) read from a host exception."""
    if name == 'with_traceback':
        return wrap_with_traceback(r)
    if name == 'exceptions':
        return tuple([exc_value(x) for x in r])
    return exc_value(r)


def wrap_with_traceback(m: Callable[[Any], BaseException]) -> Callable[[Any], Any]:
    """e.with_traceback for the native part of an interpreted exception:
    m is the native's bound method, which returns the native itself."""
    def with_traceback(tb: Any) -> Any:
        return exc_value(m(tb))
    return with_traceback


EXC_REPR: Any = BaseException.__dict__['__repr__']
"""The host BaseException.__repr__, which names the type of the host object;
for the native part of an interpreted exception that is the host base class,
so the runtime uses exc_repr instead."""


def exc_repr(name: str, args: tuple[Any, ...]) -> str:
    """BaseException.__repr__ for an exception of the class named `name` with
    arguments args: Name('arg') or Name(arg1, arg2, ...)."""
    if len(args) == 1:
        return f'{name}({args[0]!r})'
    return name + repr(args)


def annotate(e: BaseException, fr: Frame, line: int, name: str, filename: str) -> None:
    """Record the innermost line of frame fr in the interpreted traceback
    carried by host exception e.  Called by compiled code as the exception
    propagates, so entries run from the innermost frame outwards."""
    try:
        tb: list[TracebackLine] | None = getattr(e, TB_KEY, None)
        if tb is None:
            tb = []
            setattr(e, TB_KEY, tb)
        elif tb[-1][0] is fr:
            # Nested compiled blocks of one frame each catch the exception on
            # its way out; the innermost one recorded the most precise line.
            return
        tb.append((fr, line, name, filename))
    except AttributeError:
        # exceptions that do not accept new attributes get no traceback
        pass


def unbound_local(name: str) -> UnboundLocalError:
    """The error for reading local variable `name` before it is assigned."""
    return UnboundLocalError(f"cannot access local variable '{name}' where it is not associated with a value")


def unbound_free(name: str) -> NameError:
    """The error for reading free variable `name` before the enclosing scope assigns it."""
    return NameError(f"cannot access free variable '{name}' where it is not associated with a value in enclosing "
                     'scope', name=name)


def unpack_error(n: int, expected: int) -> ValueError:
    """The error for unpacking `n` values into `expected` targets (Python
    3.13 does not report the count in the too-many case)."""
    if n < expected:
        return ValueError(f'not enough values to unpack (expected {expected}, got {n})')
    return ValueError(f'too many values to unpack (expected {expected})')


# filename -> source lines, for tracebacks
SOURCES: dict[str, list[str]] = {}
