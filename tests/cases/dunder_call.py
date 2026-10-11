# __call__ on instances: direct calls, calls from host code (map, sorted
# key, functools), callable(), and error messages.
import functools


class Adder:
    def __init__(self, n):
        self.n = n

    def __call__(self, x, y=0, *rest, scale=1, **kw):
        return (self.n + x + y + sum(rest)) * scale, sorted(kw.items())


add = Adder(10)
print(add(1))
print(add(1, 2, 3, 4, scale=2, z=9))
print(add(*[1, 2], **{'scale': 3}))
print(list(map(Adder(1), [1, 2, 3])))
print(sorted([3, 1, 2], key=Adder(0)))
print(list(filter(Adder(-2), [1, 2, 3])))
print(functools.reduce(lambda a, b: a + b, map(Adder(5), [0, 1])))
p = functools.partial(Adder(100), 1, scale=10)
print(p(2))
print(callable(add), callable(Adder), callable(Adder(0).__call__), callable(3))


class NotCallable:
    pass


nc = NotCallable()
print(callable(nc))
for label, f in [('nc()', lambda: nc()),
                 ('nc(1, x=2)', lambda: nc(1, x=2)),
                 ('map(nc, [1])', lambda: list(map(nc, [1]))),
                 ('sorted key', lambda: sorted([2, 1], key=nc)),
                 ('Adder(1)()', lambda: Adder(1)()),
                 ('Adder(1)(1, 2, foo=3, scale=1, bar=4)', lambda: Adder(1)(1, 2, foo=3, scale=1, bar=4)),
                 ('Adder(1)(1, x=2)', lambda: Adder(1)(1, x=2))]:
    try:
        print(label, '->', f())
    except TypeError as e:
        print(label, '-> TypeError:', e)


# __call__ looked up on the class, not the instance
nc.__call__ = lambda: 'instance attribute'
print(callable(nc))
try:
    nc()
except TypeError as e:
    print('TypeError:', e)


# __call__ can be any callable class attribute: staticmethod, callable instance
class Static:
    __call__ = staticmethod(lambda *a: ('static', a))


print(Static()(1, 2))


class Forward:
    __call__ = Adder(1000)


print(Forward()(1))


# __call__ added after class creation, and inherited
class Later:
    pass


Later.__call__ = lambda self, v: v * 2
print(Later()(21), callable(Later()))


class SubLater(Later):
    pass


print(SubLater()(5))


# a callable instance used as a decorator and as a method
class Deco:
    def __init__(self, f):
        self.f = f
        self.calls = 0
        self.__name__ = f.__name__
        self.__doc__ = f.__doc__

    def __call__(self, *a, **k):
        self.calls += 1
        return self.f(*a, **k)


@Deco
def square(x):
    """Square it."""
    return x * x


print(square(4), square(5), square.calls, square.__name__, square.__doc__)


class Host:
    m = Adder(7)   # instances are not descriptors: no self is passed


print(Host().m(1))


# recursion through __call__
class Fact:
    def __call__(self, n):
        return 1 if n <= 1 else n * self(n - 1)


print(Fact()(10))
