# Class decorators and dynamic class creation with type(name, bases, dict).

registry = []


def register(cls):
    registry.append(cls.__name__)
    return cls


def add_repr(cls):
    def __repr__(self):
        fields = ', '.join('%s=%r' % (k, v) for k, v in sorted(vars(self).items()))
        return '%s(%s)' % (type(self).__name__, fields)
    cls.__repr__ = __repr__
    return cls


def tagged(tag):
    def deco(cls):
        cls.tag = tag
        return cls
    return deco


@register
@add_repr
@tagged('t1')
class Thing:
    def __init__(self, a, b):
        self.a = a
        self.b = b


print(Thing(1, 'x'), Thing.tag, registry)


# decorator order: bottom applied first
order = []


def mark(n):
    def deco(cls):
        order.append(n)
        cls.marks = getattr(cls, 'marks', ()) + (n,)
        return cls
    return deco


@mark(1)
@mark(2)
@mark(3)
class Marked:
    pass


print(order, Marked.marks)


# a decorator that replaces the class with something else
def to_instance(cls):
    return cls()


@to_instance
class singleton:
    value = 7

    def get(self):
        return self.value


print(type(singleton).__name__, singleton.get())


# decorator wrapping a class in a subclass
def counted(cls):
    class Wrapped(cls):
        count = 0

        def __init__(self, *a, **kw):
            super().__init__(*a, **kw)
            Wrapped.count += 1
    Wrapped.__name__ = cls.__name__
    Wrapped.__qualname__ = cls.__qualname__
    return Wrapped


@counted
class Widget:
    def __init__(self, name):
        self.name = name


w1 = Widget('a'); w2 = Widget('b')
print(Widget.count, Widget.__name__, w2.name, [k.__name__ for k in Widget.__mro__])


# type(name, bases, dict)
def init(self, v):
    self.v = v


Dynamic = type('Dynamic', (), {'x': 1, '__init__': init, 'double': lambda self: self.v * 2})
d = Dynamic(21)
print(type(d).__name__, Dynamic.__name__, d.double(), d.x, Dynamic.__bases__ == (object,))
print(isinstance(d, Dynamic), type(d) is Dynamic)

Sub = type('Sub', (Dynamic,), {'double': lambda self: 'sub ' + str(Dynamic.double(self))})
print(Sub(4).double(), [k.__name__ for k in Sub.__mro__])

# type() with staticmethod/classmethod/property in the dict
Tools = type('Tools', (object,), {
    'sm': staticmethod(lambda: 'static'),
    'cm': classmethod(lambda cls: 'class ' + cls.__name__),
    'p': property(lambda self: 'prop'),
})
print(Tools.sm(), Tools.cm(), Tools().p)

# type() with a single argument
print(type(1).__name__, type('s').__name__, type(d).__name__, type(Dynamic).__name__, type(type).__name__)
print(type(None).__name__, type(len).__name__, type([]) is list)

# type() argument errors
try:
    type('A', (), {}, 1)
except TypeError as e:
    print('TypeError:', e)
try:
    type()
except TypeError as e:
    print('TypeError:', e)

# __module__ and __qualname__ of dynamic classes
print(Dynamic.__module__, Dynamic.__qualname__)

# class created in a function has a qualname with <locals>
def factory(n):
    class Made:
        size = n
    return Made


M = factory(3)
print(M.size, M.__qualname__, M.__name__)
print(factory(1) is factory(1))

# classes are first-class objects
classes = [int, str, Dynamic, Thing]
print([c.__name__ for c in classes])
print({Dynamic: 'dyn'}[Dynamic])
