import sys
module_level = 'm'


def show(d):
    return sorted(k for k in d if not k.startswith('__'))


# module level: locals() is globals()
print(locals() is globals(), vars() is globals())
print('module_level' in globals(), 'show' in dir())
globals()['injected'] = 'via globals()'
print(injected)


def func(a, b=2, *args, **kw):
    c = a + b
    loc = locals()
    print(sorted(loc), loc['c'], loc['args'], loc['kw'])
    print(sorted(vars()) == sorted(dir()))
    print('module_level' in globals(), 'c' in globals())
    globals()['from_func'] = c
    loc['c'] = 'changed'  # locals() is a snapshot: does not change c
    return c


print(func(1, 3, 4, k=5))
print(from_func)


def fresh_snapshot():
    x = 1
    first = locals()
    x = 2
    second = locals()
    return first['x'], second['x'], first is second


print(fresh_snapshot())


def nested_globals():
    def inner():
        return globals() is sys.modules[__name__].__dict__ if False else 'module_level' in globals()
    return inner()


print(nested_globals())


def lambdas_and_locals():
    f = lambda q: sorted(locals())
    return f(1)


print(lambdas_and_locals())


class Body:
    a = 1
    b = a + 1
    names = sorted(k for k in locals() if not k.startswith('__'))
    has_module = '__module__' in locals()
    qual = locals()['__qualname__']


print(Body.names, Body.has_module, Body.qual)


class Obj:
    cls_attr = 0

    def __init__(self):
        self.x = 1
        self.y = 2

    def method(self):
        return 3


o = Obj()
print(vars(o))
vars(o)['z'] = 3
print(o.z, o.__dict__ is vars(o))
print(show(vars(Obj)))
print([n for n in dir(o) if not n.startswith('__')])
print([n for n in dir(Obj) if not n.startswith('__')])
print('__class__' in dir(o), '__init__' in dir(o), '__dict__' in dir(o))
try:
    vars(42)
except TypeError as e:
    print('TypeError:', e)


class WithDir:
    def __dir__(self):
        return ['zeta', 'alpha']


print(dir(WithDir()))
import math
print('sqrt' in dir(math), 'pi' in vars(math))
print(dir() == sorted(globals()))
