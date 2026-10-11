# __slots__: storage, errors when setting other attributes, inheritance.

class Point:
    __slots__ = ('x', 'y')

    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __repr__(self):
        return 'Point(%r, %r)' % (self.x, self.y)


p = Point(1, 2)
print(p, p.x + p.y)
p.x = 10
print(p)
try:
    p.z = 3
except AttributeError as e:
    print('AttributeError:', e)
print(hasattr(p, '__dict__'))
try:
    vars(p)
except TypeError as e:
    print('TypeError:', e)

# unset slot
class Lazy:
    __slots__ = ['value']


lz = Lazy()
try:
    lz.value
except AttributeError as e:
    print('AttributeError:', e)
print(hasattr(lz, 'value'), getattr(lz, 'value', 'dflt'))
lz.value = 'set'
print(lz.value)
del lz.value
print(hasattr(lz, 'value'))
try:
    del lz.value
except AttributeError as e:
    print('AttributeError:', e)

# slot descriptors live on the class
print(Point.__slots__)
print(sorted(k for k in Point.__dict__ if not k.startswith('__')))

# single string slot
class One:
    __slots__ = 'only'


o = One()
o.only = 1
print(o.only)
try:
    o.other = 2
except AttributeError as e:
    print('AttributeError:', e)

# subclass without __slots__ gets a __dict__
class Point3(Point):
    pass


p3 = Point3(1, 2)
p3.z = 3
print(p3.z, p3.__dict__)

# subclass with its own __slots__ stays dict-less
class Point4(Point):
    __slots__ = ('w',)


p4 = Point4(1, 2)
p4.w = 4
print(p4.x, p4.y, p4.w)
try:
    p4.q = 5
except AttributeError as e:
    print('AttributeError:', e)

# __dict__ in __slots__ allows arbitrary attributes
class WithDict:
    __slots__ = ('a', '__dict__')


wd = WithDict()
wd.a = 1
wd.b = 2
print(wd.a, wd.b, wd.__dict__)

# class attributes can still be read via a slotted instance
class SlotsAndClassAttr:
    __slots__ = ('v',)
    kind = 'shared'

    def method(self):
        return 'method ' + self.kind


s = SlotsAndClassAttr()
print(s.kind, s.method())

# private slot names are mangled
class Private:
    __slots__ = ('__secret',)

    def __init__(self):
        self.__secret = 42

    def reveal(self):
        return self.__secret


pr = Private()
print(pr.reveal(), pr._Private__secret)

# slots with defaults via __init__ and with inheritance from a dict-ful base
class Base:
    pass


class SlottedChild(Base):
    __slots__ = ('a',)


sc = SlottedChild()
sc.a = 1
sc.anything = 2   # base provides __dict__
print(sc.a, sc.anything)
