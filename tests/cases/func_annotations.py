# Function annotations are evaluated at definition time and stored in
# __annotations__.
import functools


def plain(a, b=1):
    pass


print(plain.__annotations__)


def ann(x: int, y: 'str' = 'a', *args: float, z: bool = True, **kw: dict) -> list:
    pass


print(ann.__annotations__)
print(list(ann.__annotations__))

counter = []


def side(v):
    counter.append(v)
    return v


def evaluated(p: side('p'), q: side('q') = 0) -> side('ret'):
    pass


print(counter, evaluated.__annotations__)
lam = lambda a: a
print(lam.__annotations__)


class C:
    def m(self, v: int) -> None:
        pass


print(C.m.__annotations__, C().m.__annotations__)
plain.__annotations__ = {'a': 'set'}
print(plain.__annotations__)


@functools.wraps(ann)
def wrapper(*a):
    pass


print(wrapper.__annotations__)


@functools.singledispatch
def show(x):
    return 'object'


@show.register
def _(x: int):
    return 'int'


@show.register
def _(x: str):
    return 'str'


print(show(1), show('s'), show(1.5))
