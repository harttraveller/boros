"""Cooperative multitasking with generators: a round-robin scheduler with a
virtual clock, sleeping tasks kept in a heap, channels with blocking
receive, task cancellation via throw(), join, and exception propagation
out of tasks. Tasks communicate by yielding request objects."""
import heapq
import itertools
from collections import deque


class Sleep:
    def __init__(self, ticks):
        self.ticks = ticks


class Recv:
    def __init__(self, chan):
        self.chan = chan


class Send:
    def __init__(self, chan, value):
        self.chan = chan
        self.value = value


class Join:
    def __init__(self, task):
        self.task = task


class Cancelled(Exception):
    pass


class Channel:
    def __init__(self, name):
        self.name = name
        self.items = deque()
        self.waiting = deque()

    def __repr__(self):
        return "Channel(%s, %d queued)" % (self.name, len(self.items))


class Task:
    ids = itertools.count(1)

    def __init__(self, name, gen):
        self.id = next(Task.ids)
        self.name = name
        self.gen = gen
        self.send_value = None
        self.throw_value = None
        self.done = False
        self.result = None
        self.error = None
        self.joiners = []

    def __repr__(self):
        state = "done" if self.done else "live"
        return "<Task %d %s %s>" % (self.id, self.name, state)


class Scheduler:
    def __init__(self):
        self.ready = deque()
        self.sleeping = []
        self.clock = 0
        self.trace = []
        self.seq = itertools.count()

    def spawn(self, name, gen):
        t = Task(name, gen)
        self.ready.append(t)
        return t

    def cancel(self, task):
        task.throw_value = Cancelled("cancelled at t=%d" % self.clock)
        if task not in self.ready:
            self.sleeping = [s for s in self.sleeping if s[2] is not task]
            heapq.heapify(self.sleeping)
            self.ready.append(task)

    def _finish(self, task, result=None, error=None):
        task.done = True
        task.result = result
        task.error = error
        self.trace.append((self.clock, task.name, "error: %s" % error if error else "result: %r" % (result,)))
        for j in task.joiners:
            j.send_value = (result, error)
            self.ready.append(j)

    def step(self, task):
        try:
            if task.throw_value is not None:
                exc, task.throw_value = task.throw_value, None
                req = task.gen.throw(exc)
            else:
                req = task.gen.send(task.send_value)
            task.send_value = None
        except StopIteration as e:
            self._finish(task, result=e.value)
            return
        except Exception as e:
            self._finish(task, error="%s(%s)" % (type(e).__name__, e))
            return
        if isinstance(req, Sleep):
            heapq.heappush(self.sleeping, (self.clock + req.ticks, next(self.seq), task))
        elif isinstance(req, Send):
            ch = req.chan
            if ch.waiting:
                receiver = ch.waiting.popleft()
                receiver.send_value = req.value
                self.ready.append(receiver)
            else:
                ch.items.append(req.value)
            self.ready.append(task)
        elif isinstance(req, Recv):
            ch = req.chan
            if ch.items:
                task.send_value = ch.items.popleft()
                self.ready.append(task)
            else:
                ch.waiting.append(task)
        elif isinstance(req, Join):
            if req.task.done:
                task.send_value = (req.task.result, req.task.error)
                self.ready.append(task)
            else:
                req.task.joiners.append(task)
        elif req is None:
            self.ready.append(task)
        else:
            self._finish(task, error="bad request %r" % (req,))

    def run(self, limit=1000):
        steps = 0
        while (self.ready or self.sleeping) and steps < limit:
            if not self.ready:
                t, _, task = heapq.heappop(self.sleeping)
                self.clock = t
                self.ready.append(task)
                continue
            self.step(self.ready.popleft())
            steps += 1
        return steps


def producer(chan, n, delay):
    for i in range(n):
        yield Sleep(delay)
        yield Send(chan, "item%d" % i)
    yield Send(chan, None)
    return "produced %d" % n


def consumer(chan, log):
    got = []
    while True:
        item = yield Recv(chan)
        if item is None:
            break
        got.append(item)
        log.append(item)
    return got


def ticker(name, period, log):
    n = 0
    try:
        while True:
            yield Sleep(period)
            n += 1
            log.append("%s@%d" % (name, n))
    except Cancelled as e:
        log.append("%s stopped: %s" % (name, e))
        return n
    finally:
        log.append("%s cleanup" % name)


def failing():
    yield Sleep(2)
    raise ValueError("disk full")


def supervisor(sched, tasks, log):
    for t in tasks:
        result, error = yield Join(t)
        log.append("joined %s -> %r %r" % (t.name, result, error))
    yield Sleep(1)
    sched.cancel(tick)
    result, error = yield Join(tick)
    return "ticker ran %r times" % (result,)


log = []
sched = Scheduler()
ch = Channel("jobs")
p = sched.spawn("producer", producer(ch, 4, 3))
c = sched.spawn("consumer", consumer(ch, log))
tick = sched.spawn("ticker", ticker("tick", 5, log))
f = sched.spawn("failing", failing())
bad = sched.spawn("bad", iter([42]))
sup = sched.spawn("supervisor", supervisor(sched, [p, c, f], log))
steps = sched.run()
print("steps", steps, "clock", sched.clock, ch)
for entry in sched.trace:
    print(entry)
print(log)
print(sup.result, c.result, p, f.error, tick.result)
