# Instantiation protocol: __new__, __init__, singletons, factories.

class Singleton:
    _instance = None

    def __new__(cls, *args, **kw):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.inits = 0
        return cls._instance

    def __init__(self, value):
        self.inits += 1
        self.value = value


a = Singleton(1)
b = Singleton(2)
print(a is b, a.value, a.inits, type(a).__name__)


# __new__ returning an instance of another class skips __init__
class Other:
    def __init__(self):
        self.tag = 'other-init'


class Factory:
    def __new__(cls, kind):
        if kind == 'other':
            return Other()
        if kind == 'num':
            return 42
        return super().__new__(cls)

    def __init__(self, kind):
        print('Factory.__init__', kind)
        self.kind = kind


x = Factory('self')
y = Factory('other')
z = Factory('num')
print(type(x).__name__, x.kind, type(y).__name__, y.tag, z)


# __new__ receives the actual subclass
class Base:
    def __new__(cls, *a):
        obj = super().__new__(cls)
        obj.made_by = cls.__name__
        return obj


class Sub(Base):
    def __init__(self, v):
        self.v = v


s = Sub(3)
print(s.made_by, s.v, isinstance(s, Sub))


# explicit object.__new__ and cls.__new__
class Plain:
    def __init__(self):
        self.inited = True


p = object.__new__(Plain)
print(type(p).__name__, hasattr(p, 'inited'))
p.__init__()
print(p.inited)
q = Plain.__new__(Plain)
print(type(q).__name__, hasattr(q, 'inited'))


# __init__ must return None
class BadInit:
    def __init__(self):
        return 5


try:
    BadInit()
except TypeError as e:
    print('TypeError:', e)


# arguments to a class without __init__
class NoInit:
    pass


try:
    NoInit(1, 2)
except TypeError as e:
    print('TypeError:', e)
try:
    NoInit(a=1)
except TypeError as e:
    print('TypeError:', e)


# __init__ argument errors mention the qualified name
class Two:
    def __init__(self, a, b=2, *, c):
        self.t = (a, b, c)


print(Two(1, c=3).t)
for args, kw in [((), {'c': 1}), ((1,), {}), ((1, 2, 3), {'c': 1}), ((1,), {'c': 1, 'd': 2})]:
    try:
        Two(*args, **kw)
    except TypeError as e:
        print('TypeError:', e)


# __new__ only, no __init__ ; __new__ with extra args is fine
class OnlyNew:
    def __new__(cls, a, b):
        obj = super().__new__(cls)
        obj.total = a + b
        return obj


print(OnlyNew(2, 3).total)


# __init__ only: object.__new__ ignores args
class OnlyInit:
    def __init__(self, a):
        self.a = a


print(OnlyInit(5).a)


# passing args up to object.__new__ when __new__ is overridden is an error
class PassesArgs:
    def __new__(cls, a):
        return super().__new__(cls, a)


try:
    PassesArgs(1)
except TypeError as e:
    print('TypeError:', e)


# calling __init__ again re-initializes
class Re:
    def __init__(self, n=0):
        self.n = n


r = Re(1)
r.__init__(5)
print(r.n)


# instances created via a classmethod that uses cls.__new__ directly
class Fast:
    def __init__(self):
        raise RuntimeError('should not run')

    @classmethod
    def raw(cls, v):
        obj = cls.__new__(cls)
        obj.v = v
        return obj


print(Fast.raw(9).v)


# class-level counter of instances via __new__ and __init__ ordering
log = []


class Ordered:
    def __new__(cls, *a):
        log.append('new')
        return super().__new__(cls)

    def __init__(self, *a):
        log.append('init')


Ordered(1)
print(log)


# __call__ makes instances callable; calling a class is just instantiation
class Adder:
    def __init__(self, n):
        self.n = n

    def __call__(self, x):
        return x + self.n


add3 = Adder(3)
print(add3(4), list(map(add3, [1, 2])), callable(add3))
try:
    NoInit()()
except TypeError as e:
    print('TypeError:', e)
