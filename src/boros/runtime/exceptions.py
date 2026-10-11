"""Raising, matching and printing interpreted exceptions.

Whatever propagates through interpreted code is a host exception object.
An interpreted exception (an Instance of a class derived from
BaseException) travels as its `native` part, a host exception that points
back to the Instance (see calls.make_native and errors.exc_value).

This module turns the operand of a `raise` statement into the host
exception to raise, decides whether an exception matches the type of an
`except` clause, and prints an uncaught exception the way CPython does,
using the interpreted traceback that errors.annotate records on the host
exception as it propagates out of interpreted frames.
"""

from __future__ import annotations

import contextlib
import sys
from typing import TYPE_CHECKING, Any

from .attributes import getattr_any
from .calls import instantiate, type_of
from .errors import NATIVE_EXC_ATTRS, SOURCES, TB_KEY, exc_attr_value, exc_value
from .objects import Class, Instance
from .suggestions import name_error_hint
from .typechecks import b_issubclass

if TYPE_CHECKING:
    from collections.abc import Callable
    from types import TracebackType
    from typing import Self

NOT_AN_EXCEPTION: str = 'exceptions must derive from BaseException'
"""The error message for raising something that is not an exception."""

CAUSE_MESSAGE: str = '\nThe above exception was the direct cause of the following exception:\n\n'
"""Printed between an exception and the one raised `from` it."""

CONTEXT_MESSAGE: str = '\nDuring handling of the above exception, another exception occurred:\n\n'
"""Printed between an exception and one raised while handling it."""


# -- raising and matching ------------------------------------------------------

def to_native_exc(v: Any) -> BaseException:
    """The host exception object that `raise v` raises.

    v may be an interpreted exception instance (its native part is raised),
    an interpreted exception class (instantiated without arguments), a host
    exception, or a host exception class (likewise instantiated)."""
    t: type = type(v)
    if t is Instance:
        n: Any = v.native
        if n is None or not isinstance(n, BaseException):
            raise TypeError(NOT_AN_EXCEPTION)
        return n
    if t is Class:
        if not b_issubclass(v, BaseException):
            raise TypeError(NOT_AN_EXCEPTION)
        return to_native_exc(instantiate(v, (), None))
    if isinstance(v, BaseException):
        return v
    if isinstance(v, type) and issubclass(v, BaseException):
        return v()
    raise TypeError(NOT_AN_EXCEPTION)


def exc_matches(v: Any, typ: Any) -> bool:
    """Whether the exception value v (an Instance or a host exception, see
    errors.exc_value) is caught by `except typ`, where typ is an interpreted
    class, a host exception class, or a (flat) tuple of those.  As in
    CPython, every type is checked before any is matched."""
    tt: type = type(typ)
    if tt is tuple:
        for t in typ:
            check_except_type(t)
        for t in typ:
            if exc_matches(v, t):
                return True
        return False
    check_except_type(typ)
    if type(v) is Instance:
        return typ in v.cls.mro
    if tt is Class:
        return False
    return isinstance(v, typ)


def check_except_type(t: Any) -> None:
    """Reject a type in an except clause that is not an exception class."""
    if type(t) is Class:
        ok: bool = BaseException in t.mro
    else:
        ok = isinstance(t, type) and issubclass(t, BaseException)
    if not ok:
        raise TypeError('catching classes that do not inherit from BaseException is not allowed')


# -- except* ------------------------------------------------------------------------
#
# The except* clauses of a try statement run in turn, each on the part of the
# exception that no earlier clause took: star_match splits that remainder by
# the clause's type, the clause's body runs with the matching part (an
# exception group) as the exception being handled, and star_result combines
# what the clauses raised and what none of them matched into the exception
# that propagates, following CPython (_PyEval_ExceptionGroupMatch and
# _PyExc_PrepReraiseStar).

class CatchAll:
    """A context manager that stops any exception raised in its body and
    keeps it in `caught`; it collects the exceptions that the clauses of an
    except* statement raise, since each clause runs even if one before it
    raised."""

    def __init__(self) -> None:
        self.caught: BaseException | None = None

    def __enter__(self) -> Self:
        return self

    def __exit__(self, typ: type[BaseException] | None, e: BaseException | None, tb: TracebackType | None) -> bool:
        self.caught = e
        return True


