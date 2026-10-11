"""await inside ordinary (synchronous) comprehensions of an async function."""
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


async def await_in_listcomp():
    return [await double(i) for i in range(4)]


print('await in listcomp', asyncio.run(await_in_listcomp()))

async def await_in_other_comps():
    s = {await double(i) for i in range(3)}
    d = {i: await double(i) for i in range(3)}
    cond = [i for i in range(6) if await double(i) > 4]
    return sorted(s), d, cond


print('await in set/dict/filter', asyncio.run(await_in_other_comps()))

# await in the iterable of the first loop and in a nested loop
async def await_in_iterables():
    async def items():
        await asyncio.sleep(0)
        return [1, 2]
    return [x + y for x in await items() for y in await items()]


print('await in iterables', asyncio.run(await_in_iterables()))
