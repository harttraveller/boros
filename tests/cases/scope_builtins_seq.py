class P:
    def __init__(self, name, age):
        self.name = name
        self.age = age

    def __repr__(self):
        return 'P(%s, %d)' % (self.name, self.age)

    def __lt__(self, other):
        return self.age < other.age


people = [P('ann', 31), P('bob', 25), P('cy', 31), P('dee', 19)]

# sorted / list.sort with key and reverse (stable)
print(sorted(people))
print(sorted(people, key=lambda p: p.name, reverse=True))
print(sorted(people, key=lambda p: -p.age))
print(sorted(people, reverse=True))
print(sorted('bAcD', key=str.lower), sorted([3, 1, 2], reverse=True))
people2 = list(people)
people2.sort(key=lambda p: (p.age, p.name))
print(people2)


def by_len(s):
    return len(s)


print(sorted(['ccc', 'a', 'bb', 'dd'], key=by_len))

# min / max with key / default
print(min(people), max(people))
print(min(people, key=lambda p: p.name), max(people, key=lambda p: len(p.name)))
print(max([], default='empty'), min([], key=len, default=None))
print(max(3, 7, 5), min('b', 'a', key=ord), max([1, 5, 2], key=lambda v: -v))
try:
    max([])
except ValueError as e:
    print('ValueError:', e)
try:
    min(1)
except TypeError as e:
    print('TypeError:', e)


# sum with start; instances with __add__ / __radd__
class V:
    def __init__(self, x):
        self.x = x

    def __add__(self, o):
        if isinstance(o, V):
            return V(self.x + o.x)
        return V(self.x + o)

    def __radd__(self, o):
        return V(o + self.x)

    def __repr__(self):
        return 'V(%r)' % self.x


print(sum([1, 2, 3]), sum([1, 2, 3], 10), sum([[1], [2]], []), sum([0.5, 0.25], start=1))
print(sum([V(1), V(2), V(3)]), sum([V(1)], V(10)))
try:
    sum(['a', 'b'], '')
except TypeError as e:
    print('TypeError:', e)

# zip, strict
print(list(zip('abc', [1, 2, 3], (True, False, None))))
print(list(zip('abcd', [1, 2])), list(zip()))
try:
    list(zip('abc', [1, 2], strict=True))
except ValueError as e:
    print('ValueError:', e)
try:
    list(zip('ab', [1, 2, 3], strict=True))
except ValueError as e:
    print('ValueError:', e)
print(list(zip(*[(1, 'a'), (2, 'b')])))

# enumerate with start
print(list(enumerate('xyz')), list(enumerate('xy', start=5)), list(enumerate([], 1)))

# map / filter with interpreted callables
print(list(map(lambda a, b: a * b, [1, 2, 3], [4, 5, 6])))
print(list(map(str.upper, 'ab')), list(map(by_len, ['a', 'bcd'])))
print(list(filter(lambda v: v % 2, range(7))), list(filter(None, [0, 1, '', 'x', [], [0]])))


class Pred:
    def __call__(self, v):
        return v > 2


print(list(filter(Pred(), [1, 2, 3, 4])), list(map(P, ['e'], [1])))

# any / all with generators and instances with __bool__ / __len__
class Truthy:
    def __init__(self, b):
        self.b = b

    def __bool__(self):
        return self.b


class Sized:
    def __len__(self):
        return 0


print(any(Truthy(False) for _ in range(3)), all([Truthy(True), Truthy(True)]), any([Sized()]), all([]))
calls = []


def check(v):
    calls.append(v)
    return v > 1


print(any(check(v) for v in [0, 1, 2, 3]), calls)
print(all(check(v) for v in [5, 0, 7]), calls)

# reversed / iter / next / len on instances
class Seq:
    def __init__(self, n):
        self.n = n

    def __len__(self):
        return self.n

    def __getitem__(self, i):
        if i >= self.n:
            raise IndexError(i)
        return i * 10


print(list(reversed(Seq(3))), list(Seq(4)), len(Seq(5)), 20 in Seq(3), 25 in Seq(3))
it = iter([1, 2])
print(next(it), next(it), next(it, 'done'))
counter = [0]


def tick():
    counter[0] += 1
    return counter[0]


print(list(iter(tick, 4)))
print(list(range(10))[::3], tuple(x for x in 'ab'), dict(zip('ab', range(2))), set('aab') == {'a', 'b'})
print(isinstance(people[0], (int, P)), issubclass(P, object), callable(P), callable(people[0]))
print(hasattr(people[0], 'age'), getattr(people[0], 'nope', 'dflt'), id(people[0]) == id(people[0]))
