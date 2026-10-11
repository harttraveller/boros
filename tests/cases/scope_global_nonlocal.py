counter = 0


def incr():
    global counter
    counter += 1
    return counter


print(incr(), incr(), counter)


def create_global():
    global created_later
    created_later = 'created in function'


create_global()
print(created_later)


def read_global_without_decl():
    return counter * 10


print(read_global_without_decl())


def shadow():
    counter = 'local'
    return counter


print(shadow(), counter)


def nested_global():
    def inner():
        global counter
        counter = 100
    inner()
    return counter


print(nested_global(), counter)


def global_in_nested_shadowing():
    counter = 'enclosing local'

    def inner():
        global counter
        return counter
    return inner(), counter


print(global_in_nested_shadowing())


# nonlocal
def make_counter():
    count = 0

    def inc(step=1):
        nonlocal count
        count += step
        return count
    return inc


c1 = make_counter()
c2 = make_counter()
print(c1(), c1(), c1(5), c2())


def three_levels():
    x = 'outer'

    def middle():
        def inner():
            nonlocal x
            x = 'set by inner'
        inner()
        return x
    r = middle()
    return r, x


print(three_levels())


def chained_nonlocal():
    v = 1

    def mid():
        nonlocal v
        v += 10

        def inner():
            nonlocal v
            v *= 2
        inner()
    mid()
    return v


print(chained_nonlocal())


def nonlocal_multiple():
    a, b = 1, 2

    def swap():
        nonlocal a, b
        a, b = b, a
    swap()
    return a, b


print(nonlocal_multiple())


def nonlocal_in_loop_closures():
    fs = []
    total = 0
    for i in range(3):
        def add(i=i):
            nonlocal total
            total += i
            return total
        fs.append(add)
    return [f() for f in fs], total


print(nonlocal_in_loop_closures())


def late_binding():
    fs = [lambda: i for i in range(3)]
    gs = [lambda i=i: i for i in range(3)]
    return [f() for f in fs], [g() for g in gs]


print(late_binding())


def class_in_function():
    secret = 'enclosing'

    class C:
        secret = 'class attr'
        seen_in_body = secret

        def method(self):
            return secret  # class scope is skipped: sees the enclosing function

        @staticmethod
        def change():
            nonlocal secret
            secret = 'changed via nonlocal in method'
    C.change()
    return C.seen_in_body, C().method(), secret


print(class_in_function())


class GlobalInClassBody:
    global from_class_body
    from_class_body = 'set in class body'
    x = 1


print(from_class_body, hasattr(GlobalInClassBody, 'from_class_body'))


x = 'module x'


class ClassReads:
    x = 'class x'
    y = [x for _ in range(1)]  # comprehension skips class scope: module x

    def m(self):
        return x


print(ClassReads.y, ClassReads().m())


def walrus_scopes():
    data = [1, 5, 9]
    if any((big := v) > 4 for v in data):
        pass
    [last := v for v in data]
    return big, last


print(walrus_scopes())
[module_walrus := n for n in 'ab']
print(module_walrus)


def deleting():
    global counter
    del counter
    try:
        counter
    except NameError as e:
        print('NameError:', e)
    counter = 'recreated'


deleting()
print(counter)


def unbound_local():
    try:
        print(counter)
        counter = 1
    except UnboundLocalError as e:
        print('UnboundLocalError:', e)


unbound_local()


def free_before_assignment():
    def inner():
        return late
    try:
        inner()
    except NameError as e:
        print('NameError:', e)
    late = 1
    return inner()


print(free_before_assignment())


def undefined_global():
    global never_defined
    try:
        return never_defined
    except NameError as e:
        return 'NameError: %s' % e


print(undefined_global())


def del_nonlocal():
    v = 1

    def inner():
        nonlocal v
        del v
    inner()
    try:
        return v
    except NameError as e:
        return type(e).__name__ + ': ' + str(e)


print(del_nonlocal())
