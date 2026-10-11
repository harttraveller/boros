"""Coroutine objects of interpreted async functions: reuse after
completion, send()/throw()/close() by hand, iteration errors, type name
and StopIteration raised inside a coroutine.  Each check reports its own
outcome so one discrepancy does not hide the others."""
import asyncio
import inspect


async def value():
    return 1


async def two_steps():
    await asyncio.sleep(0)
    return 'finished'


async def catcher():
    try:
        await asyncio.sleep(0)
    except KeyError as e:
        return 'caught %s' % e


async def raises_stop():
    raise StopIteration('inside coroutine')


def report(label, fn):
    try:
        print(label, 'ok', fn())
    except BaseException as e:
        print(label, type(e).__name__, e)


async def await_twice():
    c = value()
    await c
    return await c


report('await twice:', lambda: asyncio.run(await_twice()))

c = two_steps()
report('send 1:', lambda: c.send(None))
report('send 2:', lambda: c.send(None))
report('send after finish:', lambda: c.send(None))

c2 = two_steps()
c2.close()
report('send after close:', lambda: c2.send(None))

c3 = two_steps()
report('send non-None first:', lambda: c3.send('x'))
c3.close()

c4 = catcher()
c4.send(None)
try:
    c4.throw(KeyError('k'))
except StopIteration as e:
    print('throw handled -> StopIteration', e.value)

c5 = value()
report('iter(coro):', lambda: iter(c5))
report('next(coro):', lambda: next(c5))
c5.close()

report('StopIteration in coroutine:', lambda: asyncio.run(raises_stop()))

c6 = value()
print('type name:', type(c6).__name__)
print('isawaitable / asyncio.iscoroutine:', inspect.isawaitable(c6), asyncio.iscoroutine(c6))
print('inspect.iscoroutine:', inspect.iscoroutine(c6))
c6.close()
