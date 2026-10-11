"""Interpreted async objects handed to host (asyncio / contextlib / builtin)
code: custom awaitables in gather/wait_for/ensure_future, aiter()/anext()
on async iterator classes, AsyncExitStack with async context manager
classes.  Each check reports its own outcome."""
import asyncio
import contextlib
import inspect


def report(label, fn):
    try:
        print(label, 'ok', fn())
    except BaseException as e:
        print(label, type(e).__name__, e)


class Delay:
    def __init__(self, v):
        self.v = v

    def __await__(self):
        yield from asyncio.sleep(0).__await__()
        return self.v * 2


async def gather_awaitables():
    return await asyncio.gather(Delay(1), Delay(2))


async def wait_for_awaitable():
    return await asyncio.wait_for(Delay(5), timeout=10)


async def ensure_future_awaitable():
    t = asyncio.ensure_future(Delay(7))
    return await t


report('gather(custom awaitables):', lambda: asyncio.run(gather_awaitables()))
report('wait_for(custom awaitable):', lambda: asyncio.run(wait_for_awaitable()))
report('ensure_future(custom awaitable):', lambda: asyncio.run(ensure_future_awaitable()))
report('inspect.isawaitable(custom awaitable):', lambda: inspect.isawaitable(Delay(1)))


class Countdown:
    def __init__(self, n):
        self.n = n

    def __aiter__(self):
        return self

    async def __anext__(self):
        await asyncio.sleep(0)
        if self.n <= 0:
            raise StopAsyncIteration
        self.n -= 1
        return self.n


async def builtin_aiter_anext():
    it = aiter(Countdown(2))
    return [await anext(it), await anext(it), await anext(it, 'end')]


report('aiter()/anext() builtins:', lambda: asyncio.run(builtin_aiter_anext()))

class NotAsyncIterable:
    pass


async def aiter_error():
    return aiter(NotAsyncIterable())


report('aiter() on a plain object:', lambda: asyncio.run(aiter_error()))


class Conn:
    def __init__(self, name, log):
        self.name = name
        self.log = log

    async def __aenter__(self):
        await asyncio.sleep(0)
        self.log.append('open ' + self.name)
        return self

    async def __aexit__(self, typ, val, tb):
        self.log.append('close %s %s' % (self.name, typ.__name__ if typ else None))
        return False


async def async_exit_stack():
    log = []
    async with contextlib.AsyncExitStack() as stack:
        for n in ('a', 'b'):
            await stack.enter_async_context(Conn(n, log))
        log.append('body')
    return log


report('AsyncExitStack with interpreted managers:', lambda: asyncio.run(async_exit_stack()))
