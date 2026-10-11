# Ordering instances with host algorithms: sorted/list.sort/min/max,
# heapq, bisect, functools.total_ordering and cmp_to_key.
import bisect
import functools
import heapq
import operator


class Ver:
    def __init__(self, s):
        self.parts = tuple(int(p) for p in s.split('.'))
        self.s = s

    def __lt__(self, o):
        return self.parts < o.parts

    def __eq__(self, o):
        return isinstance(o, Ver) and self.parts == o.parts

    __hash__ = None

    def __repr__(self):
        return 'V' + self.s


vs = [Ver(s) for s in ['1.10', '1.2', '1.2.1', '0.9', '1.2']]
print(sorted(vs))
print(sorted(vs, reverse=True))
print(min(vs), max(vs), min(vs, key=lambda v: -len(v.s)), max(vs, key=operator.attrgetter('s')))
print(max([], default='empty'), min(vs[:1]), max(Ver('2'), Ver('10')))
copy = list(vs)
copy.sort()
print(copy, copy[1] is vs[1], copy[2] is vs[4])   # stable
copy.sort(key=lambda v: v.parts[-1])
print(copy)

h = []
for v in vs:
    heapq.heappush(h, v)
print([heapq.heappop(h) for _ in range(len(h))])
print(heapq.nsmallest(2, vs), heapq.nlargest(2, vs))
print(heapq.nsmallest(2, vs, key=lambda v: v.s), list(heapq.merge([Ver('1'), Ver('3')], [Ver('2')])))

srt = sorted(vs)
print(bisect.bisect_left(srt, Ver('1.2')), bisect.bisect_right(srt, Ver('1.2')), bisect.bisect(srt, Ver('5')))
bisect.insort(srt, Ver('1.3'))
print(srt)
print(bisect.bisect_left(srt, 2, key=lambda v: v.parts[0]))
bisect.insort(srt, Ver('0.1'), key=lambda v: v.parts)
print(srt)


# tuples with instances as tie breakers
pq = [(2, Ver('9')), (1, Ver('5')), (2, Ver('3'))]
heapq.heapify(pq)
print([heapq.heappop(pq) for _ in range(3)])


# only __gt__ defined: sort uses __lt__, reflected to __gt__
class G:
    def __init__(self, v):
        self.v = v

    def __gt__(self, o):
        return self.v > o.v

    def __repr__(self):
        return 'G%d' % self.v


print(sorted([G(3), G(1), G(2)]), min(G(5), G(4)), max([G(1), G(7)]))


class T:
    def __init__(self, v):
        self.v = v

    def __eq__(self, o):
        return self.v == o.v

    def __lt__(self, o):
        return self.v < o.v

    def __repr__(self):
        return 'T%d' % self.v


class TG:
    def __init__(self, v):
        self.v = v

    def __eq__(self, o):
        return self.v == o.v

    def __gt__(self, o):
        if not isinstance(o, TG):
            return NotImplemented
        return self.v > o.v


def use_total_ordering():
    functools.total_ordering(T)
    a, b = T(1), T(2)
    return a < b, a <= b, a > b, a >= b, b >= a, a <= T(1), a >= T(1), sorted([T(3), T(1), T(2)], reverse=True)


def use_total_ordering_gt():
    functools.total_ordering(TG)
    try:
        TG(1) <= 5
    except TypeError as e:
        print('TypeError:', e)
    return TG(1) < TG(2), TG(1) <= TG(1), TG(3) >= TG(4)


for f in (use_total_ordering, use_total_ordering_gt):
    try:
        print(f.__name__, '->', f())
    except Exception as e:
        print(f.__name__, '->', type(e).__name__ + ':', e)


class NoOrder:
    pass


try:
    functools.total_ordering(NoOrder)
except ValueError as e:
    print('ValueError:', e)


def cmp(x, y):
    return (x.v > y.v) - (x.v < y.v)


print([t.v for t in sorted([T(5), T(2), T(9)], key=functools.cmp_to_key(cmp))])


# errors
class P:
    pass


for label, f in [('sorted P', lambda: sorted([P(), P()])),
                 ('min P', lambda: min(P(), P())),
                 ('max P', lambda: max([P(), P()])),
                 ('heapify P', lambda: heapq.heapify([P(), P(), P()])),
                 ('bisect P', lambda: bisect.bisect([P()], P())),
                 ('sorted mixed', lambda: sorted([3, Ver('1')])),
                 ('sorted key error', lambda: sorted([1, 2], key=lambda x: P()))]:
    try:
        print(label, '->', f())
    except (TypeError, AttributeError) as e:
        print(label, '->', type(e).__name__ + ':', e)


# a __lt__ that raises inside list.sort propagates
class Boom:
    def __lt__(self, o):
        raise ValueError('cannot compare')


try:
    sorted([Boom(), Boom()])
except ValueError as e:
    print('ValueError:', e)
