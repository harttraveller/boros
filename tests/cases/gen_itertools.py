"""Interpreted generators and functions driving (and driven by) itertools
and other builtin iterator consumers."""
import itertools
import functools
import operator


def naturals(start=0):
    n = start
    while True:
        yield n
        n += 1


def squares():
    for n in naturals(1):
        yield n * n


print(list(itertools.islice(naturals(), 5)))
print(list(itertools.islice(squares(), 2, 10, 3)))
print(list(itertools.takewhile(lambda x: x < 30, squares())))
print(list(itertools.islice(itertools.dropwhile(lambda x: x < 30, squares()), 3)))
print(list(itertools.islice(itertools.count(10, 5), 4)))
print(list(itertools.chain(naturals(3) if False else range(2), squares.__name__, (x for x in 'ab'))))
print(list(itertools.islice(itertools.chain.from_iterable(([i] * i for i in naturals(1))), 10)))

# accumulate with interpreted functions
def running_max(a, b):
    return a if a > b else b


print(list(itertools.accumulate([3, 1, 4, 1, 5, 9, 2, 6], running_max)))
print(list(itertools.accumulate(range(1, 6), lambda a, b: a * b, initial=1)))
print(list(itertools.accumulate(itertools.islice(naturals(1), 5))))

# groupby with interpreted key functions over a generator
def words():
    yield from ['apple', 'avocado', 'banana', 'blueberry', 'cherry', 'apricot']


for key, grp in itertools.groupby(words(), key=lambda w: w[0]):
    print(key, list(grp))
print([(k, len(list(g))) for k, g in itertools.groupby('aaabccdd')])

# groupby where the key function is a bound method of an interpreted class
class Bucket:
    def __init__(self, size):
        self.size = size

    def of(self, x):
        return x // self.size


print([(k, list(g)) for k, g in itertools.groupby(range(10), Bucket(4).of)])

# map / filter / zip / enumerate over interpreted generators
print(list(map(lambda x: x + 1, itertools.islice(naturals(), 3))))
print(list(filter(lambda x: x % 3 == 0, itertools.islice(squares(), 10))))
print(list(zip(naturals(), 'xyz', squares())))
print(list(itertools.zip_longest('ab', itertools.islice(naturals(), 4), fillvalue='-')))
print(list(itertools.starmap(pow, zip(range(4), itertools.repeat(2)))))
print(list(itertools.compress(naturals(), [1, 0, 1, 0, 1])))
print(list(itertools.filterfalse(lambda x: x % 2, range(8))))
print(list(itertools.pairwise(itertools.islice(squares(), 5))))
print(list(itertools.batched(itertools.islice(naturals(), 7), 3)))

# cycle + islice and repeat
print(list(itertools.islice(itertools.cycle(x for x in 'ab'), 5)))
print(list(itertools.repeat('r', 3)))

# tee of an interpreted generator
a, b = itertools.tee(itertools.islice(squares(), 4))
print(list(a), list(b))

# product / permutations / combinations with generators as input
print(list(itertools.product((x for x in 'ab'), repeat=2)))
print(list(itertools.permutations(itertools.islice(naturals(), 3), 2)))
print(list(itertools.combinations(itertools.islice(naturals(), 4), 3)))
print(list(itertools.combinations_with_replacement('ab', 2)))

# functools.reduce with interpreted generator and function
print(functools.reduce(lambda acc, x: acc * 10 + x, itertools.islice(naturals(1), 5), 0))
print(functools.reduce(operator.add, (str(i) for i in range(4))))

# sorted / min / max with key functions on generators
people = [('ann', 31), ('bob', 25), ('cy', 40)]
print(sorted((p for p in people), key=lambda p: p[1]))
print(max((p for p in people), key=lambda p: len(p[0])), min(people, key=lambda p: -p[1]))

# itertools stops pulling from infinite generators exactly when needed
def logged():
    for i in naturals():
        print('  logged produces', i)
        yield i


print(list(itertools.takewhile(lambda x: x < 2, logged())))

# islice of an interpreted generator then resume the generator directly
g = naturals()
print(list(itertools.islice(g, 3)), next(g), next(g))

# an infinite interpreted generator with send driven manually
def fib():
    a, b = 0, 1
    while True:
        yield a
        a, b = b, a + b


print(list(itertools.islice(fib(), 15)))
print(next(itertools.dropwhile(lambda x: x < 1000, fib())))

# sum/len of generators produced from itertools.count
print(sum(itertools.islice(itertools.count(1), 100)))

# iterating a dict items generator via itertools.chain
d1, d2 = {'a': 1}, {'b': 2}
print(dict(itertools.chain(d1.items(), (kv for kv in d2.items()))))
