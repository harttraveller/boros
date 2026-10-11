# Errors raised by host code about interpreted instances must name the
# interpreted class (CPython names the object's type).
import math


class NoIdx:
    pass


class Idx:
    def __init__(self, v):
        self.v = v

    def __index__(self):
        return self.v


class BigIdx:
    def __index__(self):
        return 10 ** 30


def attempt(label, f):
    try:
        print(label, '->', f())
    except (TypeError, ValueError, OverflowError) as e:
        print(label, '->', type(e).__name__ + ':', e)


data = [1, 2, 3]
attempt('data[NoIdx()]', lambda: data[NoIdx()])
attempt("'abc'[NoIdx()]", lambda: 'abc'[NoIdx()])
attempt('(1,)[NoIdx()]', lambda: (1,)[NoIdx()])
attempt('data[NoIdx():]', lambda: data[NoIdx():])
attempt('[0] * BigIdx()', lambda: [0] * BigIdx())
attempt('pow(2, Idx(10), 1000)', lambda: pow(2, Idx(10), 1000))
attempt('pow(2, 10, Idx(7))', lambda: pow(2, 10, Idx(7)))
attempt('math.sqrt(NoIdx())', lambda: math.sqrt(NoIdx()))
attempt('math.log(NoIdx())', lambda: math.log(NoIdx()))
attempt("'%d' % NoIdx()", lambda: '%d' % NoIdx())
attempt("'%x' % NoIdx()", lambda: '%x' % NoIdx())
attempt("'%f' % NoIdx()", lambda: '%f' % NoIdx())
attempt("'-'.join([NoIdx()])", lambda: '-'.join([NoIdx()]))
attempt("'abc'.startswith(NoIdx())", lambda: 'abc'.startswith(NoIdx()))
attempt("'a' in [NoIdx()] ok", lambda: 'a' in [NoIdx()])
attempt('int.__add__(1, NoIdx())', lambda: int.__add__(1, NoIdx()))
attempt('sorted([NoIdx(), 1])', lambda: sorted([NoIdx(), 1]))
