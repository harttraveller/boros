# UnboundLocalError and NameError raised by function scoping rules.


def show(label, f):
    try:
        print(label, 'ok', f())
    except NameError as e:
        print(label, type(e).__name__ + ':', e, '| name =', getattr(e, 'name', None))


cnt = 0


def aug():
    cnt += 1


show('augmented global without declaration', aug)

x = 10


def read_before_assign():
    print(x)
    x = 5


show('read before assign', read_before_assign)


def cond(flag):
    if flag:
        v = 1
    return v


show('conditional true', lambda: cond(True))
show('conditional false', lambda: cond(False))


def after_del():
    a = 1
    del a
    return a


show('after del', after_del)


def exc_name():
    try:
        raise ValueError
    except ValueError as e:
        pass
    return e


show('except target cleared', exc_name)


def loop_never():
    for item in []:
        pass
    return item


show('loop never ran', loop_never)
show('undefined global', lambda: totally_missing)


def free_del():
    q = 1

    def inner():
        return q
    del q
    return inner()


show('free variable deleted', free_del)


def import_local():
    print(os.sep is not None)
    import os


show('import binds local', import_local)


def class_local():
    y = Foo

    class Foo:
        pass


show('class binds local', class_local)


def func_local():
    r = helper()

    def helper():
        return 1
    return r


show('def binds local', func_local)


def with_local():
    print(ctx)
    with open(__file__) as ctx:
        pass


show('with binds local', with_local)


def deleted_twice():
    z = 1
    del z
    del z


show('del twice', deleted_twice)


def match_local(v):
    print(cap)
    match v:
        case cap:
            pass


show('match capture binds local', lambda: match_local(1))


def walrus_local():
    print(wv)
    (wv := 1)


show('walrus binds local', walrus_local)


def comprehension_var():
    [leak for leak in range(3)]
    return leak


show('comprehension var does not leak', comprehension_var)


def nested_unbound():
    def g():
        return w
    r = None
    try:
        g()
    except NameError as e:
        r = type(e).__name__ + ': ' + str(e)
    w = 1
    return r


show('free var not yet bound', nested_unbound)


def del_global_undefined():
    global never_defined_zz
    del never_defined_zz


show('del undeclared global', del_global_undefined)


def local_shadows_builtin():
    print(len)
    len = 3


show('local shadows builtin', local_shadows_builtin)
print(issubclass(UnboundLocalError, NameError))
try:
    print(undefined_global_q)
except NameError as e:
    print(repr(e), e.name)
