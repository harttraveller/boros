# exec()/eval() inside a function body with default globals/locals (PEP 667
# semantics, Python 3.13): they see a snapshot of the function's locals, and
# writes made by exec do not change the function's real local variables.


def reads_locals():
    a = 10
    b = [1, 2]
    return eval('a + len(b)'), eval('b + [a]')


try:
    print('1', reads_locals())
except NameError as e:
    print('1 NameError:', e)


def exec_reads_locals():
    a = 5
    out = []
    exec('out.append(a * 2)')
    return out


try:
    print('2', exec_reads_locals())
except NameError as e:
    print('2 NameError:', e)


def exec_assign_does_not_rebind():
    x = 1
    exec('x = 2')
    return x


print('3', exec_assign_does_not_rebind())


def exec_new_name_not_visible():
    exec('brand_new = 5')
    return 'brand_new' in locals()


print('4', exec_new_name_not_visible())


def exec_into_explicit_dict():
    x = 1
    ns = {}
    exec('x = 2\ny = x * 3', globals(), ns)
    return x, ns


print('5', exec_into_explicit_dict())


def exec_with_locals_snapshot():
    x = 1
    snap = locals()
    exec('x = 99\nnew = x + 1', globals(), snap)
    return x, snap['x'], snap['new']


print('6', exec_with_locals_snapshot())


def exec_defines_global():
    exec('global made_global\nmade_global = "yes"')


exec_defines_global()
print('7', made_global)


def outer():
    captured = 3

    def inner():
        captured  # makes 'captured' a free variable of inner
        return eval('captured * 2')
    return inner()


try:
    print('8', outer())
except NameError as e:
    print('8 NameError:', e)


