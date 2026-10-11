# Mapping patterns: keys are looked up with the mapping's get() method,
# duplicate value-pattern keys raise ValueError, too-short mappings fail early.
class K:
    a = "a"


try:
    match {"a": 1, "b": 2}:
        case {K.a: 1, "a": 2}:
            print("matched")
except ValueError as e:
    print("ValueError:", e)
match {"a": 1}:
    case {K.a: 1, "a": 2}:
        print("matched")
    case _:
        print("short mapping fails before duplicate check")


class Tricky(dict):
    def __getitem__(self, k):
        return "via __getitem__"


match Tricky(x=1):
    case {"x": v}:
        print("value", v)


class Missing(dict):
    def __missing__(self, k):
        return "missing"


match Missing(x=1):
    case {"y": v}:
        print("no:", v)
    case {"x": v}:
        print("x", v)
