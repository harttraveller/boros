# Special-method fallbacks and edge cases: copying exceptions and host-type
# subclasses, special methods set to None, dict subclasses with __missing__,
# operators and conversions on instances of builtin subclasses, sequence
# fallbacks for host sequences, and match statements inside generators.
import copy
import math
import operator
from collections import Counter, defaultdict


def show(label, f):
    try:
        print(label, '->', f())
    except Exception as e:
        print(label, '->', type(e).__name__ + ':', e)


class MyErr(ValueError):
    pass


e = MyErr('x')
c = copy.copy(e)
show('copy exc', lambda: (type(c).__name__, c.args, c is e))
try:
    raise c
except MyErr as caught:
    print('caught copy', caught is c, caught.args)
d = copy.deepcopy(e)
try:
    raise d
except MyErr as caught:
    print('caught deepcopy', caught is d, caught.args)


class EqNone:
    __eq__ = None
    __hash__ = object.__hash__


show('eq None', lambda: EqNone() == 1)


class KeyErrItems:
    def __getitem__(self, k):
        raise KeyError(k)


show('KeyError from __getitem__', lambda: KeyErrItems()['a'])


class OwnGetitem(dict):
    def __getitem__(self, k):
        raise KeyError('own ' + k)

    def __missing__(self, k):
        return 'missing'


show('own __getitem__ wins', lambda: OwnGetitem(a=1)['a'])


class DD(defaultdict):
    pass


show('defaultdict subclass', lambda: DD(int)['x'])


class CC(Counter):
    pass


cc = CC('aab')
cc['z'] += 1
show('Counter subclass', lambda: sorted(cc.items()))


class ML(list):
    pass


class MS(str):
    pass


class MI(int):
    pass


class MF(float):
    pass


class FS(frozenset):
    pass


class MB(bytes):
    pass


class MC(complex):
    pass


