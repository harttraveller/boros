"""Generator, coroutine and async generator objects of interpreted functions.

The body of an interpreted generator function runs as a chain of host
generators linked by `yield from` (see compiler/generators.py).  Two host
rules get in the way of running interpreted code inside such a chain:

* close() (and throw(GeneratorExit)) on a generator suspended in `yield
  from` closes the delegated-to generator first and then raises
  GeneratorExit in every outer link of the chain, so an interpreted
  `except GeneratorExit` could not continue, yield again or return a
  value.  `drive` therefore runs the chain with a plain `yield` and
  delivers close() into it as an ordinary exception, GenClose, which the
  innermost interpreted yield point turns back into a GeneratorExit.  (The
  compiler uses drive only for bodies whose try or with statements could
  stop that GeneratorExit, and for async generators.)
* a StopIteration leaving any host generator frame becomes RuntimeError
  (PEP 479), long before it reaches the interpreted generator's own
  try/except.  Interpreted code inside the chain therefore raises it as a
  StopCarrier, which `except` clauses see as the StopIteration it carries;
  only the outermost frame turns an uncaught one into RuntimeError.

The coroutine object of an `async def` function is a real host coroutine,
made by the `async def coroutine` below, so that asyncio, inspect and the
host's coroutine error messages accept it at every level of the
interpreter tower (when boros runs itself, `coroutine` is itself
interpreted, and the coroutine it returns is the outer level's, which is
again a host coroutine).  An `async def` containing `yield` returns an
`async_generator`.
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING, Any

from .errors import INST_KEY, exc_value
from .objects import RETURN, Class, Instance

if TYPE_CHECKING:
    from collections.abc import Callable, Generator, Iterator

    from ..core_types import Frame


class GenClose(BaseException):
    """Delivers close() to the chain of host generators running an
    interpreted generator (see the module docstring)."""


class StopCarrier(BaseException):
    """Carries a StopIteration raised by interpreted code across the host
    generator frames running an interpreted generator.  `exc` is the
    StopIteration, which is also what exc_value() of the carrier gives."""

    exc: BaseException


def carry_stop(e: BaseException) -> StopCarrier:
    """The StopCarrier for StopIteration e."""
    c: StopCarrier = StopCarrier()
    c.exc = e
    setattr(c, INST_KEY, exc_value(e))
    return c


STOP_MESSAGES: tuple[str, ...] = ('generator raised StopIteration', 'generator raised StopIteration',
                                  'coroutine raised StopIteration', 'async generator raised StopIteration')
"""The RuntimeError message for a StopIteration escaping a generator body
of each kind: 0 a generator, 1 a generator lambda, 2 a coroutine, 3 an
async generator."""


def drive(g: Generator[Any, Any, Any], fr: Frame, kind: int) -> Generator[Any, Any, Any]:
    """The host generator that is an interpreted generator (or the body of a
    coroutine or async generator; kind as in STOP_MESSAGES): runs g, the
    chain of host generators executing the body, passing send() and
    throw() on, delivering close() as GenClose and applying PEP 479.  Its
    return value is the generator's return value."""
    try:
        send: Callable[[Any], Any] = g.send
        x: Any = send(None)
        while True:
            thrown: BaseException | None = None
            try:
                while True:
                    s: Any = yield x
                    x = send(s)
            except BaseException as e:
                if finished(g):
                    raise  # raised by the body, which has finished (handled below)
                thrown = e
            # Thrown in at the yield: passed on outside the except clause, so
            # that the body does not see it as the exception being handled.
            x = drive_throw(g, thrown)
    except StopIteration as e:
        r: Any = e.value
        if kind == 1:
            return r
        if r is RETURN:
            return fr['.rv']
        return None
    except StopCarrier as c:
        raise RuntimeError(STOP_MESSAGES[kind]) from c.exc
    except GenClose:
        pass
    raise GeneratorExit


def finished(g: Any) -> bool:
    """Whether generator g has finished (an exception raised by its body
    finishes it; one thrown into the generator delegating to it does not)."""
    return g.gi_frame is None


