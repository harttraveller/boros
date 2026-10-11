"""Basic generator behaviour: creation, iteration, exhaustion, return values."""
import types


def count_up(n):
    i = 0
    while i < n:
        yield i
        i += 1


def with_return(n):
    for i in range(n):
        yield i
    return 'done-%d' % n


def no_yield_reached(flag):
    if flag:
        yield 'reached'
    return 'early'


# lazy: body does not run until next()
def noisy():
    print('  body started')
    yield 1
    print('  after first yield')
    yield 2
    print('  body finished')


print('count_up:', list(count_up(5)))
print('sum:', sum(count_up(10)))
g = noisy()
print('created')
print('first', next(g))
print('second', next(g))
try:
    next(g)
except StopIteration as e:
    print('StopIteration value', e.value, e.args)

# return value through StopIteration.value
g = with_return(2)
print(next(g), next(g))
try:
    next(g)
except StopIteration as e:
    print('returned', repr(e.value), e.args)
# further next() calls just raise StopIteration with no value
try:
    next(g)
except StopIteration as e:
    print('again', repr(e.value), e.args)

g = no_yield_reached(False)
try:
    next(g)
except StopIteration as e:
    print('early', e.value)

# return of a tuple / None
def ret_tuple():
    yield
    return (1, 2)


g = ret_tuple()
next(g)
try:
    next(g)
except StopIteration as e:
    print('tuple value', e.value, e.args)

def ret_none():
    yield 1
    return


g = ret_none()
next(g)
try:
    next(g)
except StopIteration as e:
    print('none value', e.value, e.args)

# generator objects
g = count_up(3)
print(type(g).__name__, isinstance(g, types.GeneratorType))
print(iter(g) is g, g.__name__, g.__qualname__)
print(hasattr(g, '__next__'), hasattr(g, 'send'), hasattr(g, 'throw'), hasattr(g, 'close'))
print(list(g), list(g))   # exhausted after first list()

# next() with default
g = count_up(1)
print(next(g, 'dflt'), next(g, 'dflt'), next(g, 'dflt'))

# generator methods and qualnames
class Box:
    def __init__(self, items):
        self.items = items

    def __iter__(self):
        for it in self.items:
            yield it * 10

    def evens(self):
        for it in self.items:
            if it % 2 == 0:
                yield it

    @staticmethod
    def sgen(n):
        yield from range(n)

    @classmethod
    def cgen(cls, n):
        for i in range(n):
            yield cls.__name__ + str(i)


b = Box([1, 2, 3, 4])
print(list(b), list(b.evens()), list(Box.sgen(3)), list(Box.cgen(2)))
print(b.evens().__qualname__, Box.sgen(1).__name__)

def outer():
    def inner():
        yield 1
    return inner()


print(outer().__qualname__)

# generator lambda
gl = (lambda: (yield 5))()
print(next(gl))
try:
    gl.send('sent')
except StopIteration as e:
    print('lambda returned', e.value)

# arguments, defaults, *args, **kwargs in generator functions
def args_gen(a, b=2, *rest, key='k', **kw):
    yield a
    yield b
    yield rest
    yield key
    yield sorted(kw.items())


print(list(args_gen(1)))
print(list(args_gen(1, 3, 4, 5, key='z', x=1, y=2)))
try:
    args_gen()
except TypeError as e:
    print('TypeError', e)

# each call makes an independent generator
g1, g2 = count_up(3), count_up(3)
print(next(g1), next(g1), next(g2), next(g1), next(g2))

# local state survives suspension
def running_total(xs):
    total = 0
    for x in xs:
        total += x
        yield total


print(list(running_total([1, 2, 3, 4])))

# generator in unpacking, in, enumerate, zip, sorted
a, b, c = count_up(3)
print(a, b, c)
print(2 in count_up(5), 7 in count_up(5))
print(list(enumerate(count_up(3), 1)), list(zip(count_up(3), 'abc')))
print(sorted(count_up(4), reverse=True), max(count_up(4)), min(count_up(4)))
print(dict((i, i * i) for i in count_up(3)), '-'.join(str(i) for i in count_up(4)))
first, *rest = count_up(4)
print(first, rest)
try:
    x, y = count_up(3)
except ValueError as e:
    print('ValueError', e)
try:
    x, y, z = count_up(2)
except ValueError as e:
    print('ValueError', e)

# subscripting / len on a generator are errors
try:
    count_up(3)[0]
except TypeError as e:
    print('TypeError', e)
try:
    len(count_up(3))
except TypeError as e:
    print('TypeError', e)

# a generator function that is empty but still a generator
def empty():
    return
    yield


print(list(empty()), type(empty()).__name__)

def only_yield_in_dead_branch():
    if False:
        yield
    print('ran body')


print(list(only_yield_in_dead_branch()))

# generator state introspection
import inspect


def two():
    yield 1
    yield 2


g = two()
print(inspect.getgeneratorstate(g), g.gi_running, g.gi_suspended)
next(g)
print(inspect.getgeneratorstate(g), g.gi_running, g.gi_suspended)
list(g)
print(inspect.getgeneratorstate(g), g.gi_frame is None, inspect.isgenerator(g))
g = two()
g.close()
print(inspect.getgeneratorstate(g))
