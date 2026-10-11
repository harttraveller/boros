# inspect.signature() of interpreted functions, lambdas, bound methods,
# decorated functions and partials.
import functools
import inspect


def f(a, b=2, /, c=3, *args, d, e=5, **kw):
    pass


def g(x, y=[1]):
    pass


class K:
    def m(self, v, w=0):
        pass

    @classmethod
    def c(cls, z):
        pass

    @staticmethod
    def s(q, *, r=1):
        pass


def deco(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        return fn(*args, **kwargs)
    return wrapper


@deco
def decorated(alpha, beta=None):
    pass


print(inspect.signature(f))
print(inspect.signature(g), inspect.signature(lambda p, *q, **r: 0))
print(inspect.signature(K().m), inspect.signature(K.m), inspect.signature(K.c), inspect.signature(K.s))
print(inspect.signature(decorated), inspect.signature(functools.partial(g, 1)))
print(list(inspect.signature(f).parameters))
print([p.kind.name for p in inspect.signature(f).parameters.values()])
bound = inspect.signature(g).bind(1)
bound.apply_defaults()
print(bound.arguments)
try:
    inspect.signature(g).bind()
except TypeError as e:
    print('TypeError:', e)
