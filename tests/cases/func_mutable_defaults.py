# Default values are evaluated once, when the def statement runs.


def app(x, acc=[]):
    acc.append(x)
    return acc


print(app(1), app(2), app(3, []), app(4))
print(app.__defaults__, app(5) is app.__defaults__[0])


def app_none(x, acc=None):
    if acc is None:
        acc = []
    acc.append(x)
    return acc


print(app_none(1), app_none(2))


def kw_mut(*, d={}):
    d[len(d)] = True
    return d


kw_mut()
print(kw_mut(), kw_mut.__kwdefaults__)

calls = []


def side(tag):
    calls.append(tag)
    return len(calls)


def uses(a=side('a'), *, b=side('b')):
    return a, b


print(uses(), uses(), calls)


# defaults are evaluated left to right, positional before keyword-only
def order(x=side('x'), y=side('y'), *, z=side('z')):
    return x, y, z


print(order(), calls)

# redefining re-evaluates
fs = []
for i in range(3):
    def f(v=i, acc=[]):
        acc.append(v)
        return acc
    fs.append(f)
print([g() for g in fs], [g() for g in fs])


# shared default dict used as a cache
def memo_fib(n, _cache={0: 0, 1: 1}):
    if n not in _cache:
        _cache[n] = memo_fib(n - 1) + memo_fib(n - 2)
    return _cache[n]


print(memo_fib(50), len(memo_fib.__defaults__[0]))


# default referencing an enclosing variable binds the current value
def make():
    val = 'first'

    def inner(v=val):
        return v
    val = 'second'
    return inner()


print(make())


# mutating __defaults__ contents affects later calls
def tup(a=[1]):
    return a


tup.__defaults__[0].append(2)
print(tup())


# lambdas in a loop capture defaults per iteration
adders = [lambda x, n=n: x + n for n in range(3)]
print([a(10) for a in adders])


# method defaults are shared between instances
class Basket:
    def __init__(self, items=[]):
        self.items = items

    def add(self, x):
        self.items.append(x)


b1 = Basket()
b2 = Basket()
b1.add('apple')
print(b2.items, b1.items is b2.items)
