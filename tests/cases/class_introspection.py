# Introspection of classes and instances.

class Base:
    """Base docstring."""
    kind = 'base'

    def method(self):
        return 1


class Point(Base):
    dims = 2

    def __init__(self, x, y):
        self.x = x
        self.y = y

    def norm1(self):
        return abs(self.x) + abs(self.y)

    @property
    def pair(self):
        return (self.x, self.y)


p = Point(3, -4)

print(Point.__name__, Point.__qualname__, Point.__module__, p.__module__)
print(p.__class__.__name__, p.__class__ is Point, type(p) is Point)
print([c.__name__ for c in Point.__mro__], [c.__name__ for c in Point.__bases__])
print(Base.__doc__, Point.__doc__)
print(p.__dict__, vars(p) is p.__dict__)
print(sorted(k for k in Point.__dict__ if not k.startswith('__')))
print('__init__' in Point.__dict__, 'method' in Point.__dict__, '__module__' in Point.__dict__)
print(Point.__dict__['dims'], type(Point.__dict__).__name__)
print(sorted(k for k in vars(Point) if not k.startswith('__')))

# __dict__ of the class is read-only
try:
    Point.__dict__['dims'] = 3
except TypeError as e:
    print('TypeError:', e)

# writing through the instance __dict__
p.__dict__['z'] = 5
print(p.z, sorted(vars(p)))
vars(p)['w'] = 6
print(p.w)

# dir() filtered to user names
print([n for n in dir(p) if not n.startswith('__')])
print([n for n in dir(Point) if not n.startswith('__')])
print('__init__' in dir(p), '__class__' in dir(p), '__dict__' in dir(p), '__init__' in dir(Point))

# custom __dir__
class Custom:
    def __dir__(self):
        return ['b', 'a', 'c']


print(dir(Custom()))

# getattr / setattr / delattr / hasattr with defaults
print(getattr(p, 'x'), getattr(p, 'nope', None), getattr(Point, 'dims'), getattr(Point, 'nope', 'dflt'))
setattr(p, 'x', 100)
setattr(Point, 'added', 'class attr')
print(p.x, p.added, Point.added)
delattr(p, 'x')
print(hasattr(p, 'x'), hasattr(p, 'y'), hasattr(Point, 'added'), hasattr(Point, 'pair'))
delattr(Point, 'added')
print(hasattr(p, 'added'))
try:
    delattr(p, 'x')
except AttributeError as e:
    print('AttributeError:', e)
try:
    getattr(p, 'nope')
except AttributeError as e:
    print('AttributeError:', e)
try:
    getattr(p, 5)
except TypeError as e:
    print('TypeError:', e)
try:
    setattr(p, 5, 1)
except TypeError as e:
    print('TypeError:', e)
try:
    hasattr(p, None)
except TypeError as e:
    print('TypeError:', e)

# getattr on methods
m = getattr(p, 'norm1')
p.x = 1
print(m(), m.__name__, m.__qualname__, m.__self__ is p, m.__func__ is Point.norm1)
print(Point.norm1.__name__, Point.norm1.__qualname__)
print(type(m).__name__, type(Point.norm1).__name__)

# callable()
print(callable(Point), callable(p), callable(p.norm1), callable(p.x))

class WithCall:
    def __call__(self, a):
        return a * 2


print(callable(WithCall()), WithCall()(21))

# __subclasses__
class S1(Base): pass
class S2(Base): pass
print([c.__name__ for c in Base.__subclasses__()])

# the type of a class and of type
print(type(Point).__name__, type(Point) is type, Point.__class__.__name__)

# __init__ / methods docstrings and names
class Doc:
    def f(self):
        """f docs"""

    def g(self):
        pass


print(Doc.f.__doc__, Doc.g.__doc__, Doc.__doc__)

# __qualname__ of methods in nested classes
class Out:
    class In:
        def m(self):
            pass


print(Out.In.m.__qualname__, Out.In.__module__)

# vars() of a class without user attributes
class Empty:
    pass


print(sorted(k for k in vars(Empty) if k in ('__module__', '__doc__')))
print(Empty.__dict__.get('__doc__'), Empty.__name__)

# repr of classes from __main__
print(repr(Point), str(Base), repr(int))

# instance with no attributes
e = Empty()
print(vars(e), e.__dict__ == {}, dir(e) == sorted(dir(e)))
