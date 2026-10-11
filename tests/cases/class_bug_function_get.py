# Functions are non-data descriptors: function.__get__ binds them.

def free(self, x=1):
    return 'free(%s, %s)' % (type(self).__name__, x)


class Host:
    def meth(self):
        return 'meth'


h = Host()
bound = free.__get__(h, Host)
print(bound(), bound(5), bound.__self__ is h, bound.__func__ is free)
print(free.__get__(None, Host) is free)
print(Host.__dict__['meth'].__get__(h)())
print(hasattr(free, '__get__'), callable(free.__get__))
print(type(bound).__name__)

# binding manually with types.MethodType gives the same thing
import types
mt = types.MethodType(free, h)
print(mt(), mt.__self__ is h)

# a descriptor delegating to a function's __get__ (decorator pattern)
class logged:
    def __init__(self, func):
        self.func = func

    def __get__(self, obj, owner=None):
        if obj is None:
            return self
        return self.func.__get__(obj, owner)


class UsesLogged:
    @logged
    def hello(self, who):
        return 'hello ' + who


print(UsesLogged().hello('you'))
