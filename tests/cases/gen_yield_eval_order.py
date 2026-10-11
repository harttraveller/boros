"""Evaluation order around yield expressions must match CPython:
operands to the left of a yield are evaluated before the generator
suspends."""


# 1. augmented assignment: the target's current value is loaded *before*
#    the right-hand side (which suspends) is evaluated.
class Acc:
    def __init__(self):
        self.total = 10

    def run(self):
        while True:
            self.total += yield self.total


acc = Acc()
r = acc.run()
print('attr first', next(r))
acc.total = 1000          # changed while suspended: CPython ignores this
print('attr after send', r.send(1), acc.total)

box = [0]

def item_acc():
    while True:
        box[0] += yield


ia = item_acc()
next(ia)
box[0] = 100
ia.send(5)
print('item', box)

counter = 0

def global_acc():
    global counter
    counter += yield 'g'


g = global_acc()
next(g)
counter = 50
try:
    g.send(1)
except StopIteration:
    pass
print('global', counter)

# the subscript expressions of the target are evaluated before the value
log = []

def key(k):
    log.append('key %s' % k)
    return k


def item_order(d):
    d[key('a')] += yield 'v'


d = {'a': 1}
g = item_order(d)
print(next(g), log)
log.append('sent')
try:
    g.send(2)
except StopIteration:
    pass
print(d, log)

# 2. dict displays evaluate key, value, key, value ... left to right
def dict_order():
    dct = {(yield 'k1'): (yield 'v1'), (yield 'k2'): (yield 'v2')}
    yield sorted(dct.items())


g = dict_order()
steps = [next(g)]
for v in ['K1', 'V1', 'K2', 'V2']:
    steps.append(g.send(v))
print(steps)

def dict_mixed():
    dct = {'k': (yield 'dv'), (yield 'dk'): 'v'}
    yield sorted(dct.items())


g = dict_mixed()
print(next(g), g.send('first-sent'), g.send('second-sent'))

def note(x):
    print('  eval', x)
    return x


def dict_side_effects():
    return {note('a'): (yield 1), note('b'): note('c'), **(yield 2), note('d'): (yield 3)}


g = dict_side_effects()
print(next(g))
print(g.send('A'))
print(g.send({'m': 'M'}))
try:
    g.send('D')
except StopIteration as e:
    print(sorted(e.value.items()))

# 3. the same rule for await: `self.total += await ...` reads self.total
#    before suspending, so concurrent tasks lose updates in CPython
import asyncio


class Counter:
    def __init__(self):
        self.total = 0

    async def get(self, v):
        await asyncio.sleep(0)
        return v

    async def add(self, v):
        self.total += await self.get(v)


async def race():
    c = Counter()
    await asyncio.gather(c.add(1), c.add(2), c.add(3))
    return c.total


print('async lost update total:', asyncio.run(race()))
