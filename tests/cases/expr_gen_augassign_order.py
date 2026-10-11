# In `target op= (yield ...)` the target (and its subscript/attribute parts)
# is evaluated and loaded BEFORE the yield, as in CPython.
log = []


def v(x):
    log.append(x)
    return x


total = 0


def g1():
    global total
    total += yield "t"
    return total


gen = g1()
next(gen)
total = 100
try:
    gen.send(5)
except StopIteration as e:
    print("global", e.value, total)


class O:
    pass


o = O()
o.n = 1


def g2():
    o.n += yield "o"
    return o.n


gen = g2()
next(gen)
o.n = 50
try:
    gen.send(1)
except StopIteration as e:
    print("attr", e.value)
lst = [0, 0]


def g3():
    lst[v(1)] += yield "l"


gen = g3()
next(gen)
log.append("between")
lst[1] = 7
try:
    gen.send(2)
except StopIteration:
    print("item", lst, log)


def g4():
    count = 10

    def bump():
        nonlocal count
        count = 1000

    def gen():
        nonlocal count
        count += yield bump()
        return count

    return gen()


gen = g4()
next(gen)
try:
    gen.send(1)
except StopIteration as e:
    print("nonlocal", e.value)
