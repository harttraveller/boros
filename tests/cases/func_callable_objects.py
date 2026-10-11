# Callable objects: __call__, callable(), calling non-callables.


class Adder:
    def __init__(self, k):
        self.k = k

    def __call__(self, x, *, scale=1):
        return (x + self.k) * scale


add5 = Adder(5)
print(add5(1), add5(1, scale=2), callable(add5), list(map(add5, [1, 2])))
print(sorted([3, 1, 2], key=Adder(-10)), add5.__call__(2))


class NotCallable:
    pass


values = [NotCallable(), 5, 'abc', None, [1], {'a': 1}]
for v in values:
    try:
        v()
    except TypeError as e:
        print('TypeError:', e)
print([callable(v) for v in values])
print(callable(Adder), callable(len), callable(lambda: 0), callable(print), callable(add5.__call__))


# __call__ added to the class after creation is used
class Late:
    pass


Late.__call__ = lambda self, v: v * 3
print(Late()(3), callable(Late()))


# an instance attribute named __call__ is not used by the call syntax
class InstCall:
    pass


ic = InstCall()
ic.__call__ = lambda: 'inst'
try:
    ic()
except TypeError as e:
    print('TypeError:', e)
print(callable(ic), ic.__call__())


# __call__ inherited, overridden, and calling super().__call__
class Base:
    def __call__(self, x):
        return 'base %s' % x


class Child(Base):
    def __call__(self, x):
        return 'child ' + super().__call__(x)


print(Base()(1), Child()(2), callable(Child()))


# callable returning callables; callable as a key and as a decorator
class Multiplier:
    def __init__(self, n):
        self.n = n

    def __call__(self, f):
        def w(*a):
            return f(*a) * self.n
        return w


@Multiplier(3)
def three():
    return 2


print(three())


# __call__ defined as staticmethod / classmethod
class S:
    @staticmethod
    def __call__(x):
        return 'static %s' % x


class CM:
    @classmethod
    def __call__(cls, x):
        return '%s %s' % (cls.__name__, x)


print(S()(1), CM()(2))


# functions stored in containers and called indirectly
ops = {'add': lambda a, b: a + b, 'sub': lambda a, b: a - b, 'neg': Adder(0)}
print(ops['add'](2, 3), ops['sub'](2, 3), ops['neg'](4, scale=-1))


# generators of callables and calling bound methods stored earlier
class Counter:
    def __init__(self):
        self.n = 0

    def inc(self):
        self.n += 1
        return self.n


c = Counter()
incs = [c.inc] * 3
print([f() for f in incs], c.n)


# calling with argument errors on a callable object
try:
    add5()
except TypeError as e:
    print('TypeError:', e)
try:
    add5(1, 2)
except TypeError as e:
    print('TypeError:', e)
