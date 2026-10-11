"""Generator-based data pipeline: producers, filters, windowing, coroutines
that receive values with send(), yield from delegation with return values,
generator cleanup with close()/finally, throw(), and itertools composition."""
import itertools
from collections import deque

LOG = []


def source(lines):
    try:
        for i, line in enumerate(lines):
            yield i, line
    finally:
        LOG.append("source closed")


def strip_comments(items):
    for i, line in items:
        line = line.split("#", 1)[0].strip()
        if line:
            yield i, line


def parse_numbers(items):
    for i, line in items:
        for tok in line.replace(",", " ").split():
            try:
                yield float(tok) if "." in tok else int(tok)
            except ValueError:
                LOG.append("line %d: skip %r" % (i, tok))


def window(it, n):
    buf = deque(maxlen=n)
    for x in it:
        buf.append(x)
        if len(buf) == n:
            yield tuple(buf)


def averager():
    total = 0
    count = 0
    avg = None
    while True:
        try:
            x = yield avg
        except ValueError as e:
            LOG.append("averager reset: %s" % e)
            total = count = 0
            avg = None
            continue
        if x is None:
            break
        total += x
        count += 1
        avg = total / count
    return count, total


def delegator(results):
    while True:
        r = yield from averager()
        results.append(r)
        if len(results) >= 2:
            return "done"


def take_until_negative(it):
    for x in it:
        if x < 0:
            return x
        yield x


def chunked(it, size):
    it = iter(it)
    while chunk := list(itertools.islice(it, size)):
        yield chunk


TEXT = """
# sensor dump
1, 2, 3
4 five 6   # inline comment
7.5 8
    # blank
9, 10, -1, 11
"""

nums = list(parse_numbers(strip_comments(source(TEXT.splitlines()))))
print(nums, LOG)
print(list(window(nums, 3))[:4])
print([round(sum(w) / len(w), 2) for w in window(nums, 4)])

LOG.clear()
src = source(["1", "2", "3", "4"])
first = next(src)
src.close()
print(first, LOG, next(src, "exhausted"))

avg = averager()
next(avg)
print([avg.send(x) for x in (10, 20, 30)])
avg.throw(ValueError("bad sample"))
print(avg.send(4), avg.send(8))
try:
    avg.send(None)
except StopIteration as e:
    print("averager returned", e.value)

results = []
d = delegator(results)
next(d)
for x in (1, 2, 3, None, 100, None):
    try:
        d.send(x)
    except StopIteration as e:
        print("delegator finished:", e.value)
print(results, LOG)

gen = take_until_negative(iter(nums))
print(list(gen))


def collect_return(g):
    r = yield from g
    yield "returned %r" % (r,)


print(list(collect_return(take_until_negative([1, 2, -5, 3]))))
print(list(chunked(range(10), 4)), list(chunked([], 3)))

squares = (x * x for x in itertools.count(1))
odd_sq = filter(lambda v: v % 2, squares)
print(list(itertools.islice(odd_sq, 5)), next(squares))
pairs = itertools.pairwise(itertools.accumulate([3, 1, 4, 1, 5, 9, 2, 6]))
print([b - a for a, b in pairs])
grouped = {k: list(g) for k, g in itertools.groupby(sorted("mississippi"))}
print(grouped, list(itertools.chain.from_iterable(itertools.repeat("ab", 2))))
print(list(itertools.starmap(pow, zip(range(5), itertools.cycle([2, 3])))),
      list(itertools.takewhile(lambda c: c != "s", "mississippi")),
      list(itertools.compress("abcdef", [1, 0, 1, 0, 1, 1])))
print(list(itertools.zip_longest("abc", [1, 2], fillvalue="-")), list(itertools.product("ab", repeat=2)),
      list(itertools.combinations(range(4), 2))[:4], len(list(itertools.permutations(range(4)))))


class Countdown:
    def __init__(self, n):
        self.n = n

    def __iter__(self):
        n = self.n
        while n > 0:
            yield n
            n -= 1

    def __reversed__(self):
        return iter(range(1, self.n + 1))


cd = Countdown(4)
print(list(cd), list(reversed(cd)), sum(cd), max(cd), sorted(cd), list(zip(cd, cd)), 3 in cd)
t1, t2 = itertools.tee(iter(cd))
print(list(t1), list(t2), list(enumerate(cd, start=10)))


def fibgen():
    a, b = 0, 1
    while True:
        yield a
        a, b = b, a + b


g = fibgen()
print([next(g) for _ in range(10)], g.gi_running, type(g).__name__)
g.close()
print(list(g), next(g, None))


def broken():
    yield 1
    raise RuntimeError("pipeline stage failed")


try:
    for v in broken():
        print("got", v)
except RuntimeError as e:
    print("caught:", e)


def no_stop():
    yield 1
    raise StopIteration


try:
    list(no_stop())
except RuntimeError as e:
    print("RuntimeError:", e, type(e.__cause__).__name__)
