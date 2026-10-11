# del statement and chained assignment.
a = 1
del a
try:
    print(a)
except NameError as e:
    print("NameError:", e)
try:
    del never_defined
except NameError as e:
    print("NameError:", e)
x, y, z = 1, 2, 3
del x, y
print("z" in globals(), "x" in globals())
lst = [0, 1, 2, 3, 4]
del lst[0], lst[-1]
print(lst)
d = {"a": 1, "b": 2, "c": 3}
del d["a"]
try:
    del d["zz"]
except KeyError as e:
    print("KeyError:", e)
print(d)
(p, q) = (5, 6)
del (p, q)
[r, s] = 7, 8
del [r, s]
print("p" in globals(), "r" in globals())


class O:
    cls_attr = 1


o = O()
o.attr = 2
del o.attr
try:
    del o.attr
except AttributeError as e:
    print("AttributeError:", e)
try:
    del o.cls_attr
except AttributeError as e:
    print("AttributeError:", e)
del O.cls_attr
print(hasattr(O, "cls_attr"))
nested = {"k": [1, 2, {"z": 0}]}
del nested["k"][2]["z"], nested["k"][0]
print(nested)


def f():
    v = 1
    del v
    try:
        return v
    except UnboundLocalError as e:
        return "UnboundLocalError: " + str(e)


print(f())


def g():
    v = 1
    del v
    v = 2
    return v


print(g())


def h():
    w = 5

    def inner():
        nonlocal w
        del w

    inner()
    try:
        return w
    except NameError as e:
        return type(e).__name__ + ": " + str(e)


print(h())


def del_global():
    global gv
    gv = 1
    del gv


del_global()
print("gv" in globals())


def del_loop():
    for i in range(3):
        pass
    del i
    return "ok"


print(del_loop())
# del with subscript/attribute on custom objects
log = []


class Del:
    def __delitem__(self, k):
        log.append(("delitem", k))

    def __delattr__(self, n):
        log.append(("delattr", n))


dd = Del()
del dd[1], dd["x":"y"], dd.foo, dd[1, 2]
print(log)
# chained assignment
a = b = c = []
a.append(1)
print(a, b, c, a is b is c)
x = y = 5
x += 1
print(x, y)
log.clear()


class T:
    def __setitem__(self, k, v):
        log.append(("set", k, v))


t = T()


def val():
    log.append("rhs")
    return 9


t["first"] = t["second"] = val()
print(log)
i = 0
arr = [10, 20, 30]
i = arr[i] = 2
print(i, arr)
arr2 = [0, 0, 0, 0]
j = 0
arr2[j] = j = 3
print(arr2, j)
m, n = p2 = 1, 2
print(m, n, p2)
u = (v, w) = [3, 4]
print(u, v, w)
ob = O()
ob.a = ob.b = "same"
print(ob.a, ob.b)
k1 = k2 = {}
k1["x"] = 1
print(k2)
# annotated assignment (values; __annotations__ is covered in expr_annotations.py)
ann: int = 5
ann2: list
print(ann, "ann2" in globals())


def fa():
    loc: int = 3
    loc2: str
    return loc


print(fa())
