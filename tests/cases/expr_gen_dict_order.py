# Dict display keys and values are evaluated interleaved (k1, v1, k2, v2)
# even when the values contain yield.
log = []


def v(x):
    log.append(x)
    return x


def g():
    d = {v("k1"): (yield "y1"), v("k2"): (yield "y2")}
    return d


gen = g()
log.append(next(gen))
log.append(gen.send("a"))
try:
    gen.send("b")
except StopIteration as e:
    print(e.value, log)
