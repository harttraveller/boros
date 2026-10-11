# Numeric conversion special methods: __index__ (slicing, range, hex,
# sequence indexing/repeat), __int__, __float__, __complex__, __round__,
# __abs__, __trunc__/__floor__/__ceil__ and math functions.
import math
import operator


class Idx:
    def __init__(self, v):
        self.v = v

    def __index__(self):
        return self.v


i1, i3 = Idx(1), Idx(3)
data = list(range(10))
print(data[i3], data[i1:i3], data[::i3], data[Idx(-2)], 'abcdef'[i1:Idx(4):Idx(2)], (1, 2, 3)[i1])
print(list(range(i3)), list(range(i1, Idx(7), Idx(2))), range(10)[i3], len(range(Idx(4))))
print(hex(Idx(255)), oct(Idx(8)), bin(Idx(5)), operator.index(Idx(7)), int(Idx(9)), float(Idx(2)))


def attempt(label, f):
    try:
        print(label, '->', f())
    except (TypeError, ValueError, OverflowError, IndexError) as e:
        print(label, '->', type(e).__name__ + ':', e)


attempt('[0] * Idx(3)', lambda: [0] * Idx(3))
attempt("Idx(2) * 'ab'", lambda: Idx(2) * 'ab')
attempt("b'x' * Idx(2)", lambda: b'x' * Idx(2))
attempt('(1,) * Idx(2)', lambda: (1,) * Idx(2))
attempt("'ab' * Idx(2)", lambda: 'ab' * Idx(2))
attempt('Idx(2) * [7]', lambda: Idx(2) * [7])
attempt('bytes(Idx(3))', lambda: bytes(Idx(3)))
attempt('bytearray(Idx(2))', lambda: bytearray(Idx(2)))
print(math.comb(Idx(5), Idx(2)), math.factorial(Idx(4)), round(2.567, Idx(1)))
print('%d|%x|%c' % (Idx(42), Idx(42), Idx(65)), chr(Idx(66)), [10, 20, 30].pop(Idx(1)))
print('abc'.center(Idx(7), '*'), [1, 2, 3, 4].index(3, Idx(1)), int('11', Idx(2)))
s = list('abcdef')
s[Idx(1):Idx(3)] = 'XY'
del s[Idx(0)]
print(s)


class BigIdx:
    def __index__(self):
        return 10 ** 30


print(data[BigIdx():], data[:BigIdx()])


class NoIdx:
    pass


class BadIdx:
    def __index__(self):
        return 'nope'


attempt('range(NoIdx())', lambda: range(NoIdx()))
attempt('hex(NoIdx())', lambda: hex(NoIdx()))
attempt('operator.index(NoIdx())', lambda: operator.index(NoIdx()))
attempt('[1] * NoIdx()', lambda: [1] * NoIdx())
attempt("NoIdx() * 'a'", lambda: NoIdx() * 'a')
attempt('hex(BadIdx())', lambda: hex(BadIdx()))
attempt('data[BadIdx()]', lambda: data[BadIdx()])
attempt('range(BadIdx())', lambda: range(BadIdx()))
attempt('data[Idx(99)]', lambda: data[Idx(99)])


class Num:
    def __init__(self, v):
        self.v = v

    def __int__(self):
        return int(self.v)

    def __float__(self):
        return float(self.v)

    def __complex__(self):
        return complex(self.v, 1)

    def __round__(self, n=None):
        return ('round', n)

    def __abs__(self):
        return ('abs', self.v)

    def __neg__(self):
        return Num(-self.v)

    def __trunc__(self):
        return ('trunc', self.v)

    def __floor__(self):
        return ('floor', self.v)

    def __ceil__(self):
        return ('ceil', self.v)


n = Num(2.75)
print(int(n), float(n), complex(n), round(n), round(n, 1), abs(n), (-n).v)
print(math.trunc(n), math.floor(n), math.ceil(n), math.sqrt(Num(16)), math.isclose(Num(1), 1.0))
print('%d %.2f %s' % (n, n, (-n).v), int(Num('7')))


class FloatOnly:
    def __float__(self):
        return 3.75


class IndexOnly:
    def __index__(self):
        return 4


fo = FloatOnly()
print(float(fo), math.sqrt(fo) > 1)
attempt('math.floor(FloatOnly())', lambda: math.floor(fo))
attempt('math.ceil(FloatOnly())', lambda: math.ceil(fo))
attempt('int(FloatOnly())', lambda: int(fo))
attempt('math.trunc(FloatOnly())', lambda: math.trunc(fo))
attempt('complex(FloatOnly())', lambda: complex(fo))
attempt('complex(IndexOnly())', lambda: complex(IndexOnly()))
attempt('round(FloatOnly())', lambda: round(fo))
attempt('float(IndexOnly())', lambda: float(IndexOnly()))
attempt('int(IndexOnly())', lambda: int(IndexOnly()))
attempt('math.floor(IndexOnly())', lambda: math.floor(IndexOnly()))
attempt('math.sqrt(IndexOnly())', lambda: math.sqrt(IndexOnly()))


class Bad:
    def __int__(self):
        return 'str'

    def __float__(self):
        return 1

    def __complex__(self):
        return 2.0


attempt('int(Bad())', lambda: int(Bad()))
attempt('float(Bad())', lambda: float(Bad()))
attempt('complex(Bad())', lambda: complex(Bad()))
attempt('int(NoIdx())', lambda: int(NoIdx()))
attempt('float(NoIdx())', lambda: float(NoIdx()))
attempt('complex(NoIdx())', lambda: complex(NoIdx()))
attempt('round(NoIdx())', lambda: round(NoIdx()))
attempt('round(NoIdx(), 2)', lambda: round(NoIdx(), 2))
attempt('abs(NoIdx())', lambda: abs(NoIdx()))
attempt('math.trunc(NoIdx())', lambda: math.trunc(NoIdx()))
attempt('math.floor(NoIdx())', lambda: math.floor(NoIdx()))
attempt('math.ceil(NoIdx())', lambda: math.ceil(NoIdx()))


class BadIdxInt:
    def __index__(self):
        return 'x'


attempt('int(BadIdxInt())', lambda: int(BadIdxInt()))
