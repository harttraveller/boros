"""async/await with asyncio: running, awaiting, gather, tasks, queues,
exceptions and return values of interpreted coroutines."""
import asyncio


async def add(a, b):
    await asyncio.sleep(0)
    return a + b


async def chain(n):
    total = 0
    for i in range(n):
        total = await add(total, i)
    return total


print(asyncio.run(add(1, 2)))
print(asyncio.run(chain(5)))

# coroutine objects
async def named():
    return 'named result'


c = named()
print(c.__name__, c.__qualname__)
print(asyncio.iscoroutine(c))
print(asyncio.run(c))

# interleaving with gather: order of execution and of results
log = []


async def worker(name, steps):
    for i in range(steps):
        log.append('%s%d' % (name, i))
        await asyncio.sleep(0)
    return name * steps


async def main_gather():
    results = await asyncio.gather(worker('a', 3), worker('b', 2), worker('c', 1))
    return results


print(asyncio.run(main_gather()))
print(log)

# exceptions propagate through await
async def fails(msg):
    await asyncio.sleep(0)
    raise ValueError(msg)


async def catcher():
    try:
        await fails('inner failure')
    except ValueError as e:
        return 'caught: %s' % e


print(asyncio.run(catcher()))

# gather with return_exceptions
async def main_gather_exc():
    res = await asyncio.gather(add(1, 1), fails('bad'), add(2, 2), return_exceptions=True)
    return [type(r).__name__ if isinstance(r, Exception) else r for r in res]


print(asyncio.run(main_gather_exc()))

# gather without return_exceptions raises the first error
async def main_gather_raise():
    try:
        await asyncio.gather(add(1, 1), fails('first'))
    except ValueError as e:
        return 'gather raised %s' % e


print(asyncio.run(main_gather_raise()))

# tasks
async def main_tasks():
    t1 = asyncio.create_task(worker('x', 2))
    t2 = asyncio.create_task(worker('y', 2))
    r1 = await t1
    r2 = await t2
    return r1, r2, t1.done(), t2.result()


log.clear()
print(asyncio.run(main_tasks()), log)

# awaiting one interpreted coroutine from another, deeply
async def depth(n):
    if n == 0:
        await asyncio.sleep(0)
        return 0
    return 1 + await depth(n - 1)


print(asyncio.run(depth(30)))

# producer / consumer with asyncio.Queue
async def producer(q, n):
    for i in range(n):
        await q.put(i)
    await q.put(None)


async def consumer(q):
    got = []
    while True:
        item = await q.get()
        if item is None:
            return got
        got.append(item * item)


async def main_queue():
    q = asyncio.Queue(maxsize=2)
    _, got = await asyncio.gather(producer(q, 5), consumer(q))
    return got


print(asyncio.run(main_queue()))

# Event and Lock (async with on host objects)
async def main_sync():
    ev = asyncio.Event()
    lock = asyncio.Lock()
    order = []

    async def waiter():
        await ev.wait()
        async with lock:
            order.append('waiter')

    async def setter():
        async with lock:
            order.append('setter')
            ev.set()
            await asyncio.sleep(0)
            order.append('setter done')

    await asyncio.gather(waiter(), setter())
    return order


print(asyncio.run(main_sync()))

# methods that are coroutines, and awaiting results in expressions
class Account:
    def __init__(self):
        self.balance = 0

    async def deposit(self, n):
        await asyncio.sleep(0)
        self.balance += n
        return self.balance

    @staticmethod
    async def double(x):
        return x * 2

    @classmethod
    async def make(cls):
        acct = cls()
        await acct.deposit(5)
        return acct


async def main_methods():
    acct = await Account.make()
    v = await acct.deposit(10) + await Account.double(3)
    doubles = []
    for i in range(3):
        doubles.append(await Account.double(i))
    return acct.balance, v, doubles


print(asyncio.run(main_methods()))

# asyncio.wait_for on a coroutine that finishes quickly; shield; timeouts not hit
async def main_wait_for():
    r = await asyncio.wait_for(add(20, 22), timeout=10)
    s = await asyncio.shield(add(1, 1))
    return r, s


print(asyncio.run(main_wait_for()))

# cancellation of a task running an interpreted coroutine
async def sleeper(log):
    try:
        await asyncio.sleep(10)
    except asyncio.CancelledError:
        log.append('cancelled inside')
        raise
    finally:
        log.append('sleeper finally')


async def main_cancel():
    log = []
    t = asyncio.create_task(sleeper(log))
    await asyncio.sleep(0)
    t.cancel()
    try:
        await t
    except asyncio.CancelledError:
        log.append('caller saw CancelledError')
    return log, t.cancelled()


print(asyncio.run(main_cancel()))

# async lambda-like: a coroutine function returned from a factory
def make_coro_fn(k):
    async def f(x):
        await asyncio.sleep(0)
        return x * k
    return f


print(asyncio.run(make_coro_fn(3)(7)))

# an uncaught exception in asyncio.run propagates to the caller
try:
    asyncio.run(fails('top level'))
except ValueError as e:
    print('asyncio.run raised', e)
