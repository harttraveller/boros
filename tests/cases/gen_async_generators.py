"""Asynchronous generators (async def containing yield): async for,
asend/athrow/aclose, aiter()/anext(), async generator expressions and
contextlib.asynccontextmanager."""
import asyncio
import contextlib


async def ticker(n):
    for i in range(n):
        await asyncio.sleep(0)
        yield i


async def main_basic():
    out = []
    async for t in ticker(4):
        out.append(t)
    return out


print('basic', asyncio.run(main_basic()))

# object protocol
async def main_protocol():
    ag = ticker(2)
    names = (type(ag).__name__, ag.__name__, ag.__qualname__)
    has = (hasattr(ag, '__aiter__'), hasattr(ag, '__anext__'), hasattr(ag, 'asend'),
           hasattr(ag, 'athrow'), hasattr(ag, 'aclose'))
    first = await ag.__anext__()
    second = await anext(ag)
    try:
        await anext(ag)
    except StopAsyncIteration:
        done = 'StopAsyncIteration'
    dflt = await anext(ag, 'default')
    return names, has, first, second, done, dflt, aiter(ag) is ag


print('protocol', asyncio.run(main_protocol()))

# asend
async def accumulator():
    total = 0
    while True:
        v = yield total
        if v is None:
            return
        total += v


async def main_asend():
    ag = accumulator()
    out = [await ag.asend(None)]
    for v in (5, 10, 20):
        out.append(await ag.asend(v))
    try:
        await ag.asend(None)
    except StopAsyncIteration:
        out.append('stopped')
    return out


print('asend', asyncio.run(main_asend()))

# athrow / aclose and finally blocks
async def guarded(log):
    try:
        while True:
            try:
                yield 'tick'
            except ValueError as e:
                log.append('handled %s' % e)
                yield 'after error'
    finally:
        await asyncio.sleep(0)
        log.append('cleanup')


async def main_athrow():
    log = []
    ag = guarded(log)
    log.append(await ag.__anext__())
    log.append(await ag.athrow(ValueError('v')))
    log.append(await ag.__anext__())
    await ag.aclose()
    log.append(await anext(ag, 'closed'))
    return log


print('athrow', asyncio.run(main_athrow()))

# break out of async for, then explicitly close
async def main_break():
    log = []
    ag = guarded(log)
    async for v in ag:
        log.append(v)
        break
    await ag.aclose()
    return log


print('break', asyncio.run(main_break()))

# async generator delegating with async for to another
async def evens(n):
    async for t in ticker(n):
        if t % 2 == 0:
            yield t


async def labelled(n):
    async for e in evens(n):
        yield 'e%d' % e


async def main_nested():
    return [x async for x in labelled(7)]


print('nested', asyncio.run(main_nested()))

# async generator expressions
async def main_agenexp():
    agen = (t * 10 async for t in ticker(3))
    out = []
    async for v in agen:
        out.append(v)
    async def double(x):
        await asyncio.sleep(0)
        return 2 * x
    agen2 = (await double(i) for i in range(3))
    out.append([v async for v in agen2])
    return out


print('agenexp', asyncio.run(main_agenexp()))

# contextlib.asynccontextmanager
@contextlib.asynccontextmanager
async def resource(name, log):
    log.append('open ' + name)
    await asyncio.sleep(0)
    try:
        yield name.upper()
    finally:
        log.append('close ' + name)


async def main_acm():
    log = []
    async with resource('db', log) as r:
        log.append('using ' + r)
    try:
        async with resource('file', log):
            raise KeyError('k')
    except KeyError:
        log.append('KeyError propagated')
    return log


print('acm', asyncio.run(main_acm()))

# errors
async def bad_return():
    yield 1
    return


async def main_errors():
    out = []
    ag = ticker(1)
    try:
        await ag.asend('x')
    except TypeError as e:
        out.append('TypeError %s' % e)
    async def raises_stop():
        yield 1
        raise StopAsyncIteration
    try:
        async for _ in raises_stop():
            pass
    except RuntimeError as e:
        out.append('RuntimeError %s' % e)
    return out


print('errors', asyncio.run(main_errors()))

# async generator methods and closures
class Feed:
    def __init__(self, items):
        self.items = items

    async def stream(self, scale):
        for it in self.items:
            await asyncio.sleep(0)
            yield it * scale


async def main_method():
    return [v async for v in Feed([1, 2, 3]).stream(10)]


print('method', asyncio.run(main_method()))
