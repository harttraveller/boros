"""async for over classes with __aiter__/__anext__, async with over classes
with __aenter__/__aexit__, custom awaitables with __await__."""
import asyncio


class Ticker:
    """Async iterator yielding 0..n-1, awaiting between items."""

    def __init__(self, n):
        self.n = n
        self.i = 0

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self.i >= self.n:
            raise StopAsyncIteration
        await asyncio.sleep(0)
        self.i += 1
        return self.i - 1


async def use_ticker():
    out = []
    async for t in Ticker(4):
        out.append(t)
    return out


print(asyncio.run(use_ticker()))

# async for with break / continue / else
async def loop_control():
    out = []
    async for t in Ticker(10):
        if t == 1:
            continue
        if t == 4:
            break
        out.append(t)
    else:
        out.append('else not reached')
    async for t in Ticker(2):
        out.append('second %d' % t)
    else:
        out.append('else reached')
    return out


print(asyncio.run(loop_control()))

# __aiter__ returning a separate iterator object; __anext__ returning an awaitable
class Pages:
    def __init__(self, pages):
        self.pages = pages

    def __aiter__(self):
        return PagesIter(self.pages)


class PagesIter:
    def __init__(self, pages):
        self.it = iter(pages)

    def __anext__(self):
        try:
            v = next(self.it)
        except StopIteration:
            return self._stop()
        return self._value(v)

    async def _value(self, v):
        await asyncio.sleep(0)
        return v.upper()

    async def _stop(self):
        raise StopAsyncIteration


async def use_pages():
    return await collect(Pages(['a', 'b', 'c']))


async def collect(ait):
    out = []
    async for x in ait:
        out.append(x)
    return out


print(asyncio.run(use_pages()))

# tuple unpacking target in async for
class PairStream:
    def __init__(self):
        self.items = [(1, 'one'), (2, 'two')]

    def __aiter__(self):
        self.idx = 0
        return self

    async def __anext__(self):
        if self.idx == len(self.items):
            raise StopAsyncIteration
        self.idx += 1
        return self.items[self.idx - 1]


async def unpack_pairs():
    out = []
    async for num, name in PairStream():
        out.append('%s=%d' % (name, num))
    return out


print(asyncio.run(unpack_pairs()))

# async with
class Resource:
    def __init__(self, name, log, suppress=False):
        self.name = name
        self.log = log
        self.suppress = suppress

    async def __aenter__(self):
        await asyncio.sleep(0)
        self.log.append('enter ' + self.name)
        return self.name.upper()

    async def __aexit__(self, typ, val, tb):
        await asyncio.sleep(0)
        self.log.append('exit %s %s %s' % (self.name, typ.__name__ if typ else None, val))
        return self.suppress


async def use_resources():
    log = []
    async with Resource('a', log) as a, Resource('b', log) as b:
        log.append('body %s %s' % (a, b))
    async with Resource('s', log, suppress=True):
        raise KeyError('suppressed')
    log.append('after suppress')
    try:
        async with Resource('p', log):
            raise ValueError('propagates')
    except ValueError as e:
        log.append('caught %s' % e)
    return log


for line in asyncio.run(use_resources()):
    print(line)

# return / break inside async with run __aexit__
async def early_exit():
    log = []
    for i in range(3):
        async with Resource('loop%d' % i, log):
            if i == 1:
                break
    async def inner():
        async with Resource('ret', log):
            return 'returned'
    log.append(await inner())
    return log


print(asyncio.run(early_exit()))

# custom awaitable via __await__ (a generator method)
class Delay:
    def __init__(self, value):
        self.value = value

    def __await__(self):
        yield from asyncio.sleep(0).__await__()
        return self.value * 2


async def use_awaitable():
    a = await Delay(5)
    b = await Delay('x')
    return a, b


print(asyncio.run(use_awaitable()))

# __await__ returning an iterator of a host future
class FutureWrapper:
    def __init__(self, fut):
        self.fut = fut

    def __await__(self):
        return self.fut.__await__()


async def use_future():
    loop = asyncio.get_running_loop()
    fut = loop.create_future()
    loop.call_soon(fut.set_result, 'future value')
    return await FutureWrapper(fut)


print(asyncio.run(use_future()))

# awaiting asyncio primitives inside async iteration and context managers together
class Locked:
    def __init__(self):
        self.lock = asyncio.Lock()

    async def __aenter__(self):
        await self.lock.acquire()
        return self

    async def __aexit__(self, *exc):
        self.lock.release()
        return False


async def locked_counter():
    res = Locked()
    counter = [0]

    async def bump():
        async with res:
            v = counter[0]
            await asyncio.sleep(0)
            counter[0] = v + 1

    await asyncio.gather(*[bump() for _ in range(5)])
    return counter[0], res.lock.locked()


print(asyncio.run(locked_counter()))

# async for over an async iterator whose __anext__ raises a normal exception
class Broken:
    def __aiter__(self):
        return self

    async def __anext__(self):
        raise RuntimeError('broken stream')


async def use_broken():
    try:
        async for _ in Broken():
            pass
    except RuntimeError as e:
        return 'caught %s' % e


print(asyncio.run(use_broken()))