def check_star_type(typ: Any) -> None:
    """Reject the type (or tuple of types) of an except* clause that is not
    an exception class, or that is an exception group class."""
    types: Any = typ if type(typ) is tuple else (typ,)
    for t in types:
        check_except_type(t)
        group: bool = BaseExceptionGroup in t.mro if type(t) is Class else issubclass(t, BaseExceptionGroup)
        if group:
            raise TypeError('catching ExceptionGroup with except* is not allowed. Use except instead.')


def star_match(e: BaseException | None, typ: Any) -> tuple[BaseException | None, BaseException | None]:
    """(match, rest) for an except* clause of type typ, given the host
    exception e that earlier clauses left unhandled (None if they handled
    everything).  A matching exception that is not a group is wrapped in
    one; a group is split, leaf by leaf."""
    check_star_type(typ)
    if e is None:
        return None, None
    if exc_matches(exc_value(e), typ):
        if isinstance(e, BaseExceptionGroup):
            return e, None
        return BaseExceptionGroup('', (e,)), None
    if isinstance(e, BaseExceptionGroup):
        return e.split(star_matcher(typ))
    return None, e


def star_matcher(typ: Any) -> Callable[[BaseException], bool]:
    """The predicate for BaseExceptionGroup.split that selects the host
    exceptions caught by an except* clause of type typ (which may be an
    interpreted class, which the host's split does not understand)."""
    def matches(x: BaseException) -> bool:
        return exc_matches(exc_value(x), typ)
    return matches


def star_result(orig: BaseException, raised: list[tuple[BaseException, BaseException]],
                rest: BaseException | None) -> BaseException | None:
    """The exception that propagates from a try statement whose except*
    clauses handled host exception orig, or None if it was handled.
    raised holds (match, exception its clause raised) for each clause that
    raised; rest is what no clause matched.

    A clause that re-raises its match keeps those leaves of orig, as does
    rest; they propagate as a copy of orig restricted to them, grouped with
    the new exceptions the clauses raised, if any (a single exception
    propagates on its own)."""
    if not isinstance(orig, BaseExceptionGroup):
        # a naked exception: at most one clause ran (on the wrapped exception)
        return raised[0][1] if raised else rest
    keep: set[int] = set()
    new: list[BaseException] = []
    for match, x in raised:
        if x is match:
            add_leaf_ids(x, keep)
        else:
            new.append(x)
    if rest is not None:
        add_leaf_ids(rest, keep)
    kept: BaseException | None = orig.split(leaf_matcher(keep))[0] if keep else None
    if kept is not None:
        new.append(kept)
    if len(new) <= 1:
        return new[0] if new else None
    return BaseExceptionGroup('', new)


def add_leaf_ids(e: BaseException, ids: set[int]) -> None:
    """Add the ids of the exceptions in group e (or of e, if it is not a
    group) to ids."""
    if isinstance(e, BaseExceptionGroup):
        for x in e.exceptions:
            add_leaf_ids(x, ids)
    else:
        ids.add(id(e))


def leaf_matcher(ids: set[int]) -> Callable[[BaseException], bool]:
    """The split predicate selecting the exceptions whose ids are in ids."""
    def matches(x: BaseException) -> bool:
        return id(x) in ids
    return matches


# -- host attributes holding exceptions ------------------------------------------

def b_sys_exc_info() -> tuple[Any, Any, Any]:
    """sys.exc_info() for interpreted code: the exception being handled is
    the interpreted exception, not the host object that carries it."""
    e: BaseException | None = sys.exc_info()[1]
    if e is None:
        return (None, None, None)
    v: Any = exc_value(e)
    return (type_of(v), v, e.__traceback__)


def b_sys_exception() -> Any:
    """sys.exception() for interpreted code (see b_sys_exc_info)."""
    e: BaseException | None = sys.exception()
    return None if e is None else exc_value(e)


SYS_EXC_FUNCTIONS: dict[str, Any] = {'exc_info': b_sys_exc_info, 'exception': b_sys_exception}
"""What interpreted code gets for these functions of the sys module."""


