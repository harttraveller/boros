# TypeErrors raised while matching class patterns.
class P:
    __match_args__ = ["x"]
    x = 1


class P1:
    __match_args__ = ("x",)
    x = 1


class P2:
    __match_args__ = (1,)


class P0:
    pass


notcls = len


def run(name, thunk):
    try:
        thunk()
    except TypeError as e:
        print(name, "TypeError:", e)


def t1():
    match P():
        case P(1):
            print("matched")


def t2():
    match P1():
        case P1(1, 2):
            print("matched")


def t3():
    match P2():
        case P2(1):
            print("matched")


def t4():
    match P0():
        case P0(1):
            print("matched")


def t5():
    match 5:
        case int(1, 2):
            print("matched")


def t6():
    match P1():
        case P1(1, x=1):
            print("matched")


def t7():
    match 5:
        case notcls():
            print("matched")


def t8():
    match 5:
        case P1(1, 2):
            print("not an instance: no error")
        case _:
            print("no match, no error")


for i, t in enumerate([t1, t2, t3, t4, t5, t6, t7, t8]):
    run("t%d" % (i + 1), t)
