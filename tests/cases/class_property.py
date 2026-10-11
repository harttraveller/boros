# property: getter/setter/deleter, read-only errors, inheritance.

class Temperature:
    def __init__(self, c):
        self._c = c

    @property
    def celsius(self):
        """Temperature in Celsius."""
        return self._c

    @celsius.setter
    def celsius(self, value):
        if value < -273.15:
            raise ValueError('below absolute zero')
        self._c = value

    @celsius.deleter
    def celsius(self):
        print('deleting celsius')
        del self._c

    @property
    def fahrenheit(self):
        return self._c * 9 / 5 + 32


t = Temperature(100)
print(t.celsius, t.fahrenheit)
t.celsius = 0
print(t.celsius, t.fahrenheit)
try:
    t.celsius = -300
except ValueError as e:
    print('ValueError:', e)
print(t.celsius)

# read-only property
try:
    t.fahrenheit = 5
except AttributeError as e:
    print('AttributeError:', e)

# deleter
del t.celsius
try:
    t.celsius
except AttributeError as e:
    print('AttributeError:', e)

try:
    del t.fahrenheit
except AttributeError as e:
    print('AttributeError:', e)

# property object introspection
p = Temperature.__dict__['celsius']
print(type(p).__name__, Temperature.celsius.__doc__)
print(Temperature.celsius.fget.__name__, Temperature.fahrenheit.fset)
print(isinstance(Temperature.celsius, property))

# property() called directly
class Box:
    def __init__(self):
        self._v = 1

    def get_v(self):
        return self._v

    def set_v(self, v):
        self._v = v * 10

    v = property(get_v, set_v, None, 'the v')
    only_get = property(get_v)


b = Box()
b.v = 4
print(b.v, Box.v.__doc__, b.only_get)
try:
    b.only_get = 3
except AttributeError as e:
    print('AttributeError:', e)

# property beats the instance dict (data descriptor)
b.__dict__['v'] = 'in dict'
print(b.v)

# property with no getter
class NoGet:
    x = property(None, lambda self, v: print('set', v))


ng = NoGet()
ng.x = 5
try:
    ng.x
except AttributeError as e:
    print('AttributeError:', e)

# overriding a property in a subclass and extending with .getter/.setter
class Base:
    def __init__(self):
        self._n = 0

    @property
    def n(self):
        return self._n

    @n.setter
    def n(self, v):
        self._n = v


class Doubled(Base):
    @Base.n.getter
    def n(self):
        return self._n * 2


d = Doubled()
d.n = 21
print(d.n, Base.n is not Doubled.n)


class Plain(Base):
    n = 'shadowed by plain attribute'


print(Plain().n)

# property computed from other properties, chained
class Rect:
    def __init__(self, w, h):
        self.w = w
        self.h = h

    @property
    def area(self):
        return self.w * self.h

    @property
    def desc(self):
        return 'area=%d' % self.area


r = Rect(3, 4)
print(r.area, r.desc)
r.w = 10
print(r.desc)

print(hasattr(Temperature(1), 'celsius'))

# property on the class returns the property itself
print(Rect.area.__class__.__name__)
