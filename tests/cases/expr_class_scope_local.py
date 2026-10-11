# In a class body, a name that is *assigned* in that class body is looked up
# in the class namespace, then globals/builtins -- never in an enclosing
# function's locals (LOAD_NAME semantics).  Names not assigned in the class
# body do see the enclosing function's variables.
def f1():
    val = "func-local"

    class Inner:
        items = [val for _ in range(2)]
        val = "class-level"
        after = val

    return Inner.items, Inner.after


print(f1())


def f2():
    val = "func-local"

    class Inner:
        try:
            v2 = val
        except NameError as e:
            v2 = "NameError: " + str(e)
        val = "class-level"

    return Inner.v2


print(f2())
len = "global len"


def f3():
    len = "func len"

    class Inner:
        got = len
        len = 5

    return Inner.got


print(f3())


def f4():
    val = "func-local"

    class Inner:
        v2 = val

        def m(self):
            return val

    return Inner.v2, Inner().m()


print(f4())
