# Host-level access to interpreted classes and instances, and object-model
# details: subscripting classes with host generic bases, dir() from host
# code, deleting __dict__, slotted-instance error messages, and `with` on a
# __slots__ class that is not a context manager.
import inspect
from typing import Generic, TypeVar

T = TypeVar('T')


class Box(Generic[T]):
    def __init__(self, v):
        self.v = v


class Names(list):
    pass


alias = Box[int]
print(alias, alias(3).v, Names[str], Box[int] == Box[int])


class Point:
    """A point."""
    dims = 2

    def norm(self):
        return 0


print([name for name, _ in inspect.getmembers(Point) if not name.startswith('__')])
print(inspect.getdoc(Point), inspect.getdoc(Point()))
p = Point()
p.x = 1
del p.__dict__
print(vars(p), hasattr(p, 'x'))


class Slotted:
    __slots__ = ('a',)
    kind = 'k'


s = Slotted()
for name in ('kind', 'zz', 'a'):
    try:
        delattr(s, name)
    except AttributeError as e:
        print('AttributeError:', e)
try:
    with Slotted():
        pass
except TypeError as e:
    print('TypeError:', e)
