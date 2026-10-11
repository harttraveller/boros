# __init_subclass__ with keyword arguments, registries, and __set_name__.

class Plugin:
    registry = {}

    def __init_subclass__(cls, name=None, **kw):
        super().__init_subclass__(**kw)
        cls.plugin_name = name or cls.__name__.lower()
        Plugin.registry[cls.plugin_name] = cls


class Alpha(Plugin, name='alpha!'):
    pass


class Beta(Plugin):
    pass


class Gamma(Beta, name='g'):
    pass


print(sorted(Plugin.registry))
print(Alpha.plugin_name, Beta.plugin_name, Gamma.plugin_name)
print(Plugin.registry['g'] is Gamma)
print(hasattr(Plugin, 'plugin_name'))


# __init_subclass__ is implicitly a classmethod
class Counter:
    count = 0

    def __init_subclass__(cls):
        Counter.count += 1
        cls.serial = Counter.count


class C1(Counter): pass
class C2(Counter): pass
class C3(C1): pass

print(C1.serial, C2.serial, C3.serial, Counter.count)


# chained __init_subclass__ across hierarchy
class A:
    def __init_subclass__(cls, **kw):
        print('A.__init_subclass__', cls.__name__, sorted(kw.items()))
        super().__init_subclass__()


class B(A):
    def __init_subclass__(cls, flag=False, **kw):
        print('B.__init_subclass__', cls.__name__, flag)
        super().__init_subclass__(**kw)


class Cc(B, flag=True, other=1):
    pass


# unexpected keyword to object.__init_subclass__
try:
    class Bad(object, spam=1):
        pass
except TypeError as e:
    print('TypeError:', e)


# __set_name__ is called for descriptors in the class body
class Named:
    def __set_name__(self, owner, name):
        self.owner = owner.__name__
        self.name = name


class Holder:
    first = Named()
    second = Named()


print(Holder.first.owner, Holder.first.name, Holder.second.name)


# __set_name__ is not called for attributes added after class creation
Holder.third = Named()
print(hasattr(Holder.third, 'name'))


# __init_subclass__ sees the fully populated class namespace
class Validated:
    def __init_subclass__(cls):
        missing = [m for m in ('run', 'stop') if not hasattr(cls, m)]
        cls.missing = missing


class Impl(Validated):
    def run(self):
        pass


print(Impl.missing)


# type() with kwargs calls __init_subclass__ too
T = type('T', (Plugin,), {}, name='via-type')
print(T.plugin_name, Plugin.registry['via-type'] is T)