SPECIAL_ATTRS: dict[str, int] = {'__cause__': 1, '__context__': 1, 'exceptions': 1, 'exc_info': 1, 'exception': 1}
"""Attribute names (used as a set) whose values, read from host objects, may
be host exceptions standing for interpreted ones: the exception attributes
of errors.NATIVE_EXC_ATTRS and the functions SYS_EXC_FUNCTIONS replaces.
The compiler reads attributes of these names with getattr_special, so
other attribute reads pay nothing for it."""


def getattr_special(o: Any, name: str) -> Any:
    """getattr_any(o, name), mapping host exceptions found in the attributes
    of host exceptions (__cause__, __context__, exceptions) to the
    interpreted exceptions they stand for, and replacing sys.exc_info and
    sys.exception."""
    if o is sys:
        f: Any = SYS_EXC_FUNCTIONS.get(name)
        if f is not None:
            return f
    r: Any = getattr_any(o, name)
    if name in NATIVE_EXC_ATTRS and isinstance(o, BaseException):
        return exc_attr_value(name, r)
    return r


# -- printing uncaught exceptions ----------------------------------------------

def qualified_type_name(v: Any) -> str:
    """The name of the type of exception value v as a traceback shows it:
    the qualified class name, prefixed by the module unless that is
    __main__ or builtins."""
    name: str
    mod: str | None
    if type(v) is Instance:
        cls: Class = v.cls
        name = cls.__qualname__
        mod = cls.__module__
    else:
        t: type = type(v)
        name = t.__qualname__
        mod = t.__module__
    if mod is not None and mod != '__main__' and mod != 'builtins':
        name = mod + '.' + name
    return name


def safe_str(v: Any) -> str:
    """str(v), or the placeholder CPython prints when str() of an exception
    itself raises."""
    msg: str = '<exception str() failed>'
    with contextlib.suppress(BaseException):
        msg = str(v)
    return msg


def exception_line(v: Any) -> str:
    """The final line of a traceback for exception value v, such as
    'ValueError: bad value' (just the type name when the message is empty)."""
    name: str = qualified_type_name(v)
    msg: str = safe_str(v)
    if msg:
        return f'{name}: {msg}'
    return name


def source_line(filename: str, line: int) -> str:
    """The stripped text of line `line` of a file the interpreter has run,
    or '' when the source is unknown."""
    src: list[str] | None = SOURCES.get(filename)
    if src is not None and 0 < line <= len(src):
        return src[line - 1].strip()
    return ''


def format_traceback(tb: list[tuple[Any, int, str, str]] | None) -> list[str]:
    """The 'Traceback (most recent call last):' block for an interpreted
    traceback: a list of (frame, line, function name, filename) entries,
    innermost first, as recorded by errors.annotate."""
    if not tb:
        return []
    out: list[str] = ['Traceback (most recent call last):\n']
    for entry in reversed(tb):
        line: int = entry[1]
        filename: str = entry[3]
        out.append(f'  File "{filename}", line {line}, in {entry[2]}\n')
        text: str = source_line(filename, line)
        if text:
            out.append(f'    {text}\n')
    return out


class PrintContext:
    """The state of printing an uncaught exception (like the host's
    traceback._ExceptionPrintContext): the ids of the exceptions already
    printed, and for exception groups, how deeply nested in groups the
    exception being printed is (each level indents its lines and draws a
    margin) and whether the innermost group's box still needs closing."""

    def __init__(self) -> None:
        self.seen: set[int] = set()
        self.depth: int = 0
        self.need_close: bool = False

    def emit(self, out: list[str], texts: list[str], margin: str = '|') -> None:
        """Append texts to out, each line indented for the current depth."""
        if not self.depth:
            out.extend(texts)
            return
        prefix: str = ' ' * (2 * self.depth) + margin + ' '
        for text in texts:
            for ln in text.splitlines(True):
                out.append(prefix + ln)


