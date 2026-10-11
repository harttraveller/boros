# locals() inside a nested function includes the free variables it uses.


def outer():
    a = 1
    b = 2

    def inner(c):
        d = a + c
        return sorted(locals().items())
    return inner(3)


print(outer())


def outer2():
    x = 1

    def inner():
        nonlocal x
        x += 1
        return sorted(locals())
    return inner(), x


print(outer2())


def outer3():
    v = 'v'

    def mid():
        def leaf():
            return v
        return sorted(locals()), leaf()
    return mid()


print(outer3())


def args_locals(a, *b, k=1, **c):
    return sorted(locals())


print(args_locals(1))
