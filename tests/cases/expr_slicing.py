# Slicing: reading, negative indices, steps, assignment, deletion.
s = list(range(10))
print(s[2:5], s[:3], s[7:], s[-3:], s[:-7], s[-5:-2], s[::2], s[1::3])
print(s[::-1], s[8:2:-2], s[-1:-4:-1], s[:2:-3], s[100:], s[-100:2], s[5:1])
print(s[::-3], s[None:None:None], s[None:3], s[2:None:2])
print("hello world"[::-1], "abcdef"[1:-1:2], (1, 2, 3, 4)[::-2], b"bytes"[1:3])
print(range(10)[2:8:3], range(10)[::-1][:3], list(range(10)[::-1][:3]))
i, j = 1, 4
print(s[i:j], s[i + 1:j * 2], s[-j:], s[len(s) // 2:])
try:
    s[::0]
except ValueError as e:
    print("ValueError:", e)
try:
    s["a":2]
except TypeError as e:
    print("TypeError:", e)
try:
    s[1.5]
except TypeError as e:
    print("TypeError:", e)
try:
    s[20]
except IndexError as e:
    print("IndexError:", e)
try:
    "abc"[5]
except IndexError as e:
    print("IndexError:", e)
try:
    (1, 2)[-3]
except IndexError as e:
    print("IndexError:", e)
# slice assignment
a = list(range(6))
a[1:3] = ["x", "y", "z"]
print(a)
a[:0] = [-1]
print(a)
a[len(a):] = [99, 100]
print(a)
a[2:5] = []
print(a)
a[::2] = "ABCD"
print(a)
a[:] = range(3)
print(a)
b = a
a[:] = (7, 8)
print(b, a is b)
a[1:1] = "pq"
print(a)
a[-1:] = []
print(a)
c = list(range(8))
c[::-2] = [0, 0, 0, 0]
print(c)
try:
    c[::2] = [1, 2]
except ValueError as e:
    print("ValueError:", e)
try:
    c[1:3] = 5
except TypeError as e:
    print("TypeError:", e)
try:
    t = (1, 2, 3)
    t[0:1] = [9]
except TypeError as e:
    print("TypeError:", e)
try:
    "abc"[0] = "z"
except TypeError as e:
    print("TypeError:", e)
# deletion
d = list(range(10))
del d[1:3]
print(d)
del d[::3]
print(d)
del d[-1]
print(d)
del d[::-2]
print(d)
del d[:]
print(d)
e = list(range(5))
del e[10:20]
del e[1], e[1]
print(e)
try:
    del e[7]
except IndexError as ex:
    print("IndexError:", ex)
# objects with __getitem__ receiving slices
log = []


class S:
    def __getitem__(self, k):
        log.append(k)
        return k

    def __setitem__(self, k, v):
        log.append(("set", k, v))

    def __delitem__(self, k):
        log.append(("del", k))


o = S()
print(o[1:2], o[::], o[:3], o[1:2:3], o[1:2, 3], o[..., 1], o[:, :], o[()], o[1,])
print(o[-1], o[None:], o[:, None])
o[1:2] = 5
o[::2, 1] = 6
del o[:4]
del o[1, 2:3]
print(log)
sl = slice(1, 8, 2)
print(s[sl], sl.start, sl.stop, sl.step, sl.indices(5), slice(3), slice(None).indices(4))
print(slice(1, 2) == slice(1, 2), slice(-3, None, -1).indices(10), repr(slice(1, None)))
x = "abcdefgh"
print(x[sl], x[slice(None, None, -2)], x[-2::-3])


class Idx:
    def __index__(self):
        return 2


print(s[Idx()], s[Idx():], s[:Idx()], s[::Idx()], "abc"[Idx()])
m = [[1, 2, 3], [4, 5, 6]]
print(m[1][::-1], m[-1][-1], [row[1:] for row in m])
bb = bytearray(b"hello")
bb[1:3] = b"EY"
del bb[-1]
print(bb)
