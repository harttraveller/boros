# __hash__ / __eq__ interplay: unhashable classes, inherited hashes,
# instances as dict keys and set members, hash() result checks.


class Plain:
    pass


p1, p2 = Plain(), Plain()
print(hash(p1) == hash(p1), p1 == p1, p1 == p2, len({p1, p2, p1}))
d = {p1: 'one'}
print(d[p1], p2 in d)


class EqOnly:
    def __init__(self, v):
        self.v = v

    def __eq__(self, o):
        return isinstance(o, EqOnly) and self.v == o.v


print(EqOnly.__hash__)
print(EqOnly(1) == EqOnly(1))
for label, f in [('hash', lambda: hash(EqOnly(1))),
                 ('set', lambda: {EqOnly(1)}),
                 ('dict key', lambda: {EqOnly(1): 1}),
                 ('in set', lambda: EqOnly(1) in {1, 2}),
                 ('frozenset', lambda: frozenset([EqOnly(2)])),
                 ('dict.get', lambda: {}.get(EqOnly(1))),
                 ('set.add', lambda: set().add(EqOnly(3)))]:
    try:
        f()
        print(label, 'ok')
    except TypeError as e:
        print(label, 'TypeError:', e)

import collections.abc
print(isinstance(EqOnly(1), collections.abc.Hashable), isinstance(p1, collections.abc.Hashable))


class Key:
    def __init__(self, a, b):
        self.a = a
        self.b = b

    def __eq__(self, o):
        print('eq called')
        return isinstance(o, Key) and (self.a, self.b) == (o.a, o.b)

    def __hash__(self):
        return hash((self.a, self.b))

    def __repr__(self):
        return 'Key(%r, %r)' % (self.a, self.b)


k = Key(1, 2)
d = {k: 'v'}
print(d[k])               # identity: no __eq__ call
print(d[Key(1, 2)])       # equal hash -> __eq__ called
print(Key(1, 3) in d)
s = {Key(1, 2), Key(1, 2), Key(2, 1)}
print(len(s))
print(sorted(s, key=lambda x: (x.a, x.b)))


# subclass that defines __eq__ loses the inherited __hash__
class Base:
    def __hash__(self):
        return 42


class Sub(Base):
    def __eq__(self, o):
        return True


class Sub2(Base):
    pass


print(hash(Base()), hash(Sub2()))
print(Sub.__hash__)
try:
    hash(Sub())
except TypeError as e:
    print('TypeError:', e)


# explicitly restoring a hash
class Sub3(Sub):
    __hash__ = Base.__hash__


print(hash(Sub3()))


# explicit __hash__ = None
class NoHash:
    __hash__ = None


try:
    hash(NoHash())
except TypeError as e:
    print('TypeError:', e)
print(NoHash.__hash__)


# subclass of an unhashable class re-enabling hashing
class ReHash(NoHash):
    def __hash__(self):
        return 7


print(hash(ReHash()))


# hash() checks the return type
class BadHash:
    def __init__(self, r):
        self.r = r

    def __hash__(self):
        return self.r


for r in [10, -1, 2 ** 100, True, 'x', 1.5, None]:
    try:
        print(repr(r), '->', hash(BadHash(r)))
    except TypeError as e:
        print(repr(r), '-> TypeError:', e)


# __hash__ raising propagates out of dict operations
class Raiser:
    def __hash__(self):
        raise KeyError('no hashing')


try:
    {Raiser(): 1}
except KeyError as e:
    print('KeyError:', e)


# hash consistent with ==: int-like key finds an int entry
class IntLike:
    def __init__(self, v):
        self.v = v

    def __hash__(self):
        return hash(self.v)

    def __eq__(self, o):
        return self.v == o


d = {1: 'int one', 'a': 'str a'}
print(d[IntLike(1)], d.get(IntLike(2), 'missing'))
print(IntLike(1) in {1, 2, 3}, {IntLike(1): 'x'}.get(1))
