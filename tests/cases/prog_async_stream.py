"""Async streaming pipeline built from async generators: an async source,
async filter/map stages, async comprehensions, aclose()/athrow() and
cleanup in finally, and asyncio.as_completed-free deterministic ordering."""
import asyncio

LOG = []


async def readings(n):
    try:
        for i in range(n):
            await asyncio.sleep(0)
            yield i * 1.5
    finally:
        LOG.append("source closed")


async def only_even_index(stream):
    idx = 0
    async for x in stream:
        if idx % 2 == 0:
            yield x
        idx += 1


async def scaled(stream, k):
    async for x in stream:
        yield round(x * k, 2)


async def counter():
    n = 0
    while True:
        try:
            cmd = yield n
        except ValueError:
            LOG.append("reset")
            n = 0
            continue
        n += cmd or 1


async def main():
    out = [x async for x in scaled(only_even_index(readings(7)), 2)]
    print("pipeline", out)
    agen = readings(10)
    first = await agen.__anext__()
    await agen.aclose()
    print("first", first, LOG)
    c = counter()
    print(await c.asend(None), await c.asend(5), await c.asend(None))
    print(await c.athrow(ValueError()), await c.asend(2))
    await c.aclose()
    total = sum([v async for v in readings(4) if v > 1])
    print("total", total, type(readings(1)).__name__)


asyncio.run(main())
print(LOG)
