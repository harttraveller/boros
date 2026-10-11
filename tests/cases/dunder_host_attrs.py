# Host library code reading and writing attributes of interpreted
# instances: operator.attrgetter, str.format field access, functools.wraps
# and update_wrapper with callable instances.
import functools
import operator


def show(label, f):
    try:
        print(label, '->', f())
    except Exception as e:
        print(label, '->', type(e).__name__ + ':', e)


class Rec:
    """Rec docstring."""

    def __init__(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)

    def __repr__(self):
        return 'Rec(%s)' % ', '.join('%s=%r' % kv for kv in sorted(vars(self).items()))


r = Rec(name='n', x=10)
show('attrgetter name,x', lambda: operator.attrgetter('name', 'x')(r))
show('sorted by attrgetter', lambda: sorted([Rec(k=3), Rec(k=1), Rec(k=2)], key=operator.attrgetter('k')))
show('format name-x', lambda: '{0.name}-{0.x}'.format(r))
show('attrgetter __doc__', lambda: operator.attrgetter('__doc__')(r))
show('format __module__', lambda: '{0.__module__}'.format(r))
show('methodcaller __repr__', lambda: operator.methodcaller('__repr__')(r))


# host setattr on an instance: functools.update_wrapper
class Wrapper:
    def __init__(self, f):
        functools.update_wrapper(self, f)

    def __call__(self, *a):
        return self.__wrapped__(*a)


def target(a, b):
    """Target doc."""
    return a + b


def use_wrapper():
    w = Wrapper(target)
    return w(1, 2), w.__name__, w.__doc__, w.__wrapped__ is target, w.__qualname__


show('update_wrapper(instance, f)', use_wrapper)


def deco(f):
    @functools.wraps(f)
    def inner(*a):
        return ('wrapped', f(*a))
    return inner


class CallMe:
    """CallMe doc."""

    def __call__(self, v):
        return v * 3


def use_wraps():
    wrapped = deco(CallMe())
    return wrapped(4), wrapped.__doc__, wrapped.__module__


show('wraps(instance)', use_wraps)


# attrgetter falls back to __getattr__ / properties
class Dyn:
    @property
    def prop(self):
        return 'property value'

    def __getattr__(self, name):
        return 'dyn:' + name


class Bag:
    pass


show('attrgetter prop/__getattr__', lambda: operator.attrgetter('prop', 'whatever')(Dyn()))
show('format prop/__getattr__', lambda: '{0.prop} {0.zzz}'.format(Dyn()))
show('attrgetter missing', lambda: operator.attrgetter('missing')(Bag()))


# interpreted functions are descriptors for host classes too
import string


def shout(self, suffix='!'):
    return self.template.upper() + suffix


string.Template.shout = shout
show('function as method of a host class', lambda: string.Template('ab').shout())
show('function.__get__', lambda: shout.__get__(string.Template('cd'))('?'))
show('function.__get__(None, cls)', lambda: shout.__get__(None, string.Template) is shout)
