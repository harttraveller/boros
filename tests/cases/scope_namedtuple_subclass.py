from collections import namedtuple


class Point(namedtuple('PointBase', 'x y')):
    __slots__ = ()

    def norm1(self):
        return abs(self.x) + abs(self.y)

    def __add__(self, other):
        return Point(self.x + other.x, self.y + other.y)


p = Point(3, -4)
print('1', p.x, p.y, p[0], p.norm1(), len(p), list(p), p[-1], p[:1], hash(p) == hash((3, -4)))
x, y = p
print('2', x, y, isinstance(p, tuple), p == (3, -4), Point._fields, (p + Point(1, 1)).norm1())
# comparisons between two instances of the subclass use tuple comparison
try:
    print('3', Point(1, 2) == Point(1, 2), Point(1, 2) != Point(1, 3), Point(1, 2) < Point(1, 3))
    print('3b', sorted([Point(2, 1), Point(1, 2)], key=lambda q: q.norm1()))
    print('3c', max(Point(2, 1), Point(1, 2)))
except TypeError as e:
    print('3 TypeError:', e)
# the repr uses the subclass name
print('4', repr(p), str(p), p + Point(1, 1))
# _replace / _make build instances of the subclass
r = p._replace(x=0)
print('5', type(r).__name__, r)
try:
    print('5b', r.norm1())
except AttributeError as e:
    print('5b AttributeError:', e)


class Plain(namedtuple('Plain', 'a b')):
    pass


try:
    print('6', Plain(1, 2) + Plain(3, 4))
except TypeError as e:
    print('6 TypeError:', e)
