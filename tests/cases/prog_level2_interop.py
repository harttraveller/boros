"""Everyday host-library interop that works when boros runs a program but
breaks when boros runs boros running the program, because at that level the
inner interpreter's functions, classes and coroutines are themselves
interpreted objects: functools.wraps/update_wrapper and abc.abstractmethod
set attributes on functions from host code, inspect.getdoc reads __doc__
from host code, asyncio checks for a coroutine, and a dict subclass routes
attribute assignment to dict.__setitem__. Sections are independent."""
import abc
import asyncio
import functools
import inspect


def section(name):
    def deco(fn):
        try:
            print(name + ":", fn())
        except Exception as e:
            print(name + ": raised", type(e).__name__, e)
        return fn
    return deco


def logged(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        return ("logged", fn(*args, **kwargs))
    return wrapper


@section("wraps")
def _():
    @logged
    def area(w, h):
        """Area of a rectangle."""
        return w * h
    return area(3, 4), area.__name__, area.__doc__, area.__wrapped__.__name__, area.__module__


@section("update_wrapper")
def _():
    def target():
        """target doc"""
    def proxy():
        return "proxied"
    functools.update_wrapper(proxy, target)
    return proxy.__name__, proxy.__doc__, proxy.__qualname__.split(".")[-1], proxy()


@section("partial")
def _():
    def power(base, exp):
        return base ** exp
    square = functools.partial(power, exp=2)
    return square(7), square.func is power, square.keywords


@section("abstractmethod flag")
def _():
    class Base:
        @abc.abstractmethod
        def run(self):
            """Run it."""
    return Base.run.__isabstractmethod__, Base.run.__name__


@section("function attributes")
def _():
    def handler():
        pass
    setattr(handler, "priority", 5)
    handler.tags = ["a"]
    return getattr(handler, "priority"), handler.tags, handler.__dict__["priority"]


@section("getdoc")
def _():
    def documented():
        """Line one.

        Indented detail."""
    class Thing:
        """A thing."""
        def method(self):
            """Do the thing."""
    return inspect.getdoc(documented), inspect.getdoc(Thing.method), Thing.__doc__


@section("asyncio.run")
def _():
    async def compute(n):
        await asyncio.sleep(0)
        return n * 2

    async def main():
        return await asyncio.gather(compute(1), compute(2))
    return asyncio.run(main())


@section("attr dict")
def _():
    class Record(dict):
        __setattr__ = dict.__setitem__
    r = Record(a=1)
    r.b = 2
    return sorted(r.items())


@section("lru_cache")
def _():
    @functools.lru_cache(maxsize=8)
    def fib(n):
        return n if n < 2 else fib(n - 1) + fib(n - 2)
    return fib(30), fib.cache_info().hits, fib.__name__


@section("cached_property")
def _():
    class Data:
        calls = 0

        @functools.cached_property
        def total(self):
            Data.calls += 1
            return 42
    d = Data()
    return d.total, d.total, Data.calls
