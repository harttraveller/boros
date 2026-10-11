# Name resolution in comprehensions, lambdas, class bodies, augmented
# assignment and del, including closures and global/nonlocal declarations.
gv = 10


class C:
    gv += 1
    lst = [1, 2]
    lst += [3]
    doubled = [v * 2 for v in lst]
    try:
        lam = (lambda: lst)()
    except NameError as e:
        lam = "NameError: " + str(e)


print(C.gv, gv, C.lst, C.doubled, C.lam)


def outer():
    c = 0

    def inner():
        c += 1

    try:
        inner()
    except UnboundLocalError as e:
        return "UnboundLocalError: " + str(e)


print(outer())


def late_binding():
    fs = [lambda: y for _ in range(2)]
    y = 5
    return [h() for h in fs]


print(late_binding())


def global_walrus():
    global gw
    [gw := i for i in range(3)]
    return gw


print(global_walrus(), gw)
x = "g"


def comp_shadow_global():
    global x
    return [x for x in range(2)], x


print(comp_shadow_global())


def lambda_walrus():
    f = lambda: [yy := 1 for _ in [0]] and yy
    return f()


print(lambda_walrus())


def del_cell():
    xx = 1

    def get():
        return xx

    del xx
    try:
        return get()
    except NameError as e:
        return type(e).__name__ + ": " + str(e)


print(del_cell())


def nested_comp_closure():
    return [[(lambda: i * j)() for j in range(3)] for i in range(3)]


print(nested_comp_closure())


def comp_uses_outer_after_rebind():
    n = 1
    gen = (n * k for k in range(3))
    n = 10
    return list(gen)


print(comp_uses_outer_after_rebind())


def class_in_function():
    val = "func-local"

    class Inner:
        val2 = val
        items = [val for _ in range(2)]
        after = val2 + "!"

    return Inner.val2, Inner.items, Inner.after


print(class_in_function())


def nonlocal_aug():
    total = 0

    def add(n):
        nonlocal total
        total += n
        return total

    add(3)
    add(4)
    return total


print(nonlocal_aug())


def comp_in_default_args(a=[i * i for i in range(3)], b={k: k for k in "ab"}):
    return a, b


print(comp_in_default_args())
# chained assignment creating a self-referential list
aa = aa_alias = [None]
aa[0] = aa
print(aa, aa_alias is aa)
bb = bb[0] = [None]
print(bb)


# keyword arguments named like soft keywords
def kw(match=0, case=0, _=0, type=0):
    return match + case + _ + type


print(kw(match=1, case=2, _=3, type=4))
match, case, _ = 1, 2, 3
print(match + case + _)
type_ = type
print(type_(1).__name__)
