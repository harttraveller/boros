"""User-defined iterator classes, the old __getitem__ protocol,
iter(callable, sentinel) and error messages of iter()/next()."""


class Range2:
    def __init__(self, n):
        self.n = n

    def __iter__(self):
        return Range2Iter(self.n)


class Range2Iter:
    def __init__(self, n):
        self.i = 0
        self.n = n

    def __iter__(self):
        return self

    def __next__(self):
        if self.i >= self.n:
            raise StopIteration
        self.i += 1
        return self.i * 2


r = Range2(4)
print(list(r), list(r), sum(r), 6 in r, 7 in r)
for x in r:
    print('for', x)
a, *b = r
print(a, b)
print(sorted(r, reverse=True), max(r), dict.fromkeys(r))
print([x for x in r], {x % 4 for x in r}, list(zip(r, r)))
it = iter(r)
print(next(it), next(it), next(it, None), next(it), next(it, 'done'))

# __iter__ implemented as a generator method
class Tree:
    def __init__(self, value, *children):
        self.value = value
        self.children = children

    def __iter__(self):
        yield self.value
        for c in self.children:
            yield from c


t = Tree(1, Tree(2, Tree(3)), Tree(4))
print(list(t), list(iter(t)))

# old-style sequence iteration via __getitem__
class Seq:
    def __getitem__(self, i):
        if i >= 3:
            raise IndexError(i)
        return 'item%d' % i


print(list(Seq()), 'item1' in Seq())
for v in Seq():
    print('seq', v)
print(list(reversed([x for x in Seq()])))

# __getitem__ raising StopIteration also ends iteration
class Seq2:
    def __getitem__(self, i):
        if i == 2:
            raise StopIteration
        return i


print(list(Seq2()))

# iter(callable, sentinel) with interpreted functions and callables
data = [1, 2, 3, 0, 4]
pos = [0]

def reader():
    v = data[pos[0]]
    pos[0] += 1
    return v


print(list(iter(reader, 0)))

class Counter:
    def __init__(self):
        self.n = 0

    def __call__(self):
        self.n += 1
        return self.n


print(list(iter(Counter(), 4)))
lines = iter(['a', 'b', '', 'c'])
print(list(iter(lambda: next(lines), '')))
it = iter(Counter(), 3)
print(next(it), next(it), next(it, 'sentinel reached'), next(it, 'stays exhausted'))

# a callable-iterator stops if the callable raises StopIteration
def raiser_factory():
    vals = iter([5, 6])

    def f():
        return next(vals)
    return f


print(list(iter(raiser_factory(), None)))

# errors
class NotIterable:
    pass


try:
    iter(NotIterable())
except TypeError as e:
    print('TypeError', e)
try:
    for _ in NotIterable():
        pass
except TypeError as e:
    print('TypeError', e)
try:
    next(NotIterable())
except TypeError as e:
    print('TypeError', e)
try:
    next([1, 2])
except TypeError as e:
    print('TypeError', e)

class BadIter:
    def __iter__(self):
        return 42


try:
    iter(BadIter())
except TypeError as e:
    print('TypeError', e)

try:
    iter(42, 0)
except TypeError as e:
    print('TypeError', e)

# an iterator raising mid-way
class Faulty:
    def __init__(self):
        self.i = 0

    def __iter__(self):
        return self

    def __next__(self):
        self.i += 1
        if self.i == 3:
            raise ValueError('faulty at 3')
        return self.i


out = []
try:
    for v in Faulty():
        out.append(v)
except ValueError as e:
    print(out, e)

# iterator protocol used by builtins: enumerate, map with two iterators, str.join
class Letters:
    def __init__(self, s):
        self.s = s

    def __iter__(self):
        return iter(self.s)


print(list(enumerate(Letters('abc'))), '-'.join(Letters('xyz')), list(map(str.__add__, Letters('ab'), Letters('cd'))))

# __reversed__ and __len__/__length_hint__ with list()
class Rev:
    def __init__(self, items):
        self.items = items

    def __iter__(self):
        return iter(self.items)

    def __reversed__(self):
        yield from self.items[::-1]

    def __len__(self):
        return len(self.items)


print(list(reversed(Rev([1, 2, 3]))), len(Rev([1])), list(Rev([4, 5])))

# an iterator whose __next__ is a generator-backed delegation
class GenBacked:
    def __init__(self):
        self._g = self._gen()

    def _gen(self):
        yield 'one'
        yield 'two'

    def __iter__(self):
        return self

    def __next__(self):
        return next(self._g)


print(list(GenBacked()))

# iterators are consumed only once
it = iter(Range2(3))
print(list(it), list(it))
