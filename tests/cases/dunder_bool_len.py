# Truthiness via __bool__ and __len__, and len() result checking.


class B:
    def __init__(self, r):
        self.r = r

    def __bool__(self):
        print('__bool__ called')
        return self.r


class L:
    def __init__(self, n):
        self.n = n

    def __len__(self):
        return self.n


class Both:
    def __bool__(self):
        return False

    def __len__(self):
        print('len should not be used')
        return 5


class Neither:
    pass


print(bool(B(True)), bool(B(False)), not B(False))
if B(True):
    print('if ok')
print('and:', type(B(False) and 'x').__name__, 'or:', B(False) or 'y')
print(bool(L(0)), bool(L(3)), bool(Both()), bool(Neither()))
print([x for x in [L(0), L(1), L(2), L(0)] if x].__len__())
print(len(L(7)), len(L(0)))
while L(0):
    print('never')
print('ternary', 'yes' if L(2) else 'no', 'yes' if L(0) else 'no')
print(any([L(0), L(0)]), all([L(1), L(2)]), list(filter(None, [L(0), L(4)]))[0].n)
assert L(1), 'assert uses truth'
print((L(1) and L(0) and 1).n, (L(0) or L(5)).n)


def check_bool(label, obj):
    try:
        print(label, '->', bool(obj))
    except (TypeError, ValueError, OverflowError) as e:
        print(label, '->', type(e).__name__ + ':', e)


def check_len(label, obj):
    try:
        print(label, '->', len(obj))
    except (TypeError, ValueError, OverflowError) as e:
        print(label, '->', type(e).__name__ + ':', e)


check_bool('__bool__ returns 1', B(1))
check_bool('__bool__ returns None', B(None))
check_bool('__bool__ returns []', B([]))
check_len('len returns -1', L(-1))
check_len('len returns 2.0', L(2.0))
check_len("len returns '3'", L('3'))
check_len('len returns True', L(True))
check_len('len returns 2**70', L(2 ** 70))
check_len('no __len__', Neither())
check_len('__bool__ only', B(True))
check_bool('bool len -1', L(-1))
check_bool("bool len '3'", L('3'))
check_bool('bool len 2.0', L(2.0))
check_bool('bool len 2**70', L(2 ** 70))
check_bool('bool len True', L(True))

# truth testing of the result inside if/while/not raises the same errors
try:
    if B(2):
        pass
except TypeError as e:
    print('if: TypeError:', e)
try:
    print(not L(-5))
except ValueError as e:
    print('not: ValueError:', e)


# __bool__ = None makes truth testing fail
class NoBool:
    __bool__ = None


try:
    bool(NoBool())
except TypeError as e:
    print('TypeError:', e)


# __len__ = None
class NoLen:
    __len__ = None


try:
    len(NoLen())
except TypeError as e:
    print('TypeError:', e)
print(bool(NoLen()) if False else 'skip')


# __bool__ inherited, overridden in subclass
class T(B):
    def __bool__(self):
        return not B.__bool__(self)


print(bool(T(True)), bool(T(False)))

# operator.truth / operator.not_
import operator
print(operator.truth(L(0)), operator.not_(L(0)), operator.length_hint(L(4)))
