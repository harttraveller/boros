# yield inside the subscript of an assignment / augmented-assignment / del target.
def drive(g, sends):
    out = []
    try:
        out.append(next(g))
        for s in sends:
            out.append(g.send(s))
    except StopIteration as e:
        out.append(("ret", e.value))
    return out


def g1():
    a = [10, 20, 30]
    a[(yield "idx")] = "set"
    del a[(yield "del")]
    return a


def g2():
    a = [1, 2]
    a[(yield)] += 5
    return a


class O:
    pass


def g3():
    o = O()
    d = {}
    d[(yield "key")], o.attr = "v", "w"
    return d, o.attr


print(drive(g1(), [0, 1]))
print(drive(g2(), [1]))
print(drive(g3(), ["k"]))


def g4():
    a = [0, 0, 0]
    a[(yield "i")], *a[(yield "j"):] = "xyz"
    return a


print(drive(g4(), [0, 1]))
