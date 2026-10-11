# Error messages for comparisons and augmented assignments where a host
# value is the left operand and an interpreted instance (without the needed
# method) is the right operand: the message names the operator as written
# and the operands in source order.


class P:
    pass


class Ver:
    def __init__(self, v):
        self.v = v

    def __lt__(self, o):
        if not isinstance(o, Ver):
            return NotImplemented
        return self.v < o.v


def attempt(label, f):
    try:
        print(label, '->', f())
    except TypeError as e:
        print(label, '-> TypeError:', e)


attempt('1 < P()', lambda: 1 < P())
attempt('1.5 >= P()', lambda: 1.5 >= P())
attempt("'s' > P()", lambda: 's' > P())
attempt('None < P()', lambda: None < P())
attempt('[1] <= P()', lambda: [1] <= P())
attempt('1 < Ver(2)', lambda: 1 < Ver(2))
attempt('sorted([Ver(1), 3])', lambda: sorted([Ver(1), 3]))
attempt('max(1, P())', lambda: max(1, P()))
attempt('min([P(), 2])', lambda: min([P(), 2]))


def isub_int():
    i = 1
    i -= P()
    return i


def ior_int():
    p = 3
    p |= P()
    return p


def ipow_float():
    f = 2.0
    f **= P()
    return f


def iadd_attr():
    class Box:
        pass
    b = Box()
    b.v = 1
    b.v += P()
    return b.v


def imul_item():
    d = {'k': 2}
    d['k'] *= P()
    return d


attempt('i -= P()', isub_int)
attempt('3 |= P()', ior_int)
attempt('2.0 **= P()', ipow_float)
attempt('b.v += P()', iadd_attr)
attempt("d['k'] *= P()", imul_item)
