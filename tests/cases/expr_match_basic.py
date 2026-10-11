# match statement: literals, captures, wildcard, value patterns, guards, OR/AS patterns.
class Tag:
    def __init__(self, name):
        self.name = name

    def __eq__(self, other):
        return isinstance(other, Tag) and other.name == self.name

    def __repr__(self):
        return "Tag(%r)" % self.name


class Color:
    RED = Tag("red")
    GREEN = Tag("green")


class Consts:
    LIMIT = 10
    NAME = "consts"


def lit(v):
    match v:
        case 0:
            return "zero"
        case 1 | 2 | 3:
            return "small"
        case -1:
            return "minus one"
        case 1.5:
            return "one and a half"
        case -2.5:
            return "neg float"
        case 1 + 2j:
            return "complex"
        case -1 - 1j:
            return "neg complex"
        case "hello" | "hi":
            return "greeting"
        case "con" "cat":
            return "concatenated"
        case b"bytes":
            return "bytes"
        case None:
            return "none"
        case True:
            return "true"
        case False:
            return "false"
        case Color.RED:
            return "red"
        case Consts.LIMIT:
            return "limit"
        case Consts.NAME:
            return "name const"
        case _:
            return "other"


for v in [0, 1, 3, -1, 1.5, -2.5, 1 + 2j, -1 - 1j, "hi", "concat", b"bytes", None, True, False, 0.0, 1.0,
          Color.RED, Color.GREEN, Tag("red"), 10, "consts", [], "x"]:
    print(repr(v), "->", lit(v))


def cap(v):
    match v:
        case int(n) if n > 100:
            return "big int %d" % n
        case int() as n if n < 0:
            return "negative %d" % n
        case (1 | 2) as small:
            return "small %d" % small
        case str() as s if len(s) > 3:
            return "long str " + s
        case x if x == "ab":
            return "guarded ab"
        case x:
            return "captured %r" % (x,)


for v in [500, -3, 2, "abcdef", "ab", "zz", 7, 2.0]:
    print(repr(v), "->", cap(v))
# guard sees capture; capture persists after match
match 42:
    case n if n > 50:
        print("no")
    case n:
        print("n is", n)
print(n)
# subject evaluated once
log = []


def subj():
    log.append("subj")
    return 5


match subj():
    case 1:
        pass
    case 2:
        pass
    case 5:
        print("five", log)
# guard evaluation order and side effects
log.clear()


def gd(name, r):
    log.append(name)
    return r


match 3:
    case 3 if gd("g1", False):
        print("no")
    case 4 if gd("g2", True):
        print("no")
    case 3 if gd("g3", True):
        print("matched g3", log)
# no case matched -> nothing happens
match "nothing":
    case 1:
        print("no")
print("after unmatched")
# bool/int distinction in literal patterns: 1 matches True? (== comparison) but True uses `is`
for v in [True, 1, 1.0]:
    match v:
        case True:
            print(repr(v), "is True pattern")
        case 1:
            print(repr(v), "matched literal 1")
# OR pattern with captures in each alternative
for v in [(1, "a"), ["b", 2], (3,)]:
    match v:
        case (1, x) | [x, 2]:
            print("or-capture", x)
        case (x,) | [x, _, _]:
            print("single", x)
# AS pattern binding whole sequence
match [1, 2, 3]:
    case [1, *rest] as whole:
        print(whole, rest)
# match on a tuple subject without parens
a, b = 1, "z"
match a, b:
    case 1, "y":
        print("no")
    case 1, ("z" | "w") as second:
        print("tuple subject", second)
# nested match
for v in [(1, 2), (2, 1)]:
    match v:
        case (x, y):
            match x > y:
                case True:
                    print("desc", x, y)
                case False:
                    print("asc", x, y)
# soft keywords usable as names
match = [1]
case = 2
print(match, case)
match match:
    case [case]:
        print("match/case as names", case)
_ = "underscore"
match 9:
    case _:
        print("wildcard does not bind", _)
