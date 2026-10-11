# Augmented assignment: names, attributes, subscripts; evaluation order; in-place.
log = []


class Obj:
    def __init__(self):
        self.__dict__["x"] = 1

    def __getattr__(self, name):
        log.append(("getattr-missing", name))
        return 0

    def __setattr__(self, name, value):
        log.append(("setattr", name, value))
        self.__dict__[name] = value


o = Obj()
o.x += 5
o.y += 2
print(o.x, o.y, log)
log.clear()


class Seq:
    def __init__(self):
        self.d = {}

    def __getitem__(self, k):
        log.append(("get", k))
        return self.d.get(k, 0)

    def __setitem__(self, k, v):
        log.append(("set", k, v))
        self.d[k] = v


def idx(i):
    log.append(("idx", i))
    return i


def src(v):
    log.append(("src", v))
    return v


def holder(h):
    log.append("holder")
    return h


s = Seq()
holder(s)[idx(1)] += src(10)
print(log)
log.clear()
holder(s)[idx(1):idx(2)] += src(1)
print(log)
log.clear()
# in-place semantics on lists
a = [1, 2]
b = a
a += [3]
print(a, b, a is b)
a += (4, 5)
a += "xy"
print(b)
a *= 2
print(b, a is b)
t = (1, 2)
u = t
t += (3,)
print(t, u, t is u)
st = "ab"
st += "cd"
st *= 2
print(st)
# tuple containing a list: error but mutation happens
tl = ([1],)
try:
    tl[0] += [2]
except TypeError as e:
    print("TypeError:", e)
print(tl)
# sets and dicts
ss = {1, 2}
alias = ss
ss |= {3}
ss -= {1}
ss &= {2, 3, 4}
ss ^= {5}
print(sorted(alias), alias is ss)
dd = {"a": 1}
dalias = dd
dd |= {"b": 2}
print(dalias, dd is dalias)
# all the operators on ints
n = 100
n += 1; n -= 3; n *= 2; n //= 3; n %= 50; n **= 2; n <<= 3; n >>= 1; n &= 0xFFF; n |= 1; n ^= 0x10
print(n)
f = 7.5
f /= 2; f //= 1; f %= 2.5
print(f)


class Num:
    def __init__(self, v):
        self.v = v

    def __add__(self, o):
        log.append("add")
        return Num(self.v + o)

    def __iadd__(self, o):
        log.append("iadd")
        if o < 0:
            return NotImplemented
        self.v += o
        return self

    def __radd__(self, o):
        log.append("radd")
        return Num(o + self.v)

    def __isub__(self, o):
        log.append("isub")
        return None


m = Num(1)
m0 = m
m += 5
print(m.v, m is m0, log)
log.clear()
m += -1
print(m.v, m is m0, log)
log.clear()
k = 3
k += Num(4)
print(type(k).__name__, k.v, log)
log.clear()
m -= 1
print(m, log)
log.clear()


class OnlyAdd:
    def __init__(self, v):
        self.v = v

    def __add__(self, o):
        return OnlyAdd(self.v + o)


p = OnlyAdd(1)
p0 = p
p += 1
print(p.v, p is p0)
try:
    z = OnlyAdd(1)
    z -= 1
except TypeError as e:
    print("TypeError:", e)
try:
    q = [1]
    q += 5
except TypeError as e:
    print("TypeError:", e)
try:
    q = 1
    q += "s"
except TypeError as e:
    print("TypeError:", e)
try:
    undefined_thing += 1
except NameError as e:
    print("NameError:", e)


def loc():
    try:
        cnt += 1
    except UnboundLocalError as e:
        print("UnboundLocalError:", e)


loc()
# nested subscripts and attributes
grid = [[0] * 3 for _ in range(2)]
grid[1][2] += 7
grid[0][-1] -= 1
print(grid)
d = {"k": [1]}
d["k"] += [2]
d["k"][0] *= 10
print(d)


class Box:
    pass


bx = Box()
bx.items = []
alias_items = bx.items
bx.items += [1]
print(alias_items, bx.items is alias_items)
bx.count = 0
for _ in range(3):
    bx.count += 1
print(bx.count)
cnt = {}
for ch in "banana":
    cnt[ch] = cnt.get(ch, 0) + 1
print(cnt)
g = 0


def bump():
    global g
    g += 2


bump(); bump()
print(g)
