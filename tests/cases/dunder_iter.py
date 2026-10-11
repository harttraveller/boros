# Iteration protocol: __iter__/__next__, old-style __getitem__ iteration,
# iter()/next() on objects lacking the methods, __iter__ = None.


class Countdown:
    def __init__(self, n):
        self.n = n

    def __iter__(self):
        return self

    def __next__(self):
        if self.n <= 0:
            raise StopIteration
        self.n -= 1
        return self.n


print(list(Countdown(4)))
for v in Countdown(2):
    print('for', v)
it = iter(Countdown(3))
print(next(it), next(it), next(it), next(it, 'done'))
try:
    next(it)
except StopIteration as e:
    print('StopIteration', e.args)


class GenIter:
    def __init__(self, items):
        self.items = items

    def __iter__(self):
        for x in self.items:
            yield x * 2


g = GenIter([1, 2, 3])
print(list(g), list(g), sum(g), tuple(g), sorted(g, reverse=True))
print([x + 1 for x in g], {x for x in g}, dict.fromkeys(g))
a, b, c = g
print(a, b, c)
first, *rest = g
print(first, rest)
print(*g)


# old-style sequence iteration through __getitem__
class Seq:
    def __init__(self, n):
        self.n = n

    def __getitem__(self, i):
        print('getitem', i)
        if i >= self.n:
            raise IndexError(i)
        return i * 10


print(list(Seq(3)))
print(type(iter(Seq(0))).__name__)
print(2 * 10 in Seq(5))
for x in Seq(1):
    print('seq for', x)


class StopSeq:
    def __getitem__(self, i):
        if i == 2:
            raise StopIteration
        return i


print(list(StopSeq()))


class KeyErrSeq:
    def __getitem__(self, i):
        raise KeyError(i)


try:
    list(KeyErrSeq())
except KeyError as e:
    print('KeyError', e)

# iter() with a sentinel calls a callable
class Counter:
    def __init__(self):
        self.i = 0

    def __call__(self):
        self.i += 1
        return self.i


print(list(iter(Counter(), 4)))


# errors
class Nothing:
    pass


class IterReturnsInt:
    def __iter__(self):
        return 5


class IterReturnsNonIterator:
    def __iter__(self):
        return Nothing()


class NextOnly:
    def __next__(self):
        return 1


class IterNone:
    __iter__ = None

    def __getitem__(self, i):
        if i >= 3:
            raise IndexError(i)
        return i


def attempt(label, f):
    try:
        print(label, '->', f())
    except TypeError as e:
        print(label, '-> TypeError:', e)


attempt('iter(Nothing())', lambda: iter(Nothing()))
attempt('list(Nothing())', lambda: list(Nothing()))
attempt('for over Nothing', lambda: [x for x in Nothing()])
attempt('next(Nothing())', lambda: next(Nothing()))
attempt('next(Nothing(), 1)', lambda: next(Nothing(), 1))
attempt('iter(IterReturnsInt())', lambda: iter(IterReturnsInt()))
attempt('list(IterReturnsInt())', lambda: list(IterReturnsInt()))
attempt('iter(IterReturnsNonIterator())', lambda: iter(IterReturnsNonIterator()))
attempt('iter(NextOnly())', lambda: iter(NextOnly()))
attempt('next(NextOnly())', lambda: next(NextOnly()))
attempt('iter(IterNone())', lambda: iter(IterNone()))
attempt('list(IterNone())', lambda: list(IterNone()))
attempt('unpack Nothing', lambda: [a for a, b in [Nothing()]])
attempt('star Nothing', lambda: [*Nothing()])
attempt('sum(Nothing())', lambda: sum(Nothing()))
attempt('zip(Nothing())', lambda: zip(Nothing()))
attempt('enumerate(Nothing())', lambda: enumerate(Nothing()))
attempt('dict(Nothing())', lambda: dict(Nothing()))
attempt("''.join(Nothing())", lambda: ''.join(Nothing()))


def unpack_nothing():
    a, b = Nothing()


attempt('a, b = Nothing()', unpack_nothing)


def yield_from_nothing():
    yield from Nothing()


attempt('yield from Nothing()', lambda: list(yield_from_nothing()))


# __next__ raising StopIteration with a value inside a for loop ends it
class StopVal:
    def __iter__(self):
        return self

    def __next__(self):
        raise StopIteration('val')


print(list(StopVal()))


# an iterator whose __next__ raises another error propagates it
class Broken:
    def __iter__(self):
        return self

    def __next__(self):
        raise ValueError('broken next')


try:
    for _ in Broken():
        pass
except ValueError as e:
    print('ValueError:', e)

# iter() of an iterator returns itself
cd = Countdown(1)
print(iter(cd) is cd)

# __length_hint__ is used by operator.length_hint
import operator


class Hint:
    def __iter__(self):
        return iter([1, 2])

    def __length_hint__(self):
        return 99


print(operator.length_hint(Hint()), operator.length_hint(Nothing(), 3), list(Hint()))
