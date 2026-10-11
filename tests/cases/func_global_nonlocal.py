# global and nonlocal declarations.

G = 0


def set_global():
    global G
    G = 5

    def inner():
        global G
        G += 1
    inner()


set_global()
print(G)


def create_global():
    global CREATED
    CREATED = 'made'


create_global()
print(CREATED)


def nested_global():
    def inner():
        global DEEP
        DEEP = 42
    inner()


nested_global()
print(DEEP)


# a local of the same name in another function is independent
def local_g():
    G = 'local'
    return G


print(local_g(), G)


# global declaration in an intermediate function: inner functions without
# their own declaration read the global
X = 'global X'


def mid():
    global X
    X = 'set in mid'

    def inner():
        return X
    return inner()


print(mid(), X)


# a nested function referencing a name the enclosing function declares global
def enc():
    global Y
    Y = 1

    def inner():
        return Y + 1
    return inner()


print(enc())


# nonlocal binds to the nearest enclosing function binding
def outer():
    x = 'outer'

    def middle():
        x = 'middle'

        def inner():
            nonlocal x
            x = 'inner'
        inner()
        return x
    return middle(), x


print(outer())


# nonlocal in a class body inside a function
def class_nonlocal():
    q = 1

    class I:
        nonlocal q
        q = 2
    return q


print(class_nonlocal())


# global in a class body
class H:
    global HG
    HG = 'from class'


print(HG, hasattr(H, 'HG'))


# del of a global through a declaration
GX = 1


def delg():
    global GX
    del GX


delg()
print('GX' in globals())
try:
    delg()
except NameError as e:
    print('NameError:', e)


# nonlocal then del
def nl_del():
    v = 1

    def kill():
        nonlocal v
        del v
    kill()
    try:
        return v
    except UnboundLocalError as e:
        return 'UnboundLocalError: ' + str(e)


print(nl_del())


# globals() is the module namespace
def g_dict():
    globals()['VIA_DICT'] = 7
    return globals() is g_dict.__globals__


print(g_dict(), VIA_DICT)


# augmented assignment through nonlocal and global
COUNT = 0


def bump_both():
    total = 10

    def inner():
        global COUNT
        nonlocal total
        COUNT += 1
        total *= 2
    inner()
    inner()
    return total


print(bump_both(), COUNT)
