import functools


def add(a, b):
    return a + b


print(functools.reduce(add, [1, 2, 3, 4]), functools.reduce(lambda a, b: a * b, [1, 2, 3], 10))
print(functools.reduce(add, [], 'init'))
try:
    functools.reduce(add, [])
except TypeError as e:
    print('TypeError:', e)

# partial of an interpreted function
p = functools.partial(add, 10)
print(p(5), p.func is add, p.args, p.keywords)
kw = functools.partial(sorted, key=lambda s: s[-1])
print(kw(['ab', 'ba', 'cc']))


def power(base, exp=2):
    return base ** exp


cube = functools.partial(power, exp=3)
print(cube(2), cube(2, exp=4), functools.partial(cube, 3)())

# lru_cache / cache on interpreted functions
calls = []


@functools.lru_cache(maxsize=None)
def fib(n):
    calls.append(n)
    return n if n < 2 else fib(n - 1) + fib(n - 2)


print(fib(20), len(calls), fib.cache_info().hits, fib.cache_info().misses)
fib.cache_clear()
print(fib.cache_info().currsize, fib.__name__, fib.__wrapped__.__name__)


@functools.cache
def square(x):
    calls.append(('sq', x))
    return x * x


print(square(4), square(4), calls[-1], len([c for c in calls if c == ('sq', 4)]))


# wraps
def deco(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        return ('wrapped', f(*args, **kwargs))
    return wrapper


@deco
def documented(x):
    """Doc of documented."""
    return x * 2


print(documented(4), documented.__name__, documented.__doc__, documented.__wrapped__(1))
print(documented.__qualname__, documented.__module__)

# cmp_to_key
def cmp(a, b):
    return (a > b) - (a < b)


print(sorted([3, 1, 2], key=functools.cmp_to_key(cmp)), sorted(['bb', 'a', 'ccc'], key=functools.cmp_to_key(lambda a, b: len(b) - len(a))))


# cached_property
class Lazy:
    computed = 0

    @functools.cached_property
    def value(self):
        Lazy.computed += 1
        return 'expensive'


lz = Lazy()
print(lz.value, lz.value, Lazy.computed, 'value' in vars(lz))
