# Assignment expressions (walrus) in various contexts.
data = [3, 1, 4, 1, 5, 9, 2, 6]
if (n := len(data)) > 5:
    print("long", n)
it = iter(data)
total = 0
while (x := next(it, None)) is not None:
    total += x
print(total, x)
print([y for v in data if (y := v * 2) > 6], y)
print([(z := v) for v in range(3)], z)
print({k: (w := k * k) for k in range(4)}, w)
print(sum(q for q in range(5) if (last := q) % 2), last)
print((a := 1, b := 2), a, b)
print([a := 10, a + 1], a)


def f():
    res = [m for m in range(5) if (found := m) > 2]
    return res, found


print(f())


def g():
    total = 0
    vals = [(total := total + v) for v in range(5)]
    return vals, total


print(g())


def outer():
    def inner():
        [hit := t for t in "abc"]
        return hit

    hit = "unset"
    r = inner()
    return r, hit


print(outer())


def nl():
    count = 0

    def bump():
        nonlocal count
        [count := count + 1 for _ in range(3)]

    bump()
    return count


print(nl())
# walrus inside nested comprehension binds in the containing function scope
print([[(cell := i * j) for j in range(3)] for i in range(3)], cell)
# walrus in conditional expression and lambda
print((p := 5) if True else 0, p)
fn = lambda v: (sq := v * v) + sq
print(fn(3))
# walrus in function call argument
print(abs(r := -7), r)
# walrus and short-circuit
s = None
print(0 and (s := 1), s)
print(1 or (s := 2), s)
print(0 or (s := 3), s)
# walrus in comprehension iterable condition referencing outer
lines = ["a=1", "b", "c=3"]
print([(k, v) for line in lines if (parts := line.split("="))[1:] for k, v in [parts]])
# global scope walrus in genexp
print(any((hit2 := c) == "q" for c in "xyqz"), hit2)


class K:
    vals = [1, 2, 3]
    doubled = [v * 2 for v in vals]
    total = (cnt := len(vals))


print(K.doubled, K.total, K.cnt)
# walrus with attribute-less targets in while with complex condition
buf = list("hello")
out = []
while buf and (ch := buf.pop()) != "e":
    out.append(ch)
print(out, ch)
print([(i, j) for i in range(3) if (j := i ** 2) or i == 0])
