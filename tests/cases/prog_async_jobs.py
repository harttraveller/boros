"""An asyncio job runner: worker tasks pulling from an asyncio.Queue,
a Semaphore limiting concurrency, async context managers, an async
iterator class, gather with return_exceptions, task cancellation, timeouts
via wait_for on a never-set Event, and exception propagation. Only
sleep(0) is used so the schedule is deterministic. (Async generators are
covered separately by prog_async_stream.py.)"""
import asyncio

LOG = []


class JobFailed(Exception):
    def __init__(self, job, reason):
        super().__init__("%s: %s" % (job, reason))
        self.job = job


class Resource:
    def __init__(self, name):
        self.name = name
        self.open = 0

    async def __aenter__(self):
        self.open += 1
        LOG.append("open " + self.name)
        await asyncio.sleep(0)
        return self

    async def __aexit__(self, et, ev, tb):
        self.open -= 1
        LOG.append("close %s%s" % (self.name, " after " + et.__name__ if et else ""))
        return False


class ticks:
    """Async iterator (class based) yielding 0..n-1 with a scheduling point."""

    def __init__(self, n):
        self.i = 0
        self.n = n

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self.i >= self.n:
            raise StopAsyncIteration
        await asyncio.sleep(0)
        self.i += 1
        return self.i - 1


async def job(name, steps, fail=False):
    total = 0
    async for i in ticks(steps):
        total += i
    if fail:
        raise JobFailed(name, "boom after %d steps" % steps)
    return name, total


async def worker(wid, queue, sem, results, res):
    while True:
        item = await queue.get()
        try:
            if item is None:
                return wid
            name, steps, fail = item
            async with sem:
                async with res:
                    try:
                        results.append(await job(name, steps, fail))
                    except JobFailed as e:
                        results.append(("failed", e.job))
        finally:
            queue.task_done()


async def main():
    queue = asyncio.Queue()
    sem = asyncio.Semaphore(2)
    res = Resource("db")
    results = []
    for spec in [("a", 3, False), ("b", 1, True), ("c", 4, False), ("d", 0, False)]:
        queue.put_nowait(spec)
    workers = [asyncio.create_task(worker(i, queue, sem, results, res)) for i in range(3)]
    await queue.join()
    for _ in workers:
        queue.put_nowait(None)
    done = await asyncio.gather(*workers)
    print("workers", sorted(done), "results", sorted(results, key=str), "open", res.open)

    outcomes = await asyncio.gather(job("x", 2), job("y", 1, fail=True), job("z", 0), return_exceptions=True)
    print([o if not isinstance(o, BaseException) else "%s(%s)" % (type(o).__name__, o) for o in outcomes])

    try:
        await asyncio.gather(job("p", 1), job("q", 2, fail=True))
    except JobFailed as e:
        print("gather raised:", e, isinstance(e, Exception))

    async def forever():
        try:
            while True:
                await asyncio.sleep(0)
        except asyncio.CancelledError:
            LOG.append("forever cancelled")
            raise

    t = asyncio.create_task(forever())
    for _ in range(3):
        await asyncio.sleep(0)
    t.cancel()
    try:
        await t
    except asyncio.CancelledError:
        print("task cancelled:", t.cancelled(), t.done())

    ev = asyncio.Event()
    try:
        await asyncio.wait_for(ev.wait(), timeout=0)
    except TimeoutError:
        print("timed out waiting for event")

    async with Resource("cache") as r:
        print("inside", r.name, r.open)
    try:
        async with Resource("file"):
            raise KeyError("missing")
    except KeyError as e:
        print("KeyError propagated", e)
    squares = []
    async for i in ticks(5):
        if i % 2 == 0:
            squares.append(i * i)
    print("async for", squares)
    return "main done"


print(asyncio.run(main()))
print(LOG)
