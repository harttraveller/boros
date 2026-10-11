"""yield inside if/elif/else, while/for (with break/continue/else),
try/except/else/finally, with, match, nested functions."""


def branches(n):
    if n < 0:
        yield 'negative'
    elif n == 0:
        yield 'zero'
        yield 'still zero'
    else:
        yield 'positive'
    yield 'after if'


print([list(branches(n)) for n in (-1, 0, 1)])

def loops():
    i = 0
    while True:
        i += 1
        if i == 2:
            continue
        if i > 4:
            break
        yield 'while %d' % i
    else:
        yield 'not reached'
    for j in range(3):
        yield 'for %d' % j
    else:
        yield 'for-else'
    for k in range(5):
        if k == 1:
            continue
        if k == 3:
            break
        yield 'k %d' % k
    else:
        yield 'not reached either'
    n = 0
    while n < 2:
        yield 'n %d' % n
        n += 1
    else:
        yield 'while-else'


print(list(loops()))

def nested_loops():
    for i in range(3):
        for j in range(3):
            if j > i:
                break
            yield (i, j)


print(list(nested_loops()))

def try_flow(mode):
    try:
        yield 'try start'
        if mode == 'raise':
            raise ValueError('boom')
        if mode == 'return':
            return 'early return'
        yield 'try end'
    except ValueError as e:
        yield 'except %s' % e
    else:
        yield 'else'
    finally:
        yield 'finally'
    yield 'after'


for mode in ('ok', 'raise', 'return'):
    g = try_flow(mode)
    out = list(g)
    print(mode, out)

def handler_variable_cleared():
    try:
        raise KeyError('kk')
    except KeyError as err:
        yield repr(err)
    try:
        err
    except NameError as e:
        yield 'NameError: ' + str(e)


print(list(handler_variable_cleared()))

# return inside finally overrides an exception
def finally_return():
    try:
        yield 1
        raise ValueError('lost')
    finally:
        return 'finally wins'


g = finally_return()
next(g)
try:
    next(g)
except StopIteration as e:
    print('StopIteration', e.value)

# break / continue inside try/finally within loops in a generator
def loop_finally():
    for i in range(4):
        try:
            if i == 1:
                continue
            if i == 3:
                break
            yield i
        finally:
            yield 'cleanup %d' % i


print(list(loop_finally()))

# exception raised while suspended in nested try blocks
def nested_try():
    try:
        try:
            yield 'inner'
        except KeyError:
            yield 'inner caught KeyError'
            raise IndexError('from inner handler')
    except IndexError as e:
        yield 'outer caught %s, context=%r' % (e, e.__context__)


g = nested_try()
print(next(g))
print(g.throw(KeyError('k')))
print(next(g))

# with statement inside a generator
class CM:
    def __init__(self, name, suppress=False):
        self.name = name
        self.suppress = suppress

    def __enter__(self):
        print('  enter', self.name)
        return self.name.upper()

    def __exit__(self, typ, val, tb):
        print('  exit', self.name, typ.__name__ if typ else None, val)
        return self.suppress


def with_gen():
    with CM('a') as a, CM('b') as b:
        yield a + b
    with CM('s', suppress=True):
        yield 'in s'
        raise ValueError('suppressed')
    yield 'after s'
    with CM('p'):
        yield 'in p'


g = with_gen()
print(next(g))
print(next(g))
print(next(g))
print(next(g))
try:
    g.throw(TypeError('into p'))
except TypeError as e:
    print('propagated', e)

# closing a generator suspended in a with block runs __exit__ with GeneratorExit
def with_close():
    with CM('c'):
        yield 1


g = with_close()
next(g)
g.close()

# match statement with yields
def matcher(values):
    for v in values:
        match v:
            case int(n) if n > 0:
                yield 'positive int %d' % n
            case [a, b]:
                yield 'pair %r %r' % (a, b)
                yield 'pair sum %r' % (a + b)
            case {'k': val}:
                yield 'mapping %r' % (val,)
            case _:
                yield 'other %r' % (v,)


print(list(matcher([3, -1, [1, 2], {'k': 'v'}, 'str'])))

# match on a yielded value
def match_sent():
    while True:
        match (yield 'ready'):
            case 'stop':
                return 'stopped'
            case cmd:
                print('  command', cmd)


g = match_sent()
next(g)
g.send('go')
g.send('jump')
try:
    g.send('stop')
except StopIteration as e:
    print(e.value)

# yield in nested function definitions does not make the outer a generator
def outer_not_gen():
    def inner():
        yield 1
    return list(inner())


print(outer_not_gen())

# generator defined inside a loop capturing the loop variable
def make():
    gens = []
    for i in range(3):
        def g(i=i):
            yield i
            yield i * 10
        gens.append(g())
    return [list(x) for x in gens]


print(make())

# del, global and nonlocal inside generators
counter = 0

def uses_global():
    global counter
    for _ in range(3):
        counter += 1
        yield counter


print(list(uses_global()), counter)

def uses_nonlocal():
    state = 0

    def bump():
        nonlocal state
        while True:
            state += 1
            yield state
    b = bump()
    next(b)
    next(b)
    return state


print(uses_nonlocal())

def deleting():
    x = 1
    yield x
    del x
    try:
        yield x
    except UnboundLocalError as e:
        yield 'UnboundLocalError: ' + str(e)


print(list(deleting()))

# assert / raise inside generator
def asserting(v):
    assert v, 'v must be truthy'
    yield v


print(list(asserting(1)))
try:
    list(asserting(0))
except AssertionError as e:
    print('AssertionError', e)

# yield inside a lambda default and decorator expression
def deco_gen():
    def deco(f):
        f.tag = 'decorated'
        return f

    @(yield deco)
    def h():
        pass
    yield h.tag


g = deco_gen()
d = next(g)
print(g.send(d))

# return in a loop inside try/finally inside a generator
def ret_in_loop():
    try:
        for i in range(5):
            yield i
            if i == 1:
                return 'returned at 1'
    finally:
        print('  ret_in_loop finally')


g = ret_in_loop()
print(next(g), next(g))
try:
    next(g)
except StopIteration as e:
    print(e.value)
