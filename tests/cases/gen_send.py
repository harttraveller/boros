"""send() semantics and yield used as an expression in many positions."""


def echo():
    received = []
    while True:
        x = yield len(received)
        if x is None:
            break
        received.append(x)
    return received


g = echo()
print(g.send(None))
print(g.send('a'), g.send('b'))
try:
    g.send(None)
except StopIteration as e:
    print('returned', e.value)

# send non-None to just-started generator
g = echo()
try:
    g.send(1)
except TypeError as e:
    print('TypeError', e)
# the generator is still usable afterwards
print(next(g), g.send('z'))

# send to an exhausted generator
g = echo()
next(g)
try:
    g.send(None)
except StopIteration:
    print('exhausted')
try:
    g.send('late')
except StopIteration as e:
    print('still exhausted', e.args)

# running averager coroutine
def averager():
    total = 0.0
    count = 0
    avg = None
    while True:
        term = yield avg
        total += term
        count += 1
        avg = total / count


a = averager()
next(a)
print([a.send(v) for v in (10, 20, 30, 5)])

def log(*args, **kw):
    print('  log', *args, sorted(kw.items()))
    return args, sorted(kw.items())


# yield in call arguments: evaluated left to right
def call_args():
    log((yield 'first'), (yield 'second'))
    log(1, (yield 'third'), k=(yield 'fourth'))
    r = log(*(yield 'star'), **(yield 'dstar'))
    yield r


g = call_args()
print(next(g))
print(g.send('A'))
print(g.send('B'))
print(g.send('C'))
print(g.send('D'))
print(g.send((7, 8)))
print(g.send({'x': 9}))

# print((yield)) and chained yields
def printer():
    while True:
        print('  got', (yield))


p = printer()
next(p)
p.send('hello')
p.send(42)
p.close()

def chained():
    x = yield (yield 1)
    yield 'x=%r' % (x,)


g = chained()
print(next(g), g.send('inner'), g.send('outer'))

# yield in conditional expressions and boolean operators
def cond(flag):
    v = (yield 'then') if flag else (yield 'else')
    w = (yield 'and-left') and (yield 'and-right')
    z = (yield 'or-left') or (yield 'or-right')
    yield (v, w, z)


for flag in (True, False):
    g = cond(flag)
    out = [next(g)]
    out.append(g.send('V'))          # value for v
    out.append(g.send(0))            # and-left falsy: skip and-right
    out.append(g.send(''))           # or-left falsy: evaluate or-right
    out.append(g.send('R'))
    print(out)

# yield inside displays, subscripts, comparisons, f-strings, arithmetic
def displays():
    lst = [1, (yield 'l'), 3]
    tup = ((yield 't'), 'x')
    dct = {'k': (yield 'dv'), 'k2': (yield 'dv2')}
    st = {(yield 's')}
    yield (lst, tup, sorted(dct.items()), st)
    data = {'a': 1, 'b': 2}
    yield data[(yield 'key')]
    yield 1 < (yield 'cmp') < 10
    yield f'<{(yield "fs")}>'
    yield 10 - (yield 'sub') * 2
    yield -(yield 'neg')
    yield [(yield 'c1'), (yield 'c2')][::-1]


g = displays()
res = [next(g)]
for v in ['L', 'T', 'DV', 'DV2', 'S']:
    res.append(g.send(v))
print(res)
print(next(g), g.send('b'))
print(next(g), g.send(5))
print(next(g), g.send('mid'))
print(next(g), g.send(3))
print(next(g), g.send(4))
print(next(g), g.send('one'), g.send('two'))

# walrus with yield, yield in while/if/for headers
def headers():
    total = 0
    while (n := (yield total)) is not None:
        if (yield 'check %d' % n):
            total += n
    for item in (yield 'iterable?'):
        total += item
    return total


g = headers()
print(next(g), g.send(5), g.send(True), g.send(7), g.send(False))
print(g.send(None))
try:
    g.send([100, 200])
except StopIteration as e:
    print('total', e.value)

# return (yield) and yield as a statement inside expression statements
def ret_yield():
    return (yield 'q')


g = ret_yield()
print(next(g))
try:
    g.send('answer')
except StopIteration as e:
    print('returned', e.value)

# a bare yield yields None, the send value of next() is None
def bare():
    a = yield
    b = yield
    yield (a, b)


g = bare()
print(next(g), next(g), next(g))

# send() with a method on an attribute target: obj.attr = yield / obj[k] = yield
class Holder:
    pass


def store_targets(h, d):
    h.attr = yield 'attr'
    d['key'] = yield 'item'
    h.a, h.b = yield 'unpack'
    yield 'done'


h = Holder()
d = {}
g = store_targets(h, d)
print(next(g), g.send(1), g.send(2), g.send((3, 4)))
print(h.attr, d, h.a, h.b)
