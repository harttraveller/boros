# Tuple/list/star unpacking in assignments and for-targets.
a, b = 1, 2
print(a, b)
a, b = b, a
print(a, b)
(c, d), e = (3, 4), 5
print(c, d, e)
[f, g] = "xy"
print(f, g)
h, *rest = range(5)
print(h, rest)
*init, last = [1, 2, 3]
print(init, last)
first, *mid, end = "abcde"
print(first, mid, end)
p, *q, r = 1, 2
print(p, q, r)
*all_, = (9, 8)
print(all_)
[x, [y, *z]], w = [1, [2, 3, 4]], 5
print(x, y, z, w)
(i,) = [42]
print(i)
[j] = {7: "a"}
print(j)
k, l = {"k": 1, "l": 2}
print(k, l)
m, n = iter([10, 20])
print(m, n)
() = []
[] = ()
print("empty ok")
for u, v in [(1, 2), (3, 4)]:
    print(u, v, end="; ")
print()
for (u, v), *ws in [((1, 2), 3, 4), ((5, 6),)]:
    print(u, v, ws, end="; ")
print()
for idx, (ch, num) in enumerate(zip("ab", [1, 2])):
    print(idx, ch, num, end="; ")
print()


class O:
    pass


o = O()
lst = [0, 0, 0]
o.a, lst[1], *o.b = 1, 2, 3, 4
print(o.a, lst, o.b)
for o.c, lst[0] in [(5, 6)]:
    pass
print(o.c, lst)
dct = {}
for dct["k"] in range(3):
    pass
print(dct)
# evaluation order of targets
log = []


class T:
    def __setattr__(self, name, value):
        log.append((name, value))
        object.__setattr__(self, name, value)


t = T()
t.x, t.y, t.z = 1, 2, 3
print(log)
log.clear()
t.x, (t.y, t.z) = "a", "bc"
print(log)
# swap via indexes uses already-evaluated rhs
arr = [1, 2, 3]
arr[0], arr[2] = arr[2], arr[0]
print(arr)
ii = 0
ii, arr[ii] = 2, "set"
print(ii, arr)
# errors
try:
    a, b, c = 1, 2
except ValueError as ex:
    print("ValueError:", ex)
try:
    a, *b, c = [1]
except ValueError as ex:
    print("ValueError:", ex)
try:
    a, b = 5
except TypeError as ex:
    print("TypeError:", ex)
try:
    a, b = None
except TypeError as ex:
    print("TypeError:", ex)
try:
    (a, b), c = [1, 2]
except TypeError as ex:
    print("TypeError:", ex)
try:
    a, b = iter([1])
except ValueError as ex:
    print("ValueError:", ex)
try:
    a, b = "x"
except ValueError as ex:
    print("ValueError:", ex)


# unpacking a generator stops consuming after error check
def gen():
    for v in range(5):
        log.append(v)
        yield v


log.clear()
try:
    a, b = gen()
except ValueError as ex:
    print("ValueError:", ex, log)
log.clear()
a, *b = gen()
print(a, b, log)


# custom iterables
class Three:
    def __iter__(self):
        return iter((1, 2, 3))


a, b, c = Three()
print(a, b, c)
*xs, = Three()
print(xs)


class GI:
    def __getitem__(self, i):
        if i >= 3:
            raise IndexError
        return i * 10


a, b, c = GI()
print(a, b, c, [*GI()])
# nested star with strings
(a, *b), *c = "hey", "you"
print(a, b, c)
# unpack in comprehension target
print([a + b for a, b in [(1, 2), (3, 4)]], {k: v for k, *v in ["abc", "de"]})
# unpack dict items
for key, val in sorted({"b": 2, "a": 1}.items()):
    print(key, val, end=" ")
print()
# rhs evaluated fully before any assignment
xx = [1, 2]
xx, yy = xx + [3], xx
print(xx, yy)
