# A function's __dict__ holds only custom attributes; __name__, __qualname__,
# __doc__ and __module__ are not stored in it.
import functools


def f(a):
    "doc of f"
    return a


print(f.__dict__)
print(vars(f))
f.custom = 1
print(f.__dict__)
lam = lambda: 0
print(lam.__dict__)


def deco(fn):
    @functools.wraps(fn)
    def w(*a):
        return fn(*a)
    return w


wrapped = deco(f)
print(sorted(wrapped.__dict__))
f.__name__ = 'other'
print(f.__dict__)
g = lambda: 1
g.__dict__ = {'x': 1}
print(g.x, g.__dict__, g.__name__)
