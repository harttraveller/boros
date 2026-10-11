# Rich comparisons: reflection, NotImplemented fallbacks, default ==/!=
# behaviour, chained comparisons and error messages.


class N:
    def __init__(self, v):
        self.v = v

    def __repr__(self):
        return 'N(%d)' % self.v

    def __lt__(self, o):
        return self.v < (o.v if isinstance(o, N) else o)

    def __le__(self, o):
        return self.v <= (o.v if isinstance(o, N) else o)

    def __eq__(self, o):
        if isinstance(o, N):
            return self.v == o.v
        return NotImplemented


a, b, c = N(1), N(2), N(3)
print(a < b, b < a, a <= a, a == N(1), a != N(1), a != b)
print(b > a, a > b, b >= a, a >= b)   # reflected __lt__/__le__
print(a < 5, 5 > a, 2 >= a, 0 > a)    # reflected with an int on the left
print(a < b < c, a < c < b, a == N(1) == N(1))
print(a == 1, 1 == a, a != 1, 1 != a)  # NotImplemented both ways -> identity
print(a == a, [a] == [N(1)], (a, b) == (N(1), N(2)), [a] < [b])
print(N(1) in [N(0), N(1)], N(5) in [N(0), N(1)])
print(sorted([c, a, b]), max([a, c, b]), min(b, a, c))


# result values are passed through unchanged (no bool conversion)
class Weird:
    def __eq__(self, o):
        return 'eq-result'

    def __lt__(self, o):
        return [1, 2]

    def __ne__(self, o):
        return 0


w = Weird()
print(w == 1, 1 == w, w < 3, 3 > w, w != 1, 1 != w)


# default __ne__ inverts __eq__ unless it is NotImplemented
class OnlyEq:
    def __init__(self, k):
        self.k = k

    def __eq__(self, o):
        print('OnlyEq.__eq__')
        return isinstance(o, OnlyEq) and o.k == self.k


print(OnlyEq(1) != OnlyEq(1), OnlyEq(1) != OnlyEq(2))


class EqList:
    def __eq__(self, o):
        return [0]   # falsy, non-bool


print(EqList() != 5)


# order of calls: left first, then reflected
class Log:
    def __init__(self, name):
        self.name = name

    def __lt__(self, o):
        print(self.name, '__lt__', o.name)
        return NotImplemented

    def __gt__(self, o):
        print(self.name, '__gt__', o.name)
        return NotImplemented

    def __eq__(self, o):
        print(self.name, '__eq__', o.name)
        return NotImplemented


x, y = Log('x'), Log('y')
try:
    x < y
except TypeError as e:
    print('TypeError:', e)
print(x == y)
print(x != y)


# comparisons with a subclass on the right: its reflected method is tried
# first (even when it is inherited, unlike binary operators)
class LogSub(Log):
    pass


class LogSub2(Log):
    def __gt__(self, o):
        print(self.name, 'LogSub2.__gt__', o.name)
        return 'sub2'


try:
    x < LogSub('s')
except TypeError as e:
    print('TypeError:', e)
print(x < LogSub2('s2'))
print(x == LogSub('s'))


# error messages
class P:
    pass


tests = [
    ('P() < P()', lambda: P() < P()),
    ('P() <= 1', lambda: P() <= 1),
    ('P() > None', lambda: P() > None),
    ('[P()] < [P()]', lambda: [P()] < [P()]),
    ('(1, P()) < (1, P())', lambda: (1, P()) < (1, P())),
    ('sorted([P(), P()])', lambda: sorted([P(), P()])),
    ('max(P(), P())', lambda: max(P(), P())),
    ('min([P(), P()])', lambda: min([P(), P()])),
    ('N(1) < "a"', lambda: N(1) < 'a'),
    ('P() == P()', lambda: P() == P()),
    ('P() != 1', lambda: P() != 1),
]
for label, f in tests:
    try:
        print(label, '->', f())
    except TypeError as e:
        print(label, '-> TypeError:', e)


# __eq__ / __lt__ raising propagates
class Boom:
    def __eq__(self, o):
        raise ValueError('boom eq')

    __hash__ = object.__hash__


try:
    Boom() == 1
except ValueError as e:
    print('ValueError:', e)
try:
    print(Boom() in [1, 2])
except ValueError as e:
    print('ValueError:', e)
bm = Boom()
print(bm in [bm])   # identity short-circuit, __eq__ not called
