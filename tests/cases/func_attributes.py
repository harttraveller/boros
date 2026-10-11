# Function attributes: __name__, __qualname__, __doc__, __defaults__,
# __kwdefaults__, __module__, __globals__ and custom attributes.


def f(a, b=2, *args, c, d=4, **kw):
    "doc of f"
    return (a, b, c, d)


print(f.__name__, f.__qualname__, f.__doc__, f.__module__)
print(f.__defaults__, f.__kwdefaults__)


def nodoc():
    pass


def notfirst():
    x = 1
    "not a docstring"
    return x


print(nodoc.__doc__, notfirst.__doc__, nodoc.__defaults__, nodoc.__kwdefaults__)

# custom attributes
f.custom = 1
f.tags = ['a']
print(f.custom, f.tags, hasattr(f, 'custom'), getattr(f, 'missing', 'dflt'))
del f.custom
print(hasattr(f, 'custom'))
try:
    nodoc.missing
except AttributeError as e:
    print('AttributeError:', e)

# renaming does not change the qualname and vice versa
f.__name__ = 'renamed'
print(f.__name__, f.__qualname__)
f.__qualname__ = 'Q.f'
print(f.__name__, f.__qualname__)
f.__doc__ = 'new doc'
print(f.__doc__)


# __defaults__ / __kwdefaults__ are read at call time
def g(x=1, y=2):
    return (x, y)


g.__defaults__ = (5,)
try:
    g()
except TypeError as e:
    print('TypeError:', e)
print(g(0))
g.__defaults__ = (7, 8)
print(g())
g.__defaults__ = None
try:
    g()
except TypeError as e:
    print('TypeError:', e)


def kk(*, a=1, b):
    return (a, b)


print(kk.__kwdefaults__)
kk.__kwdefaults__ = {'a': 7, 'b': 8}
print(kk())
kk.__kwdefaults__ = None
try:
    kk()
except TypeError as e:
    print('TypeError:', e)

# defaults tuple holds the very objects
default_list = []


def uses(x=default_list):
    return x


print(uses() is default_list, uses.__defaults__[0] is default_list)


# qualnames of nested functions, methods, nested classes and lambdas
class C:
    def m(self):
        "mdoc"
        def inner():
            pass
        return inner

    class D:
        def n(self):
            pass

    lam = lambda self: 0


def outer():
    def inner():
        def innermost():
            pass
        return innermost
    return inner


print(C.m.__qualname__, C().m().__qualname__, C.D.n.__qualname__, C.D.__qualname__, C.lam.__qualname__)
print(outer().__qualname__, outer()().__qualname__, outer.__qualname__)
print(C().m.__name__, C().m.__qualname__)
lam = lambda: 0
print(lam.__name__, lam.__qualname__, lam.__doc__)
print((lambda: (lambda: 0))().__qualname__)


def make_class():
    class Local:
        def meth(self):
            pass
    return Local


print(make_class().__qualname__, make_class().meth.__qualname__)

# __globals__
print(f.__globals__ is globals(), f.__globals__['__name__'])

# type names
print(type(f).__name__, type(C().m).__name__, type(lam).__name__)


# functions are hashable, compare by identity, usable as dict keys
def h1():
    pass


def h2():
    pass


table = {h1: 'one', h2: 'two'}
print(table[h1], table[h2], h1 == h1, h1 == h2, h1 != h2)

# bound methods
o = C()
bm = o.m
print(bm.__self__ is o, bm.__func__ is C.m, bm == o.m, bm.__name__, bm.__qualname__)
try:
    bm.attr = 1
except AttributeError as e:
    print('AttributeError:', e)
