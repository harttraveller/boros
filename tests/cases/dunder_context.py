# Context managers: __enter__/__exit__ call order, return values,
# exception suppression, exit arguments, and protocol errors.


class CM:
    def __init__(self, name, suppress=False):
        self.name = name
        self.suppress = suppress

    def __enter__(self):
        print('enter', self.name)
        return self.name.upper()

    def __exit__(self, et, ev, tb):
        print('exit', self.name, et.__name__ if et else None, repr(ev) if ev else None, tb is not None)
        return self.suppress


with CM('a') as v:
    print('body', v)

with CM('outer') as o, CM('inner') as i:
    print('body', o, i)

with CM('s', suppress=True):
    raise ValueError('suppressed')
print('after suppressed')

try:
    with CM('n'):
        raise KeyError('propagates')
except KeyError as e:
    print('caught', e)

try:
    with CM('o1', suppress=True), CM('o2'):
        1 / 0
    print('o1 suppressed what o2 let through')
except ZeroDivisionError:
    print('not reached')


# __exit__ return value truthiness is used
class Truthy:
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return 'yes'


with Truthy():
    raise RuntimeError
print('truthy suppressed')


# exiting through return/break/continue calls __exit__ with Nones
def f():
    for n in range(3):
        with CM('loop%d' % n):
            if n == 0:
                continue
            if n == 1:
                break
    with CM('ret'):
        return 'returned'


print(f())


# exception raised in __exit__ replaces the original
class BadExit:
    def __enter__(self):
        return self

    def __exit__(self, *a):
        raise TypeError('from exit')


try:
    with BadExit():
        raise ValueError('original')
except TypeError as e:
    print('TypeError', e, type(e.__context__).__name__)


# exception in __enter__: __exit__ is not called
class BadEnter:
    def __enter__(self):
        raise LookupError('enter failed')

    def __exit__(self, *a):
        print('exit should not run')


try:
    with BadEnter():
        print('no body')
except LookupError as e:
    print('LookupError', e)


# target unpacking
class Pair:
    def __enter__(self):
        return (1, [2, 3])

    def __exit__(self, *a):
        return False


with Pair() as (a, [b, c]):
    print(a, b, c)


# methods found via the class, inherited, and via staticmethod
class Base:
    def __enter__(self):
        return 'base enter'

    def __exit__(self, *a):
        print('base exit')


class Child(Base):
    pass


with Child() as x:
    print(x)


# protocol errors
class NoCM:
    pass


class EnterOnly:
    def __enter__(self):
        return self


class ExitOnly:
    def __exit__(self, *a):
        pass


for cls in (NoCM, EnterOnly, ExitOnly):
    try:
        with cls():
            print('body should not run')
    except TypeError as e:
        print('TypeError:', e)

# instance attributes are not used
n = NoCM()
n.__enter__ = lambda: 1
n.__exit__ = lambda *a: None
try:
    with n:
        pass
except TypeError as e:
    print('TypeError:', e)


# contextlib helpers with instances
import contextlib

with contextlib.ExitStack() as stack:
    print(stack.enter_context(CM('stacked')))
    stack.callback(print, 'callback ran')
print('stack done')

with contextlib.suppress(ZeroDivisionError):
    with CM('in suppress'):
        1 / 0
print('suppress done')


class Closer:
    def close(self):
        print('closed')


with contextlib.closing(Closer()) as cl:
    print(type(cl).__name__)

try:
    with contextlib.ExitStack() as stack:
        stack.enter_context(NoCM())
except TypeError as e:
    print('TypeError:', e)
