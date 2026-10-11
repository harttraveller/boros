import bisect
import heapq
import operator


class Task:
    def __init__(self, pri, name):
        self.pri = pri
        self.name = name

    def __lt__(self, other):
        return self.pri < other.pri

    def __repr__(self):
        return 'Task(%d, %s)' % (self.pri, self.name)


h = []
for t in [Task(3, 'c'), Task(1, 'a'), Task(2, 'b'), Task(0, 'z')]:
    heapq.heappush(h, t)
print([heapq.heappop(h) for _ in range(len(h))])
data = [5, 1, 8, 3, 9, 2]
heapq.heapify(data)
print(data[0], heapq.nsmallest(3, data), heapq.nlargest(2, data))
print(heapq.nsmallest(2, ['ccc', 'a', 'bb'], key=len), heapq.nlargest(1, [Task(1, 'x'), Task(5, 'y')]))
print(heapq.heappushpop([1, 4], 2), list(heapq.merge([1, 4], [2, 3])), list(heapq.merge(['b', 'aa'], ['c'], key=len)))
h2 = [(2, 'b'), (1, 'a')]
heapq.heapify(h2)
print(heapq.heapreplace(h2, (0, 'z')), h2[0])

# bisect
a = [1, 3, 3, 5, 9]
print(bisect.bisect_left(a, 3), bisect.bisect_right(a, 3), bisect.bisect(a, 4), bisect.bisect_left(a, 10))
bisect.insort(a, 4)
bisect.insort_left(a, 3)
print(a)
recs = [Task(1, 'a'), Task(4, 'b'), Task(7, 'c')]
print(bisect.bisect_left(recs, 5, key=lambda r: r.pri), bisect.bisect_right(recs, 4, key=operator.attrgetter('pri')))
bisect.insort(recs, Task(5, 'n'), key=lambda r: r.pri)
print(recs)
print(bisect.bisect(recs, Task(6, 'q')))

# operator helpers on interpreted instances
class Rec:
    def __init__(self, name, score, inner=None):
        self.name = name
        self.score = score
        self.inner = inner

    def __getitem__(self, k):
        return {'n': self.name, 's': self.score}[k]

    def total(self, bonus=0):
        return self.score + bonus

    def __repr__(self):
        return 'Rec(%s)' % self.name


rs = [Rec('b', 2, Rec('x', 0)), Rec('a', 2, Rec('y', 1)), Rec('c', 1, Rec('z', 2))]
print(sorted(rs, key=operator.attrgetter('score', 'name')))
print(list(map(operator.attrgetter('inner.name'), rs)), operator.attrgetter('name')(rs[0]))
print(sorted(rs, key=operator.itemgetter('s')), operator.itemgetter('n', 's')(rs[0]))
print(list(map(operator.methodcaller('total', bonus=10), rs)), operator.methodcaller('total')(rs[2]))
print(operator.itemgetter(1)([5, 6]), operator.itemgetter(slice(1, None))('abc'), operator.add(2, 3), operator.neg(4))
print(operator.index(5), operator.contains([1, 2], 2), operator.not_(0), operator.truth([]), operator.concat('a', 'b'))
print(operator.lt(Task(1, 'a'), Task(2, 'b')), operator.is_(None, None), operator.getitem(rs[0], 'n'))
lst = [1, 2, 3]
operator.setitem(lst, 0, 'x')
operator.delitem(lst, 1)
print(lst, operator.iadd([1], [2]), operator.length_hint(iter([1, 2, 3])))
try:
    operator.attrgetter('missing')(rs[0])
except AttributeError as e:
    print('AttributeError:', e)
