# TypeError messages raised while binding arguments (one problem per call).


def check(label, fn, *args, **kwargs):
    try:
        result = fn(*args, **kwargs)
    except TypeError as e:
        print(label, '-> TypeError:', e)
    else:
        print(label, '->', result)


def f0():
    return 0


def f1(a):
    return a


def f2(a, b=2):
    return (a, b)


def f3(a, b, c):
    return 3


def po(a, b, /, c):
    return (a, b, c)


def ko(*, a, b=2):
    return (a, b)


def mixed(a, /, b, *, c):
    return (a, b, c)


def full(a, b, /, c=3, *args, d, e=5, **kw):
    return 'full'


check('f0 1 arg', f0, 1)
check('f0 2 args', f0, 1, 2)
check('f0 kw', f0, x=1)
check('f1 none', f1)
check('f1 2 args', f1, 1, 2)
check('f1 dup', f1, 1, a=2)
check('f2 none', f2)
check('f2 3 args', f2, 1, 2, 3)
check('f2 4 args', f2, 1, 2, 3, 4)
check('f3 none', f3)
check('f3 one', f3, 1)
check('f3 only c', f3, c=1)
check('f3 four', f3, 1, 2, 3, 4)
check('f3 dup a', f3, 1, b=2, c=3, a=5)
check('f3 unexpected', f3, 1, 2, 3, d=4)
check('po as kw', po, a=1, b=2, c=3)
check('po b as kw', po, 1, b=2, c=3)
check('po missing c', po, 1, 2)
check('ko none', ko)
check('ko positional', ko, 1)
check('ko positional and kw', ko, 1, a=2, b=3)
check('ko missing a', ko, b=1)
check('mixed too many', mixed, 1, 2, 3)
check('mixed too many with kw', mixed, 1, 2, 3, c=4)
check('mixed missing c', mixed, 1, 2)
check('mixed a by kw', mixed, a=1, b=2, c=3)
check('full missing b', full, 1)
check('full missing d', full, 1, 2)
check('full missing a b', full, d=3)
check('full ok', full, 1, 2, d=3, a=9)


def three_kwonly(*, x, y, z):
    pass


check('3 kwonly missing', three_kwonly)
check('2 kwonly missing', three_kwonly, y=1)


def many(a, b, c, d):
    pass


check('4 missing', many)


class A:
    def m(self, x):
        return x

    @staticmethod
    def s(x):
        return x

    @classmethod
    def c(cls, x):
        return x

    def __init__(self, v=0):
        self.v = v


a = A()
check('method missing', a.m)
check('method too many', a.m, 1, 2)
check('unbound missing', A.m, 1)
check('unbound none', A.m)
check('static missing', A.s)
check('classmethod too many', a.c, 1, 2)
check('method unexpected', a.m, y=1)
check('method self kw', a.m, self=1, x=2)
check('init too many', A, 1, 2)
check('init unexpected', A, w=1)
check('lambda too many', lambda: 0, 1)
check('lambda kwonly', lambda x, *, y: 0, 1)
check('lambda missing', lambda x, y: 0)


def outer():
    def inner(p):
        return p
    return inner


check('nested qualname', outer())


def gen(a, b):
    yield a


check('generator missing', gen, 1)
check('generator too many', gen, 1, 2, 3)

# **kwargs must have string keys
check('non-str key', lambda: f2(**{1: 2}))
check('posonly kw with **kw', lambda a, /, **k: (a, k), 1, a=2)
