"""yield from: delegation of next/send/throw/close and the return value."""


def sub(n):
    received = []
    for i in range(n):
        x = yield 'sub%d' % i
        received.append(x)
    return received


def delegator():
    r = yield from sub(3)
    print('  sub returned', r)
    r2 = yield from sub(1)
    return ('done', r, r2)


g = delegator()
print(next(g))
print(g.send('a'))
print(g.send('b'))
print(g.send('c'))
try:
    g.send('d')
except StopIteration as e:
    print('final', e.value)

# yield from arbitrary iterables
def from_iterables():
    yield from [1, 2]
    yield from (3, 4)
    yield from range(5, 7)
    yield from 'ab'
    yield from {'k': 1}
    yield from iter([7])
    yield from (x * 10 for x in range(2))
    r = yield from []
    yield r


print(list(from_iterables()))

# the value of yield from used in expressions
def adder():
    a = yield 'a'
    b = yield 'b'
    return a + b


def uses_value():
    total = (yield from adder()) * 2 + (yield from adder())
    yield total


g = uses_value()
print(next(g), g.send(1), g.send(2), g.send(10), g.send(20))

# throw() is forwarded to the subgenerator; it can handle it
def sub_handles():
    while True:
        try:
            yield 'waiting'
        except ValueError as e:
            yield 'sub handled %s' % e


def outer_simple():
    yield from sub_handles()


g = outer_simple()
next(g)
print(g.throw(ValueError('v1')))
print(next(g))

# exception not handled by subgenerator propagates into the delegator
def sub_plain():
    yield 1
    yield 2


def outer_catch():
    try:
        yield from sub_plain()
    except KeyError as e:
        yield 'outer caught %s' % e
    yield 'outer continues'


g = outer_catch()
next(g)
print(g.throw(KeyError('k')))
print(next(g))

# subgenerator returning in response to throw resumes the delegator
def sub_return_on_throw():
    try:
        yield 'sub waiting'
    except IndexError:
        return 'sub-ret'


def outer_resume():
    v = yield from sub_return_on_throw()
    yield 'resumed with %s' % v


g = outer_resume()
next(g)
print(g.throw(IndexError))

# close() closes the subgenerator first, then raises GeneratorExit in the delegator
def sub_cleanup():
    try:
        yield 'sub'
    finally:
        print('  sub cleanup')


def outer_cleanup():
    try:
        yield from sub_cleanup()
    finally:
        print('  outer cleanup')


g = outer_cleanup()
next(g)
g.close()

def outer_sees_exit():
    try:
        yield from sub_cleanup()
    except GeneratorExit:
        print('  delegator saw GeneratorExit')
        raise


g = outer_sees_exit()
next(g)
g.close()

# send() to a delegator over a plain iterator (no send) -> AttributeError
def over_list():
    yield from [1, 2, 3]


g = over_list()
next(g)
print(g.send(None))
try:
    g.send('x')
except AttributeError as e:
    print('AttributeError', e)

# throw into a delegator over a list iterator raises in the delegator
def over_list_catch():
    try:
        yield from [1, 2, 3]
    except ValueError:
        yield 'delegator got it'


g = over_list_catch()
next(g)
print(g.throw(ValueError))

# yield from an iterator class with send/throw support (duck-typed)
class Coop:
    def __init__(self):
        self.log = []
        self.n = 0

    def __iter__(self):
        return self

    def __next__(self):
        return self.send(None)

    def send(self, v):
        self.log.append(v)
        self.n += 1
        if self.n > 3:
            raise StopIteration('coop-done')
        return 'coop%d' % self.n

    def throw(self, typ, val=None, tb=None):
        self.log.append('throw:' + typ.__name__ if isinstance(typ, type) else 'throw:' + type(typ).__name__)
        return 'coop-threw'


def over_coop(c):
    r = yield from c
    yield 'coop returned %s' % r


c = Coop()
g = over_coop(c)
print(next(g), g.send('s1'), g.throw(ValueError('x')), g.send('s2'), next(g))
print(c.log)

# a plain user iterator class (no send) delegates next() fine
class Countdown:
    def __init__(self, n):
        self.n = n

    def __iter__(self):
        return self

    def __next__(self):
        if self.n <= 0:
            raise StopIteration
        self.n -= 1
        return self.n


def over_countdown():
    yield from Countdown(3)
    yield 'end'


print(list(over_countdown()))

# deep delegation chain
def chain_level(depth):
    if depth == 0:
        x = yield 'bottom'
        return 'got %s' % x
    r = yield from chain_level(depth - 1)
    return r + '<%d' % depth


g = chain_level(25)
print(next(g))
try:
    g.send('X')
except StopIteration as e:
    print(e.value[:40], '...', e.value[-10:])

# yield from a generator that is already exhausted
def exhausted_sub():
    yield 1
    return 'ret'


s = exhausted_sub()
list(s)

def outer_exhausted():
    r = yield from s
    yield r


print(list(outer_exhausted()))

# yield from a non-iterable
def bad():
    yield from 42


try:
    list(bad())
except TypeError as e:
    print('TypeError', e)

# yield from inside an expression statement and as a call argument
def arg_use():
    print('  value:', (yield from adder()))
    yield 'end'


g = arg_use()
print(next(g), g.send(3), g.send(4))

# StopIteration value from return in subgenerator with a tuple / None
def ret_none():
    yield 1


def get_none():
    v = yield from ret_none()
    yield v


print(list(get_none()))
