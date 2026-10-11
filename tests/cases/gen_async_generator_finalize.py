"""An async generator abandoned (by break) without aclose() is finalized
by the event loop: its finally block runs from a task the loop schedules
(sys.set_asyncgen_hooks), not synchronously when the object dies."""
import asyncio


# an async generator abandoned by break is finalized by the event loop
async def abandoned():
    try:
        yield 1
        yield 2
    finally:
        print('  abandoned finally')


async def main_abandon():
    async for x in abandoned():
        print('  got', x)
        break
    print('  after break')
    await asyncio.sleep(0)
    print('  after sleep')


asyncio.run(main_abandon())
print('after run')
