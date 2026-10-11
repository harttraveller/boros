# Argument binding: defaults, *args, **kwargs, keyword-only, positional-only.


def plain(a, b, c):
    return (a, b, c)


print(plain(1, 2, 3), plain(1, c=3, b=2), plain(c=3, a=1, b=2), plain(*[1, 2], c=3), plain(**{'a': 1, 'b': 2, 'c': 3}))


def defaults(a, b=2, c=3):
    return (a, b, c)


print(defaults(1), defaults(1, 5), defaults(1, c=9), defaults(a=0, b=None), defaults(*(7, 8, 9)))


def star(a, *rest):
    return (a, rest, type(rest).__name__)


print(star(1), star(1, 2, 3), star(*range(4)), star(*'xy'))


def kwargs(a, **kw):
    return (a, kw)


print(kwargs(1), kwargs(1, x=2, y=3), kwargs(a=1, b=2), kwargs(**{'a': 0, 'z': 26}))
# keyword order is preserved
print(list(kwargs(0, z=1, y=2, x=3)[1]))


def kwonly(a, *, b, c=3):
    return (a, b, c)


print(kwonly(1, b=2), kwonly(1, c=0, b=2), kwonly(a=1, b=2))


def posonly(a, b, /, c, d=4):
    return (a, b, c, d)


print(posonly(1, 2, 3), posonly(1, 2, c=3), posonly(1, 2, 3, d=5), posonly(1, 2, d=5, c=6))


def everything(a, b=2, /, c=3, *args, d, e=5, **kw):
    return (a, b, c, args, d, e, kw)


print(everything(1, d=4))
print(everything(1, 2, 3, 4, 5, d=6, e=7, f=8))
print(everything(1, c=30, d=40, x=1))


# positional-only names may be reused as **kwargs keys
def po_kw(a, /, **kw):
    return (a, kw)


print(po_kw(1, a=2), po_kw(1, **{'a': 3, 'b': 4}))


# *args and **kwargs are fresh objects
def mutate(*args, **kw):
    kw['added'] = True
    return args, kw


d = {'x': 1}
r = mutate(**d)
print(r, d)
lst = [1, 2]
r = mutate(*lst)
print(r, lst, r[0] is lst)


# forwarding
def target(a, b, /, c, *, d):
    return a + b + c + d


def forward(*args, **kwargs):
    return target(*args, **kwargs)


print(forward(1, 2, 3, d=4), forward(1, 2, c=3, d=4))


# multiple star expansions
def collect(*a, **k):
    return a, k


print(collect(*[1, 2], 3, *(4,), x=1, **{'y': 2}, z=3, **{'w': 4}))
print(collect(*{}, **{}))


# defaults referencing earlier names are evaluated at definition time
base = 10


def uses_base(x=base * 2, y=[base]):
    return x, y


base = 0
print(uses_base())


# methods: self binding, keyword self
class K:
    def m(self, a, b=1, *rest, key='k', **kw):
        return (type(self).__name__, a, b, rest, key, kw)

    @staticmethod
    def s(a, b=2):
        return (a, b)

    @classmethod
    def c(cls, *args, **kw):
        return (cls.__name__, args, kw)


k = K()
print(k.m(1), k.m(1, 2, 3, key='q', z=0), K.m(k, a=5), K.s(1), k.s(b=3, a=4), K.c(1, x=2), k.c())


# generator functions bind arguments at call time
def gen(a, b=2, *rest, k=1, **kw):
    yield (a, b, rest, k, kw)


print(list(gen(1)), list(gen(1, 2, 3, k=4, z=5)))

# lambdas take every parameter kind
lam = lambda a, b=2, /, c=3, *args, d=4, **kw: (a, b, c, args, d, kw)
print(lam(1), lam(1, 2, 3, 4, d=5, e=6))
