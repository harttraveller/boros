# match statement: sequence, mapping and class patterns.
import collections


def seq(v):
    match v:
        case []:
            return "empty"
        case [x]:
            return "one %r" % (x,)
        case [1, 2, *rest]:
            return "starts 1,2 rest=%r" % (rest,)
        case [first, *_, last] if first == last:
            return "same ends %r" % (first,)
        case (a, b):
            return "pair %r %r" % (a, b)
        case [*init, "end"]:
            return "ends with end, init=%r" % (init,)
        case [[x, y], [z, *w]]:
            return "nested %r %r %r %r" % (x, y, z, w)
        case [a, b, c, *more]:
            return "3+ %r %r %r %r" % (a, b, c, more)
        case _:
            return "not a sequence"


for v in [[], (), [7], (7,), [1, 2], [1, 2, 3, 4], (5, 0, 5), (8, 9), ["a", "b", "end"], [[1, 2], [3]],
          [[1, 2], [3, 4, 5]], range(3), range(2), "ab", b"ab", bytearray(b"ab"), {1: 2}, {1, 2}, 5,
          iter([1, 2]), collections.deque([4, 5]), memoryview(b"xy")]:
    print(type(v).__name__, "->", seq(v))


def mapping(v):
    match v:
        case {"type": "point", "x": x, "y": y}:
            return "point %r %r" % (x, y)
        case {"type": "circle", "r": r, **rest}:
            return "circle %r rest=%r" % (r, sorted(rest.items()))
        case {"k": [a, *b]}:
            return "k list %r %r" % (a, b)
        case {2: one, None: n, True: t}:
            return "literal keys %r %r %r" % (one, n, t)
        case {}:
            return "any mapping (len %d)" % len(v)
        case _:
            return "not mapping"


for v in [{"type": "point", "x": 1, "y": 2, "extra": 0}, {"type": "circle", "r": 3, "c": 1, "d": 2},
          {"k": [1, 2, 3]}, {"k": "str"}, {2: "a", None: "b", True: "c"}, {}, {"z": 1}, [], "s",
          collections.OrderedDict(type="point", x=0, y=9), collections.defaultdict(int)]:
    print(type(v).__name__, "->", mapping(v))
# **rest is a fresh dict
src = {"a": 1, "b": 2}
match src:
    case {"a": 1, **others}:
        others["c"] = 3
        print(others, src)
match {"a": 1}:
    case {**everything}:
        print("everything", everything)
# defaultdict must not create keys
dd = collections.defaultdict(list)
match dd:
    case {"missing": _}:
        print("no")
    case _:
        print("defaultdict untouched", dict(dd))


class Point:
    __match_args__ = ("x", "y")

    def __init__(self, x, y):
        self.x = x
        self.y = y


class Point3(Point):
    __match_args__ = ("x", "y", "z")

    def __init__(self, x, y, z):
        super().__init__(x, y)
        self.z = z


class NoArgs:
    def __init__(self):
        self.a = 1


def cls(v):
    match v:
        case Point3(0, 0, 0):
            return "origin3"
        case Point(0, 0):
            return "origin"
        case Point(x=0, y=yy):
            return "on y axis at %r" % yy
        case Point(xx, 0):
            return "on x axis at %r" % xx
        case Point3(_, _, z) if z > 0:
            return "above, z=%r" % z
        case Point(x, y=y) if x == y:
            return "diagonal %r" % x
        case Point():
            return "some point"
        case NoArgs(a=1):
            return "noargs a=1"
        case int(i) | float(i):
            return "number %r" % i
        case str(s) if s:
            return "nonempty str %r" % s
        case bool(b):
            return "bool %r" % b
        case list([1, *r]):
            return "list starting with 1, rest %r" % r
        case tuple((a, b)):
            return "tuple pair %r %r" % (a, b)
        case dict({"k": k}):
            return "dict with k=%r" % k
        case _:
            return "unknown"


for v in [Point3(0, 0, 0), Point(0, 0), Point(0, 5), Point(4, 0), Point3(1, 2, 3), Point(3, 3), Point(1, 2),
          NoArgs(), 7, 2.5, True, "s", "", [1, 2, 3], (1, 2), {"k": 9}, None]:
    print(type(v).__name__, "->", cls(v))
# attributes missing -> no match (AttributeError swallowed)
match NoArgs():
    case NoArgs(b=1):
        print("no")
    case NoArgs(a=a_val):
        print("a_val", a_val)


class Prop:
    __match_args__ = ("val",)

    @property
    def val(self):
        return "computed"


match Prop():
    case Prop(v):
        print("property via match_args", v)
# class patterns nest inside sequences and mappings
shapes = [Point(1, 1), {"p": Point(0, 2)}, [Point(5, 0), Point(0, 0)]]
for s in shapes:
    match s:
        case Point(x=1) as p:
            print("x=1 point", p.y)
        case {"p": Point(0, y)}:
            print("dict point y", y)
        case [Point(x, 0), Point(0, 0)]:
            print("list of points", x)
# dotted value patterns and module attributes
import math

for v in [math.pi, 0.0]:
    match v:
        case math.pi:
            print("pi")
        case _:
            print("not pi")