def format_chain(e: BaseException, ctx: PrintContext) -> list[str]:
    """The printout of the exception that e was raised from (its __cause__)
    or while handling (its __context__, unless suppressed), followed by the
    sentence linking the two.  Empty if there is none, or if it has already
    been printed (ctx.seen holds the ids of printed exceptions)."""
    out: list[str] = []
    cause: BaseException | None = e.__cause__
    context: BaseException | None = e.__context__
    if cause is not None and id(cause) not in ctx.seen:
        out.extend(format_exception(cause, ctx))
        ctx.emit(out, [CAUSE_MESSAGE])
    elif context is not None and not e.__suppress_context__ and id(context) not in ctx.seen:
        out.extend(format_exception(context, ctx))
        ctx.emit(out, [CONTEXT_MESSAGE])
    return out


def format_notes(e: BaseException) -> list[str]:
    """One line for each note added to e with add_note()."""
    notes: Any = getattr(e, '__notes__', None)
    if not notes:
        return []
    return [f'{note}\n' for note in notes]


def format_exception(e: BaseException, ctx: PrintContext | None = None) -> list[str]:
    """The text CPython prints for the uncaught host exception e, as a list
    of strings: the chained exceptions first, then e's interpreted
    traceback, its final line and its notes, and for an exception group,
    its exceptions in nested boxes."""
    if ctx is None:
        ctx = PrintContext()
    ctx.seen.add(id(e))
    out: list[str] = format_chain(e, ctx)
    tb: list[str] = format_traceback(getattr(e, TB_KEY, None))
    if not isinstance(e, BaseExceptionGroup):
        ctx.emit(out, tb)
        v: Any = exc_value(e)
        ctx.emit(out, [exception_line(v) + name_error_hint(e, v) + '\n', *format_notes(e)])
    elif ctx.depth > MAX_GROUP_DEPTH:
        ctx.emit(out, [f'... (max_group_depth is {MAX_GROUP_DEPTH})\n'])
    else:
        format_group(e, tb, ctx, out)
    return out


MAX_GROUP_WIDTH: int = 15
"""How many exceptions of a group are printed (the rest are counted)."""

MAX_GROUP_DEPTH: int = 10
"""How deeply nested exception groups are printed."""


def format_group(e: BaseExceptionGroup[Any], tb: list[str], ctx: PrintContext, out: list[str]) -> None:
    """Append the printout of exception group e, whose traceback is tb, to
    out: the group's own traceback and line, then a box for each of its
    exceptions."""
    toplevel: bool = ctx.depth == 0
    if toplevel:
        ctx.depth += 1
    if tb:
        ctx.emit(out, ['Exception Group Traceback (most recent call last):\n'], '+' if toplevel else '|')
        ctx.emit(out, tb[1:])
    ctx.emit(out, [exception_line(exc_value(e)) + '\n', *format_notes(e)])
    excs: tuple[BaseException, ...] = e.exceptions
    n: int = min(len(excs), MAX_GROUP_WIDTH + 1)
    ctx.need_close = False
    for i in range(n):
        format_group_member(excs, i, i == n - 1, ctx, out)
    if toplevel:
        ctx.depth = 0


def format_group_member(excs: tuple[BaseException, ...], i: int, last: bool, ctx: PrintContext,
                        out: list[str]) -> None:
    """Append the box holding exception i of a group's exceptions excs
    (past MAX_GROUP_WIDTH, the number of those not printed) to out."""
    if last:
        # a group nested in the last box may close the box itself
        ctx.need_close = True
    truncated: bool = i >= MAX_GROUP_WIDTH
    title: str = '...' if truncated else str(i + 1)
    out.append(' ' * (2 * ctx.depth) + ('+-' if i == 0 else '  ') + f'+---------------- {title} ----------------\n')
    ctx.depth += 1
    if truncated:
        remaining: int = len(excs) - MAX_GROUP_WIDTH
        ctx.emit(out, [f"and {remaining} more exception{'s' if remaining > 1 else ''}\n"])
    else:
        out.extend(format_exception(excs[i], ctx))
    if last and ctx.need_close:
        out.append(' ' * (2 * ctx.depth) + '+------------------------------------\n')
        ctx.need_close = False
    ctx.depth -= 1


def print_exception(e: BaseException) -> None:
    """Print the traceback of the uncaught exception e to stderr."""
    sys.stderr.write(''.join(format_exception(e)))
    sys.stderr.flush()
