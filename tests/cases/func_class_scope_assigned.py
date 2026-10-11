# A name that is assigned somewhere in a class body is looked up in the class
# namespace, then the globals and builtins -- never in an enclosing function.
loc = 'global loc'


def f():
    loc = 'func local'
    shadow = 'func shadow'

    class C:
        a = loc
        loc = 'class level'
        b = loc
        try:
            s = shadow
        except NameError as e:
            s = 'NameError: ' + str(e)
        shadow = 'class shadow'

        def m(self):
            return loc, shadow
    return C


C = f()
print(C.a, C.b, C.s, C().m())


def g():
    only_func = 1

    class D:
        try:
            r = only_func
        except NameError as e:
            r = 'NameError: ' + str(e)
        only_func = 2
    return D


print(g().r)


def h():
    len = lambda x: 'func len'

    class E:
        before = len('ab')
        len = lambda x: 'class len'
        after = len('ab')
    return E


print(h().before, h().after)
