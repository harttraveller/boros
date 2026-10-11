# Short-circuit and/or return operands, not, truthiness protocol.
log = []


def t(x):
    log.append(x)
    return x


print(t(0) and t(1), log)
log.clear()
print(t(1) and t(0) and t(2), log)
log.clear()
print(t(0) or t("") or t([]), log)
log.clear()
print(t(0) or t(2) or t(3), log)
log.clear()
print(t(1) and t(2) or t(3), log)
log.clear()
print(t(0) and t(2) or t(3), log)
log.clear()
print(t(0) or t(1) and t(0), log)
log.clear()
print(repr(None or 0), repr("" and 1), repr([] or ()), repr(0.0 or 0j or None))
print([] and 1, {} or {"a": 1}, [0] and "yes", (0,) or 1)
print(not [], not [0], not "", not " ", not None, not 0.0, not 0j, not set())


class B:
    def __init__(self, v):
        self.v = v

    def __bool__(self):
        log.append(("bool", self.v))
        return self.v


class L:
    def __init__(self, n):
        self.n = n

    def __len__(self):
        log.append(("len", self.n))
        return self.n


print(B(True) and "x", B(False) or "y", log)
log.clear()
print(not B(True), not L(0), not L(3), log)
log.clear()
print(bool(L(0)), bool(L(2)), L(0) or "e", log)
log.clear()
r = B(False) and 1
print(type(r).__name__, r.v)
if L(0) or B(False):
    print("no")
else:
    print("both false", log)
log.clear()
x = 0
while not x or x < 3:
    x += 1
print(x)
print(1 if B(True) else 2, [i for i in range(5) if i and i % 2], log)
log.clear()


class Bad:
    def __bool__(self):
        return 1


try:
    not Bad()
except TypeError as e:
    print("TypeError:", e)
try:
    if Bad():
        pass
except TypeError as e:
    print("TypeError:", e)


class Neither:
    pass


print(bool(Neither()), not Neither())
a = [1]
b = a or [2]
print(b is a, (None or a) is a, (a and None) is None)
print(all([]), any([]), all([1, 0]), any([0, 2]))
print(0 or 0 or 0 or 7 and 8 and 9)
