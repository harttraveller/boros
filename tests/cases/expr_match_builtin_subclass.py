# match against instances of user subclasses of builtin types:
# list/tuple subclasses are sequences, dict subclasses are mappings, and
# subclasses of int/str/... keep the "match self" behaviour of their base.
class L(list):
    pass


class T(tuple):
    pass


class D(dict):
    pass


class MyInt(int):
    pass


class MyStr(str):
    pass


class MyIntArgs(int):
    __match_args__ = ("real",)


for v in [L([1, 2]), T((3, 4)), D(a=1), MyInt(5), MyStr("s"), L([9]), D(b=2)]:
    match v:
        case [a, b]:
            print(type(v).__name__, "seq", a, b)
        case {"a": a}:
            print(type(v).__name__, "map", a)
        case MyInt(i):
            print(type(v).__name__, "myint", i, type(i).__name__)
        case MyStr(s):
            print(type(v).__name__, "mystr", s)
        case [*items]:
            print(type(v).__name__, "star seq", items)
        case {**rest}:
            print(type(v).__name__, "map rest", rest)
        case _:
            print(type(v).__name__, "nothing")
match MyStr("abc"):
    case str(s):
        print("str() pattern on str subclass", s)
match MyStr("ab"):
    case [a, b]:
        print("no: str subclass is not a sequence")
    case _:
        print("str subclass not matched as sequence")
match MyInt(7):
    case int(n) if n == 7:
        print("int() pattern on int subclass", n)
match MyIntArgs(3):
    case MyIntArgs(r):
        print("explicit __match_args__", r)
