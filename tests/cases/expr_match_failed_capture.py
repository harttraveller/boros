# Names captured by a pattern that fails overall are not bound (CPython binds
# all captures only after the whole pattern has matched).
match [5, 2]:
    case [x, 1]:
        pass
    case _:
        pass
try:
    print(x)
except NameError as e:
    print("NameError:", e)
match {"a": 1, "b": 3}:
    case {"a": q, "b": 2}:
        pass
    case _:
        pass
print("q" in globals())
match (1, 2):
    case (1, y) if y > 5:
        pass
    case _:
        pass
print("y bound even though guard failed:", y)
match [1, 3]:
    case [a, 2] | [a, 4]:
        pass
    case _:
        pass
print("a" in globals())


def f(v):
    match v:
        case (p, 0):
            return "zero"
        case _:
            pass
    try:
        return p
    except UnboundLocalError:
        return "p unbound"


print(f((1, 0)), f((1, 1)))
