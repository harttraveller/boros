# Decorators: simple, with arguments, stacked, class-based, on methods.
import functools

log = []


def copy_meta(src):
    def apply(dst):
        dst.__name__ = src.__name__
        dst.__qualname__ = src.__qualname__
        dst.__doc__ = src.__doc__
        dst.__wrapped__ = src
        return dst
    return apply


def simple(f):
    def wrapper(*args, **kwargs):
        log.append('before ' + f.__name__)
        r = f(*args, **kwargs)
        log.append('after ' + f.__name__)
        return r
    return wrapper


@simple
def greet(name, punct='!'):
    return 'hello ' + name + punct


print(greet('bob'), greet('amy', punct='?'), log)
print(greet.__name__, greet.__qualname__)


# decorator with arguments
def repeat(times):
    def deco(f):
        @copy_meta(f)
        def wrapper(*a):
            return [f(*a) for _ in range(times)]
        return wrapper
    return deco


@repeat(3)
def hi(x):
    "say hi"
    return 'hi ' + x


print(hi('bob'), hi.__name__, hi.__qualname__, hi.__doc__, hi.__wrapped__('x'))

# evaluation order: decorator expressions top-down, application bottom-up
order = []


def mk(n):
    order.append('make %d' % n)

    def d(f):
        order.append('apply %d' % n)

        def w():
            return 'd%d(%s)' % (n, f())
        return w
    return d


@mk(1)
@mk(2)
@mk(3)
def base():
    return 'base'


print(order)
print(base())


# decorator returning a non-function
def to_value(f):
    return f()


@to_value
def computed():
    return 99


print(computed)


# arbitrary decorator expressions (PEP 614)
decos = {'x': lambda f: (lambda: 'wrapped ' + f())}


@decos['x']
def pep614():
    return 'orig'


print(pep614())


class Registry:
    def __init__(self):
        self.items = {}

    def register(self, name):
        def deco(f):
            self.items[name] = f
            return f
        return deco


reg = Registry()


@reg.register('add')
def add(a, b):
    return a + b


@reg.register('mul')
def mul(a, b):
    return a * b


print(sorted(reg.items), reg.items['add'](2, 3), reg.items['mul'](2, 3), add is reg.items['add'])


# class-based decorator
class CountCalls:
    def __init__(self, f):
        self.f = f
        self.calls = 0

    def __call__(self, *args, **kwargs):
        self.calls += 1
        return self.f(*args, **kwargs)


@CountCalls
def square(x):
    return x * x


print(square(3), square(4), square.calls, type(square).__name__, callable(square))


# class-based decorator usable on methods through __get__
class Tracer:
    def __init__(self, func):
        self.func = func
        self.calls = 0

    def __call__(self, *args, **kwargs):
        self.calls += 1
        return self.func(*args, **kwargs)

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        return functools.partial(self.__call__, obj)


class W:
    def __init__(self, n):
        self.n = n

    @Tracer
    def double(self):
        return self.n * 2


w = W(4)
print(w.double(), W(5).double(), W.double.calls, type(W.double).__name__)


# function decorators on methods, staticmethods, classmethods, properties
def tag(f):
    @copy_meta(f)
    def w(*a, **k):
        return ('tag', f(*a, **k))
    return w


class K:
    def __init__(self, v):
        self.v = v

    @tag
    def get(self):
        return self.v

    @staticmethod
    @tag
    def st(x):
        return x

    @classmethod
    @tag
    def cm(cls):
        return cls.__name__

    @property
    @tag
    def p(self):
        return self.v

    @tag
    def __len__(self):
        return 0


print(K(1).get(), K.st(2), K(0).st(3), K.cm(), K(9).cm(), K(3).p)
print(K.get.__qualname__, K.get.__name__)
print(len(K(1)) if False else 'skip')


# decorator that adds attributes to the function
def mark(**attrs):
    def d(f):
        for k, v in attrs.items():
            setattr(f, k, v)
        return f
    return d


@mark(slow=True, level=3)
def marked():
    pass


print(marked.slow, marked.level)


# class decorator
def add_attr(cls):
    cls.extra = 'added'
    return cls


@add_attr
class Dc:
    pass


print(Dc.extra)


# decorator that replaces the class with a factory function
def singleton(cls):
    inst = {}

    def get(*a):
        if cls not in inst:
            inst[cls] = cls(*a)
        return inst[cls]
    return get


@singleton
class Config:
    def __init__(self, v):
        self.v = v


print(Config(1).v, Config(2).v, Config(3) is Config(4))


# property setter/deleter decorators
class P:
    def __init__(self):
        self._v = 0

    @property
    def v(self):
        return self._v

    @v.setter
    def v(self, val):
        self._v = val * 2

    @v.deleter
    def v(self):
        self._v = -1


p = P()
p.v = 5
print(p.v)
del p.v
print(p.v)


# decorating a lambda result and decorating with a lambda
dec = lambda f: lambda *a: f(*a) + 1


@dec
def plus(a, b):
    return a + b


print(plus(1, 2))


# memoizing decorator with a closure dict
def memo(f):
    cache = {}

    def w(n):
        if n not in cache:
            cache[n] = f(n)
        return cache[n]
    w.cache = cache
    return w


@memo
def fib(n):
    return n if n < 2 else fib(n - 1) + fib(n - 2)


print(fib(80), len(fib.cache))
