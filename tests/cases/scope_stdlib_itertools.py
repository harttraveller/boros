import itertools as it
import operator

print(list(it.chain([1, 2], 'ab', (3,))), list(it.chain.from_iterable([[1], [2, 3]])))
print([(k, list(g)) for k, g in it.groupby('aabbbca')])
words = ['apple', 'avocado', 'banana', 'blueberry', 'cherry']
print([(k, len(list(g))) for k, g in it.groupby(words, key=lambda w: w[0])])
print(list(it.accumulate([1, 2, 3, 4])), list(it.accumulate([1, 2, 3, 4], lambda a, b: a * b)))
print(list(it.accumulate([3, 1, 4], max, initial=2)))
print(list(it.product('ab', [0, 1])), len(list(it.product(range(3), repeat=2))))
print(list(it.permutations('abc', 2))[:4], list(it.combinations(range(4), 2)))
print(list(it.combinations_with_replacement('ab', 2)))
print(list(it.islice(it.count(10, 5), 3)), list(it.islice('abcdefg', 1, 6, 2)))
print(list(it.islice(it.cycle('xy'), 5)), list(it.repeat('r', 3)))
print(list(it.takewhile(lambda v: v < 3, [1, 2, 3, 1])), list(it.dropwhile(lambda v: v < 3, [1, 2, 3, 1])))
print(list(it.filterfalse(lambda v: v % 2, range(6))), list(it.compress('abcdef', [1, 0, 1, 0, 1])))
print(list(it.starmap(pow, [(2, 3), (3, 2)])), list(it.starmap(lambda a, b: a - b, [(5, 1)])))
print(list(it.zip_longest('abc', [1], fillvalue='-')))
a, b = it.tee(iter([1, 2, 3]))
print(list(a), list(b))
print(list(it.pairwise('abcd')), list(it.batched(range(7), 3)))


class Counted:
    def __init__(self, n):
        self.n = n

    def __iter__(self):
        for i in range(self.n):
            yield i


print(list(it.chain(Counted(2), Counted(3))), sum(it.islice(Counted(100), 5)))


def gen():
    yield 1
    yield 2


print(list(it.zip_longest(gen(), Counted(3))), list(map(operator.mul, gen(), gen())))
print(sorted(it.chain(*[[3, 1], [2]]), reverse=True))
