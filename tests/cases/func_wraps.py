# functools.wraps / update_wrapper: host code assigning attributes of
# interpreted functions and instances.
import functools


def deco(f):
    @functools.wraps(f)
    def w(*a, **k):
        return f(*a, **k)
    return w


@deco
def documented(x):
    "the doc"
    return x * 2


print(documented(4), documented.__name__, documented.__doc__, documented.__qualname__)
print(documented.__module__, documented.__wrapped__(5))


def with_args(prefix):
    def d(f):
        @functools.wraps(f)
        def w(*a):
            return prefix + str(f(*a))
        return w
    return d


class K:
    @with_args('>')
    def m(self, v):
        "method doc"
        return v


print(K().m(3), K.m.__name__, K.m.__qualname__, K.m.__doc__)


# update_wrapper onto an instance of a class-based decorator
class CountCalls:
    def __init__(self, f):
        functools.update_wrapper(self, f)
        self.n = 0

    def __call__(self, *a):
        self.n += 1
        return self.__wrapped__(*a)


@CountCalls
def sq(x):
    "squares"
    return x * x


print(sq(3), sq(4), sq.n, sq.__name__, sq.__doc__, sq.__qualname__)


# host setattr / delattr on an interpreted instance
class Bag:
    pass


b = Bag()
functools.update_wrapper(b, documented, assigned=('__name__',), updated=())
print(b.__name__, sorted(vars(b)), b.__wrapped__ is documented)