show('ML == list', lambda: (ML([1]) == [1], [1] == ML([1]), ML([1]) != [2]))
show('sorted MS', lambda: sorted([MS('b'), MS('a'), 'c']))
show('max MS', lambda: max([MS('b'), MS('a')]))
show('FS | FS', lambda: sorted(FS({1}) | FS({2})))
show('FS & set', lambda: sorted(FS({1, 2}) & {2}))
show('bytes MB', lambda: bytes(MB(b'xy')))
show('complex MC', lambda: complex(MC(1 + 2j)))
show('floor MF', lambda: (math.floor(MF(2.5)), math.ceil(MF(2.5)), round(MF(2.5))))
show('int MS', lambda: int(MS('12')) + 1)
show('MS % x', lambda: MS('a %s') % 'x')
show('MS % (MS,)', lambda: MS('a %s') % (MS('x'),))
show('%s % MS', lambda: '%s!' % MS('x'))
show('dict MS key', lambda: {MS('a'): 1}['a'])
show('MS key in dict', lambda: MS('a') in {'a': 1})
show('reversed ML', lambda: list(reversed(ML([1, 2]))))
show('iter ML', lambda: type(iter(ML([1]))).__name__)
show('MI ops', lambda: (MI(5) // 2, 2 ** MI(3), -MI(3), abs(MI(-3)), ~MI(1), MI(3) & 1, divmod(MI(7), 2)))
show('MF ops', lambda: (MF(1.5) + MF(2.5), MF(1.5) < 2, 3 - MF(0.5)))
show('MI in range', lambda: MI(3) in range(5))
show('list index MI', lambda: [1, 2, 3][MI(1)])


class LenTrue:
    def __len__(self):
        return True


show('bool len True', lambda: bool(LenTrue()))


class ReprSub:
    def __repr__(self):
        return MS('rep')


show('str ReprSub', lambda: (str(ReprSub()), repr(ReprSub()), f'{ReprSub()}', '%s' % ReprSub()))


class NoState:
    def __init__(self):
        self.a = 1

    def __getstate__(self):
        return None


show('copy __getstate__ None', lambda: vars(copy.copy(NoState())))


class Box:
    def __init__(self, v):
        self.v = v

    def __eq__(self, o):
        return isinstance(o, Box) and o.v == self.v

    def __hash__(self):
        return hash(self.v)


show('Box in list', lambda: (Box(1) in [Box(2), Box(1)], [Box(1)].index(Box(1))))


def gen(v):
    match v:
        case [a, b] if a > 0:
            yield a + b
        case {'k': k}:
            yield k
        case _:
            yield 'other'


show('match in generator', lambda: (list(gen([1, 2])), list(gen([0, 2])), list(gen({'k': 3}))))
show('star tuple', lambda: (*ML([1, 2]), *'ab'))
show('star set', lambda: {*None})


class It:
    def __init__(self):
        self.i = 0

    def __iter__(self):
        return self

    def __next__(self):
        self.i += 1
        if self.i > 3:
            raise StopIteration
        return self.i


class BadIter:
    def __iter__(self):
        raise TypeError('inner')


class Seq:
    def __getitem__(self, i):
        if i > 2:
            raise IndexError
        return i


class V:
    def __add__(self, o):
        return 'V+'

    def __radd__(self, o):
        return '+V'

    def __iadd__(self, o):
        return None


show('list It', lambda: list(It()))
show('in BadIter', lambda: 1 in BadIter())
show('list BadIter', lambda: list(BadIter()))
show('in Seq', lambda: (1 in Seq(), 5 in Seq()))
show('reversed Seq', lambda: list(reversed(Seq())))
show('V ops', lambda: (V() + 1, 1 + V(), [1] + V(), 'a' + V()))


def iadd_none():
    v = V()
    v += 1
    return v


def tuple_iadd():
    t = (1,)
    t += It()
    return t


def list_iadd():
    t = [1]
    t += It()
    return t


show('__iadd__ returning None', iadd_none)
show('tuple += It', tuple_iadd)
show('list += It', list_iadd)
show("'ab' * V", lambda: 'ab' * V())
show("V * 'ab'", lambda: V() * 'ab')


class Plain:
    pass


class Len0:
    def __len__(self):
        return 0


show('bool plain', lambda: (bool(Plain()), not Plain()))
show('bool Len0', lambda: (bool(Len0()), len(Len0())))
show('length_hint', lambda: (operator.length_hint(It()), operator.length_hint(Len0(), 7)))


class Cmp:
    def __init__(self, v):
        self.v = v

    def __lt__(self, o):
        return self.v < o.v


class SubCmp(Cmp):
    def __gt__(self, o):
        return 'SubCmp.gt'


show('sorted Cmp', lambda: [x.v for x in sorted([Cmp(3), Cmp(1), Cmp(2)])])
show('Cmp >', lambda: Cmp(3) > Cmp(1))
show('Cmp ==', lambda: (Cmp(1) == Cmp(1), Cmp(1) != Cmp(1)))
show('Cmp < SubCmp', lambda: Cmp(1) < SubCmp(2))
show('SubCmp < Cmp', lambda: SubCmp(1) < Cmp(2))


class BigHash:
    def __hash__(self):
        return 2 ** 70


show('big hash', lambda: hash(BigHash()) == hash(2 ** 70))


class Fmt:
    def __format__(self, spec):
        return 'F' + spec


class StrInt(int):
    def __str__(self):
        return 'SI'

    def __repr__(self):
        return 'SIr'


show('format', lambda: (f'{Fmt()}', f'{Fmt():x}', format(Fmt(), 'y')))
show('StrInt format', lambda: (f'{StrInt(5)}', f'{StrInt(5):03}', f'{StrInt(5)!r}', str(StrInt(5)),
                               '%s %d' % (StrInt(5), StrInt(5))))
show('MS format', lambda: (f'{MS("ab")}', f'{MS("ab"):>4}', format(MS('x'))))
show('next plain', lambda: next(Plain()))
show('iter plain', lambda: iter(Plain()))
show('complex plain', lambda: complex(Plain()))
show('bytes It', lambda: bytes(It()))
show('bytes plain', lambda: bytes(Plain()))
show('floor plain', lambda: math.floor(Plain()))
show('trunc plain', lambda: math.trunc(Plain()))


class FloatOnly:
    def __float__(self):
        return 2.5


show('FloatOnly', lambda: (math.floor(FloatOnly()), math.ceil(FloatOnly()), complex(FloatOnly()),
                           float(FloatOnly()), math.sqrt(FloatOnly())))
