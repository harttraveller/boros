# Annotated assignment statements: module/class annotations are evaluated
# (Python 3.13 semantics, no PEP 649) and recorded in __annotations__.
log = []


def ann(v):
    log.append(v)
    return v


x: ann("int") = 5
y: ann("list")
print(x, "y" in globals(), log)
print(__annotations__)


class C:
    a: int = 1
    b: "str"
    c: ann("c-ann") = ann("c-val")


print(C.a, hasattr(C, "b"), C.__annotations__, log)


class O:
    pass


o = O()
o.attr: ann("attr-ann") = 3
d = {}
d["k"]: ann("item-ann") = 4
(paren): int = 6
print(o.attr, d, paren, log, sorted(__annotations__))


def f():
    loc: undefined_name_is_fine = 1
    return loc


print(f())
try:
    z: undefined_annotation = 1
except NameError as e:
    print("NameError:", e)
