# User-defined descriptors: __get__/__set__/__delete__/__set_name__,
# data vs non-data descriptor precedence.

class Typed:
    def __init__(self, kind):
        self.kind = kind

    def __set_name__(self, owner, name):
        self.name = name
        self.storage = '_' + name

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        return getattr(obj, self.storage, 'unset')

    def __set__(self, obj, value):
        if not isinstance(value, self.kind):
            raise TypeError('%s must be %s, got %s' % (self.name, self.kind.__name__, type(value).__name__))
        setattr(obj, self.storage, value)

    def __delete__(self, obj):
        print('delete', self.name)
        delattr(obj, self.storage)


class Person:
    name = Typed(str)
    age = Typed(int)

    def __init__(self, name, age):
        self.name = name
        self.age = age


p = Person('Ann', 30)
print(p.name, p.age, sorted(vars(p)))
try:
    p.age = 'old'
except TypeError as e:
    print('TypeError:', e)
del p.age
print(p.age)
print(type(Person.name).__name__, Person.name.storage)

# data descriptor wins over the instance dict
p.__dict__['name'] = 'from dict'
print(p.name)


# non-data descriptor loses to the instance dict
class Lazy:
    def __init__(self, func):
        self.func = func
        self.calls = 0

    def __get__(self, obj, cls):
        if obj is None:
            return self
        self.calls += 1
        value = self.func(obj)
        obj.__dict__[self.func.__name__] = value
        return value


class Circle:
    def __init__(self, r):
        self.r = r

    @Lazy
    def area(self):
        print('computing area')
        return 3 * self.r * self.r


c = Circle(2)
print(c.area)
print(c.area)
print(Circle.__dict__['area'].calls)
c2 = Circle(1)
c2.area = 'assigned'    # non-data descriptor: plain instance attribute wins
print(c2.area)


# __get__ receives (None, owner) on class access
class Show:
    def __get__(self, obj, owner):
        return 'get(%s, %s)' % (type(obj).__name__, owner.__name__)


class Host:
    attr = Show()


class SubHost(Host):
    pass


print(Host.attr)
print(Host().attr)
print(SubHost.attr)
print(SubHost().attr)


# a descriptor with only __delete__
class DelOnly:
    def __get__(self, obj, owner):
        return 'DelOnly.get'

    def __delete__(self, obj):
        print('DelOnly.delete')


class UsesDelOnly:
    y = DelOnly()


ud = UsesDelOnly()
ud.__dict__['y'] = 'dict y'
print(ud.y)
del ud.y


# descriptor used for methods (function-like binding)
class BoundMethodLike:
    def __init__(self, f):
        self.f = f

    def __get__(self, obj, owner):
        if obj is None:
            return self.f
        def bound(*a):
            return self.f(obj, *a)
        return bound


class UsesMethodLike:
    @BoundMethodLike
    def hello(self, who):
        return 'hello %s from %s' % (who, type(self).__name__)


print(UsesMethodLike().hello('bob'))
print(UsesMethodLike.hello(UsesMethodLike(), 'carl'))


# descriptors defined on a base class apply to subclasses
class Base:
    v = Typed(int)


class Sub(Base):
    pass


s = Sub()
s.v = 3
print(s.v, s._v)
try:
    s.v = 1.5
except TypeError as e:
    print('TypeError:', e)


# setting a descriptor on the class replaces it
Base.v = 99
print(Sub().v, s.v)


# descriptor __get__ raising AttributeError
class Missing:
    def __get__(self, obj, owner):
        raise AttributeError('descriptor says no')


class HasMissing:
    m = Missing()


print(hasattr(HasMissing(), 'm'), getattr(HasMissing(), 'm', 'default'))