def drive_throw(g: Generator[Any, Any, Any], e: BaseException) -> Any:
    """Throw e, which was thrown into drive(), into the body g; returns the
    next value the body yields."""
    if isinstance(e, GeneratorExit):
        # close(): if the body yields again, the host close() raises RuntimeError
        return g.throw(GenClose())
    if type(e) is GenClose:
        # closed by an interpreted generator delegating to this one: once
        # the body has finished, GeneratorExit goes on in the delegator
        try:
            g.throw(GenClose())
        except (GeneratorExit, StopIteration):
            raise GeneratorExit from None
        raise RuntimeError('generator ignored GeneratorExit')
    return g.throw(e)


EXC_ARG_METHODS: dict[str, int] = {'throw': 1, 'set_exception': 1}
"""Names of the methods of host objects that take an exception: throw() of
generators and coroutines, set_exception() of futures (used as a set).
Calls of these methods are compiled to pass host exceptions (see
native_exc_args)."""


def native_exc_args(args: tuple[Any, ...]) -> tuple[Any, ...]:
    """The arguments of a call of throw() or set_exception() of a host
    object with an interpreted exception (class or instance) replaced by the
    host exception standing for it, which is what host code can raise.  The
    old throw(type, value[, traceback]) form passes the value."""
    from .exceptions import to_native_exc
    if len(args) > 1 and args[1] is not None:
        typ: Any = args[0]
        val: Any = args[1]
        if is_interpreted_exc(val):
            v: BaseException = to_native_exc(val)
        elif type(typ) is Class and is_interpreted_exc(typ):
            v = to_native_exc(typ(*val) if type(val) is tuple else typ(val))
        else:
            return args
        return (type(v), v) + args[2:]
    if args and is_interpreted_exc(args[0]):
        return (to_native_exc(args[0]),) + args[1:]
    return args


def is_interpreted_exc(a: Any) -> bool:
    """Whether a is an interpreted exception class or an instance of one."""
    if type(a) is Instance:
        return isinstance(a.native, BaseException)
    return type(a) is Class and BaseException in a.mro


def await_value(a: Iterator[Any]) -> Generator[Any, Any, Any]:
    """`yield from a`, an awaitable's iterator (see protocols.await_iter),
    at an interpreted await: a StopIteration thrown in is carried and a
    close() delivered as GenClose becomes GeneratorExit."""
    try:
        v: Any = yield from a
        return v
    except StopIteration as e:
        raise carry_stop(e) from None
    except GenClose:
        raise GeneratorExit from None


# -- coroutines ---------------------------------------------------------------------


class AwaitBody:
    """An awaitable over the host generator running a coroutine body."""

    __slots__ = ('g',)

    def __init__(self, g: Generator[Any, Any, Any]) -> None:
        self.g: Generator[Any, Any, Any] = g

    def __await__(self) -> Generator[Any, Any, Any]:
        return self.g


async def coroutine(body: AwaitBody) -> Any:
    """The coroutine object returned by calling an `async def` function:
    a host coroutine running the body."""
    return await body


# -- async generators -------------------------------------------------------------


class AsyncGenYield:
    """What the host generator running an async generator's body yields for
    `yield value`.  Anything else it yields comes from an `await` and is
    passed on to the event loop."""

    __slots__ = ('value',)

    def __init__(self, value: Any) -> None:
        self.value: Any = value


def agen_yield(v: Any) -> Generator[Any, Any, Any]:
    """`yield v` in an async generator; returns the value sent in."""
    try:
        s: Any = yield AsyncGenYield(v)
        return s
    except StopIteration as e:
        raise carry_stop(e) from None
    except GenClose:
        raise GeneratorExit from None


AGEN_NEXT: int = 0
AGEN_THROW: int = 1
AGEN_CLOSE: int = 2
"""The operations of an async generator step: __anext__ / asend(), athrow() and aclose()."""


