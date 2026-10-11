# staticmethod and classmethod, called on the class and on instances.

class Pizza:
    default_size = 10

    def __init__(self, toppings, size=None):
        self.toppings = toppings
        self.size = size or self.default_size

    @classmethod
    def margherita(cls):
        return cls(['mozzarella', 'tomato'])

    @classmethod
    def with_size(cls, size, *toppings):
        return cls(list(toppings), size)

    @staticmethod
    def area(r):
        return r * r * 3

    @staticmethod
    def describe(*args, **kw):
        return 'describe%r%r' % (args, sorted(kw.items()))

    def __repr__(self):
        return '%s(%r, %r)' % (type(self).__name__, self.toppings, self.size)


class BigPizza(Pizza):
    default_size = 20


print(Pizza.margherita())
print(BigPizza.margherita())
print(Pizza.margherita().margherita())
print(BigPizza.with_size(5, 'ham', 'egg'))
print(Pizza.area(2), Pizza([]).area(3))
print(Pizza.describe(1, 2, a=3), Pizza([]).describe())

# the raw objects in the class dict
sm = Pizza.__dict__['area']
cm = Pizza.__dict__['margherita']
print(type(sm).__name__, type(cm).__name__)
print(sm.__func__(4), cm.__func__(Pizza))
print(Pizza.margherita.__self__ is Pizza, BigPizza.margherita.__self__ is BigPizza)
print(Pizza([]).margherita.__self__ is Pizza)
print(Pizza.margherita.__func__ is cm.__func__)
print(Pizza.area is sm.__func__)

# staticmethod/classmethod created by calling directly
def helper(x):
    return x + 1


def clsinfo(cls, extra=''):
    return cls.__name__ + extra


class Direct:
    inc = staticmethod(helper)
    info = classmethod(clsinfo)


print(Direct.inc(1), Direct().inc(2), Direct.info(), Direct().info('!'))

# classmethod used as an alternate constructor with inheritance and super
class Shape:
    def __init__(self, kind):
        self.kind = kind

    @classmethod
    def create(cls, *a):
        obj = cls(*a)
        obj.created_by = cls.__name__
        return obj


class Circle(Shape):
    def __init__(self, r):
        super().__init__('circle')
        self.r = r

    @classmethod
    def create(cls, r):
        obj = super().create(r)
        obj.extra = True
        return obj


c = Circle.create(3)
print(c.kind, c.r, c.created_by, c.extra, type(c).__name__)

# errors from calling with wrong arguments
try:
    Pizza.area()
except TypeError as e:
    print('TypeError:', e)
try:
    Pizza.margherita(1)
except TypeError as e:
    print('TypeError:', e)

# a regular method called through the class needs self
try:
    Pizza.__repr__()
except TypeError as e:
    print('TypeError:', e)
print(Pizza.__repr__(Pizza(['x'])))

# staticmethod is callable directly (3.10+)
print(callable(sm), sm(10))

# classmethod in a class decorator context / counting instances
class Registry:
    _items = None

    @classmethod
    def register(cls, item):
        if cls._items is None:
            cls._items = []
        cls._items.append(item)
        return item

    @classmethod
    def items(cls):
        return list(cls._items or ())


class SubRegistry(Registry):
    pass


Registry.register('a')
SubRegistry.register('b')
print(Registry.items(), SubRegistry.items(), '_items' in SubRegistry.__dict__)

# staticmethod accessed via super
class S1:
    @staticmethod
    def s():
        return 'S1.s'


class S2(S1):
    def call_it(self):
        return super().s()


print(S2().call_it())
