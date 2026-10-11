# functools helpers and key functions applied to interpreted functions.
import functools
import operator


# partial
def p3(a, b, c=3, *, d=4):
    return (a, b, c, d)


pp = functools.partial(p3, 1, d=9)
print(pp(2), pp(2, 5), pp(b=7), pp(2, d=0), pp.args, pp.keywords, pp.func is p3)
pp2 = functools.partial(pp, 8)
print(pp2(), pp2.func is p3, pp2.args)
try:
    pp()
except TypeError as e:
    print('TypeError:', e)
try:
    functools.partial(p3, a=1)(2)
except TypeError as e:
    print('TypeError:', e)
print(list(map(functools.partial(operator.mul, 3), [1, 2, 3])))
add = lambda x, y: x + y
inc = functools.partial(add, 1)
print(inc(10), [inc(i) for i in range(3)])


# reduce
print(functools.reduce(lambda a, b: a * b, range(1, 6)))
print(functools.reduce(lambda a, b: a + b, [], 0))
print(functools.reduce(lambda acc, x: acc + [x * 2], [1, 2, 3], []))
try:
    functools.reduce(lambda a, b: a, [])
except TypeError as e:
    print('TypeError:', e)


def boom(a, b):
    raise ValueError('from reducer %r %r' % (a, b))


try:
    functools.reduce(boom, [1, 2, 3])
except ValueError as e:
    print('ValueError:', e)


# lru_cache / cache
@functools.lru_cache(maxsize=None)
def fib(n):
    return n if n < 2 else fib(n - 1) + fib(n - 2)


print(fib(60), fib.cache_info())


@functools.cache
def fact(n):
    return 1 if n <= 1 else n * fact(n - 1)


print(fact(20), fact(21), fact.cache_info().hits)


@functools.lru_cache(maxsize=2)
def ident(x):
    print('compute', x)
    return x


ident(1)
ident(2)
ident(1)
ident(3)
ident(2)
print(ident.cache_info())
ident.cache_clear()
print(ident.cache_info())


@functools.lru_cache
def kw_cached(a, b=0, *, c=0):
    print('miss', a, b, c)
    return a + b + c


print(kw_cached(1), kw_cached(1), kw_cached(1, c=2), kw_cached(1, c=2), kw_cached(a=1))
print(kw_cached.__name__, kw_cached.__wrapped__(5))


class M:
    @functools.lru_cache(maxsize=None)
    def meth(self, x):
        return x + 1


m = M()
print(m.meth(1), m.meth(1), M.meth.cache_info().hits)


# cmp_to_key and key functions
def cmp(a, b):
    return (a > b) - (a < b)


print(sorted([3, 1, 2], key=functools.cmp_to_key(lambda a, b: cmp(b, a))))
words = ['banana', 'Apple', 'cherry', 'date']
print(sorted(words, key=functools.cmp_to_key(lambda a, b: cmp(len(a), len(b)) or cmp(a, b))))
print(sorted(words, key=str.lower), sorted(words, key=len, reverse=True))
print(sorted([3, -1, 2], key=abs), sorted([(1, 'b'), (1, 'a'), (0, 'z')], key=lambda t: t[0]))


class Rec:
    def __init__(self, name, age):
        self.name = name
        self.age = age


people = [Rec('ann', 30), Rec('bob', 25), Rec('cid', 30)]
print([p.name for p in sorted(people, key=lambda p: (-p.age, p.name))])
print([p.name for p in sorted(people, key=operator.attrgetter('age'))])
print(min(people, key=lambda p: p.age).name, max(people, key=lambda p: (p.age, p.name)).name)
people.sort(key=lambda p: p.name, reverse=True)
print([p.name for p in people])


# map / filter with interpreted callables
print(list(map(lambda x, y: x + y, [1, 2], [10, 20])), list(filter(lambda x: x % 2, range(6))))
print(list(filter(None, [0, 1, '', 'a', [], [0]])))


def square(x):
    return x * x


print(list(map(square, range(5))), dict(map(lambda kv: (kv[1], kv[0]), {'a': 1}.items())))
print(sum(map(square, filter(lambda n: n > 2, range(6)))))
print(any(map(lambda x: x > 3, [1, 5])), all(map(bool, [1, 0])))


class Even:
    def __call__(self, x):
        return x % 2 == 0


print(list(filter(Even(), range(7))), list(map(Even(), [1, 2])))
print(sorted(range(6), key=Even()))


# cached_property and partialmethod
class CP:
    @functools.cached_property
    def val(self):
        print('computing')
        return 42


c = CP()
print(c.val, c.val, 'val' in vars(c))


class PM:
    def set(self, k, v):
        return (k, v)
    set_a = functools.partialmethod(set, 'a')


print(PM().set_a(1))