class async_generator:  # the type name programs see, as in CPython
    """The object returned by calling an `async def` that contains `yield`.

    ag_gen is the drive() generator running the body; state is 0 before
    the first step, 1 once started and 2 when finished.  Each of
    __anext__, asend, athrow and aclose returns a host coroutine (see
    agen_step) so that asyncio accepts it, for example when the event loop
    finalizes an abandoned async generator with create_task(ag.aclose())."""

    def __init__(self, g: Generator[Any, Any, Any]) -> None:
        self.ag_gen: Generator[Any, Any, Any] = g
        self.ag_running: bool = False
        self.state: int = 0
        self.finalizer: Callable[[Any], Any] | None = None
        self.__name__: str = '<genexpr>'
        self.__qualname__: str = '<genexpr>'

    def __aiter__(self) -> async_generator:
        return self

    def __anext__(self) -> Any:
        return coroutine(AwaitBody(agen_step(self, AGEN_NEXT, None)))

    def asend(self, value: Any) -> Any:
        return coroutine(AwaitBody(agen_step(self, AGEN_NEXT, value)))

    def athrow(self, typ: Any, val: Any = None, tb: Any = None) -> Any:
        return coroutine(AwaitBody(agen_step(self, AGEN_THROW, typ if val is None else val)))

    def aclose(self) -> Any:
        return coroutine(AwaitBody(agen_step(self, AGEN_CLOSE, None)))

    def __repr__(self) -> str:
        return f'<async_generator object {self.__qualname__} at 0x{id(self):x}>'

    def __del__(self) -> None:
        # an abandoned async generator is closed by its event loop's finalizer
        if self.state == 1 and self.finalizer is not None:
            self.finalizer(self)


def agen_step(ag: async_generator, op: int, arg: Any) -> Generator[Any, Any, Any]:
    """Run async generator ag up to its next `yield` (or its end): op is
    AGEN_NEXT (send arg), AGEN_THROW (throw arg) or AGEN_CLOSE.  The awaits
    of the body are passed through to the event loop.  Returns the value
    yielded; the end of the body is StopAsyncIteration (None for aclose)."""
    if ag.state == 2:
        return agen_finished(op, arg)
    if ag.state == 0:
        agen_first_step(ag, op, arg)
    g: Generator[Any, Any, Any] = ag.ag_gen
    try:
        x: Any = yield from agen_until_yield(g, agen_resume(g, op, arg))
    except StopIteration:
        ag.state = 2
        if op == AGEN_CLOSE:
            return None
        raise StopAsyncIteration from None
    except GeneratorExit:
        ag.state = 2
        if op == AGEN_CLOSE:
            return None
        raise
    except StopAsyncIteration as e:
        ag.state = 2
        raise RuntimeError('async generator raised StopAsyncIteration') from e
    except BaseException:
        ag.state = 2
        raise
    if op == AGEN_CLOSE:
        raise RuntimeError('async generator ignored GeneratorExit')
    return x.value


def agen_finished(op: int, arg: Any) -> Any:
    """A step of an async generator that has finished."""
    if op == AGEN_CLOSE:
        return None
    if op == AGEN_THROW:
        from .exceptions import to_native_exc
        raise to_native_exc(arg)
    raise StopAsyncIteration


def agen_first_step(ag: async_generator, op: int, arg: Any) -> None:
    """Start async generator ag: check the first value sent and tell the
    event loop (sys.set_asyncgen_hooks) about it."""
    if op == AGEN_NEXT and arg is not None:
        raise TypeError("can't send non-None value to a just-started async generator")
    hooks: Any = sys.get_asyncgen_hooks()
    if hooks.firstiter is not None:
        hooks.firstiter(ag)
    ag.finalizer = hooks.finalizer
    ag.state = 1


def agen_resume(g: Generator[Any, Any, Any], op: int, arg: Any) -> Any:
    """Resume the body g of an async generator for operation op; returns
    what it yields next."""
    if op == AGEN_NEXT:
        return g.send(arg)
    if op == AGEN_THROW:
        from .exceptions import to_native_exc
        return g.throw(to_native_exc(arg))
    return g.throw(GeneratorExit())


def agen_until_yield(g: Generator[Any, Any, Any], x: Any) -> Generator[Any, Any, Any]:
    """Pass what the async generator body g yields for its awaits (x first)
    through to the event loop, and what the loop sends or throws back into
    g, until g yields an AsyncGenYield, which is returned."""
    while type(x) is not AsyncGenYield:
        thrown: BaseException | None = None
        try:
            s: Any = yield x
            x = g.send(s)
            continue
        except BaseException as e:
            if finished(g):
                raise  # raised by g, which has finished
            thrown = e
        # passed on outside the except clause, as in drive()
        x = g.throw(thrown)
    return x
