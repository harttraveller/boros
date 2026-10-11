# Host builtins consuming user-defined iterables, iterators, numbers and
# containers: sum/any/all/zip/enumerate/map/filter/min/max/sorted/dict/set,
# str.join, and the errors for objects that lack the needed methods.


class Rng:
    def __init__(self, n):
        self.n = n

    def __iter__(self):
        i = 0
        while i < self.n:
            yield i
            i += 1


class It:
    """An explicit iterator class."""

    def __init__(self, items):
        self.items = list(items)

    def __iter__(self):
        return self

    def __next__(self):
        if not self.items:
            raise StopIteration
        return self.items.pop(0)


print(sum(Rng(5)), sum(Rng(3), 10), sum(It([1.5, 2.5])), any(Rng(2)), all(Rng(3)), all(Rng(0)))
print(list(zip(Rng(3), It('abc'), Rng(10))), list(enumerate(It('xy'), 1)))
print(list(map(lambda a, b: a * b, Rng(4), It([10, 20, 30]))), list(filter(None, Rng(4))))
print(min(Rng(4)), max(It([3, 9, 2])), sorted(It([3, 1, 2])), list(reversed(list(Rng(3)))))
print(dict(zip(It('ab'), Rng(2))), set(Rng(3)), frozenset(It([1, 1])), tuple(Rng(2)))
print(dict(It([('k', 'v'), ['k2', 'v2']])), '-'.join(It(['a', 'b'])), bytearray(It([67])))
try:
    print(bytes(It([65, 66])))
except TypeError as ex:
    print('bytes(It) TypeError:', ex)
print(list(map(str, Rng(3))), [*Rng(2), *It([7])], {**dict(zip(Rng(2), It('pq')))})
print(list(zip(*It([(1, 2), (3, 4)]))), max(Rng(3), key=lambda v: -v), next(iter(Rng(5))))
import itertools
print(list(itertools.chain(Rng(2), It([9]))), list(itertools.islice(Rng(100), 2, 5)))
print(list(itertools.accumulate(Rng(5))), list(itertools.zip_longest(Rng(1), It('ab'), fillvalue='-')))
print(list(itertools.starmap(pow, It([(2, 3), (3, 2)]))), sorted(itertools.permutations(Rng(2))))


# user number types in sum/min/max
class Money:
    def __init__(self, c):
        self.c = c

    def __add__(self, o):
        return Money(self.c + (o.c if isinstance(o, Money) else o))

    __radd__ = __add__

    def __lt__(self, o):
        return self.c < o.c

    def __repr__(self):
        return 'Money(%d)' % self.c


print(sum([Money(1), Money(2), Money(3)]), sum([Money(5)], Money(10)), min(Money(3), Money(1)))


# zip stops at the shortest and does not over-consume
it = It([1, 2, 3, 4])
print(list(zip(Rng(2), it)), it.items)

# enumerate/zip/map are lazy
class Loud:
    def __iter__(self):
        for i in range(3):
            print('yield', i)
            yield i


e = enumerate(Loud())
print('created')
print(next(e), next(e))


# a dict-like object for dict() / dict.update(): keys() + __getitem__
class Mapping:
    def keys(self):
        return ['a', 'b']

    def __getitem__(self, k):
        return k.upper()


print(dict(Mapping()), {**Mapping()})
d = {}
d.update(Mapping())
print(d)


# errors
class Nothing:
    pass


def attempt(label, f):
    try:
        print(label, '->', f())
    except (TypeError, ValueError) as ex:
        print(label, '->', type(ex).__name__ + ':', ex)


attempt('sum(Nothing())', lambda: sum(Nothing()))
attempt('sum([Nothing()])', lambda: sum([Nothing()]))
attempt('sum([1, Nothing()])', lambda: sum([1, Nothing()]))
attempt('any(Nothing())', lambda: any(Nothing()))
attempt('all(Nothing())', lambda: all(Nothing()))
attempt('list(map(abs, Nothing()))', lambda: list(map(abs, Nothing())))
attempt('list(zip(Rng(1), Nothing()))', lambda: list(zip(Rng(1), Nothing())))
attempt('min(Nothing())', lambda: min(Nothing()))
attempt('max(Nothing(), Nothing())', lambda: max(Nothing(), Nothing()))
attempt('sorted(Nothing())', lambda: sorted(Nothing()))
attempt('set(Nothing())', lambda: set(Nothing()))
attempt('dict(Nothing())', lambda: dict(Nothing()))
attempt('dict([Nothing()])', lambda: dict([Nothing()]))
attempt('len(Nothing())', lambda: len(Nothing()))
attempt('len(It([]))', lambda: len(It([])))
attempt('iter(Nothing())', lambda: iter(Nothing()))
attempt('next(Rng(1))', lambda: next(Rng(1)))
attempt('{**Nothing()}', lambda: {**Nothing()})
attempt('dict(**Nothing())', lambda: dict(**Nothing()))
attempt('f(*Nothing())', lambda: print(*Nothing()))
attempt('min(It([]))', lambda: min(It([])))
attempt('max(Rng(0), default=None)', lambda: max(Rng(0), default=None))
attempt('divmod(Nothing(), 2)', lambda: divmod(Nothing(), 2))
attempt('abs(Nothing())', lambda: abs(Nothing()))
attempt('hash(It) ok', lambda: hash(It([])) is not None)
attempt('sum strings', lambda: sum(It(['a', 'b']), ''))
