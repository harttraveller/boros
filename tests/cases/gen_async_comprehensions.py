"""Async comprehensions (`async for` inside list/set/dict comprehensions and
generator expressions) over class-based async iterators."""
import asyncio


async def double(x):
    await asyncio.sleep(0)
    return x * 2


class Ticker:
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


async def async_listcomp():
    return [t async for t in Ticker(5)]


print('async listcomp', asyncio.run(async_listcomp()))

async def async_comp_variants():
    evens = [t async for t in Ticker(6) if t % 2 == 0]
    squares = {t: t * t async for t in Ticker(3)}
    letters = {chr(97 + t) async for t in Ticker(3)}
    nested = [(t, u) async for t in Ticker(2) for u in range(2)]
    return evens, squares, sorted(letters), nested


print('async comp variants', asyncio.run(async_comp_variants()))

# a plain iterable in an async comprehension is a TypeError
plain = [1, 2]


async def wrong_iterable():
    try:
        return [x async for x in plain]
    except TypeError as e:
        return 'TypeError: %s' % e


print(asyncio.run(wrong_iterable()))
