# StopIteration from user iterators and other iterator protocol errors.


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


print(list(Countdown(3)), [x for x in Countdown(2)], sum(Countdown(4)))
it = Countdown(1)
print(next(it), next(it, 'default'))
try:
    next(it)
except StopIteration as e:
    print('StopIteration', e.args, e.value)


class WithValue:
    def __iter__(self):
        return self

    def __next__(self):
        raise StopIteration('payload')


try:
    next(WithValue())
except StopIteration as e:
    print('value:', e.value, e.args)
print(list(WithValue()))


class Failing:
    def __init__(self):
        self.i = 0

    def __iter__(self):
        return self

    def __next__(self):
        self.i += 1
        if self.i == 3:
            raise ValueError('failed at 3')
        return self.i


got = []
try:
    for x in Failing():
        got.append(x)
except ValueError as e:
    print(got, e)


class BadIter:
    def __iter__(self):
        return 42


try:
    iter(BadIter())
except TypeError as e:
    print('TypeError:', e)
try:
    for _ in BadIter():
        pass
except TypeError as e:
    print('TypeError:', e)


class NoNext:
    def __iter__(self):
        return self


try:
    for _ in NoNext():
        pass
except TypeError as e:
    print('TypeError:', e)


# old-style sequence iteration stops at IndexError
class Seq:
    def __getitem__(self, i):
        if i >= 3:
            raise IndexError(i)
        return i * 10


print(list(Seq()), 20 in Seq())


class SeqKeyError:
    def __getitem__(self, i):
        raise KeyError(i)


try:
    list(SeqKeyError())
except KeyError as e:
    print('KeyError from __getitem__:', e)

# iter(callable, sentinel)
vals = [1, 2, 3, 0, 4]
print(list(iter(lambda: vals.pop(0), 0)))


def raising_callable():
    raise StopIteration


print(list(iter(raising_callable, None)))

# StopIteration inside a for loop body is just an exception
try:
    for i in range(3):
        if i == 1:
            raise StopIteration('in body')
except StopIteration as e:
    print('body StopIteration:', e)

# zip / map / filter propagate errors from user iterators
try:
    list(zip([1, 2, 3], Failing()))
except ValueError as e:
    print('zip:', e)
try:
    list(map(lambda x: 1 // (x - 2), Countdown(4)))
except ZeroDivisionError as e:
    print('map:', e)

# unpacking with user iterators
a, b = Countdown(2)
print(a, b)
try:
    a, b = Countdown(3)
except ValueError as e:
    print('ValueError:', e)
try:
    a, b, c = Countdown(2)
except ValueError as e:
    print('ValueError:', e)
try:
    x, *rest = Countdown(0)
except ValueError as e:
    print('ValueError:', e)

# dict / sorted / min with user iterators raising
try:
    dict(Failing())
except TypeError as e:
    print('TypeError:', e)
try:
    min(Countdown(0))
except ValueError as e:
    print('ValueError:', e)

# exhausted iterator stays exhausted
c = Countdown(1)
print(list(c), list(c))
