# Closures: late binding, loop variables, nonlocal, deep nesting, cells.

# late binding: every lambda sees the final value of the loop variable
fs = [lambda: i for i in range(3)]
print([f() for f in fs])
fs = [lambda i=i: i for i in range(3)]
print([f() for f in fs])
fs = []
for i in range(3):
    fs.append(lambda: i)
i = 'changed'
print([f() for f in fs])


def make_in_loop():
    out = []
    for j in range(3):
        def g():
            return j
        out.append(g)
    j = 100
    return out


print([f() for f in make_in_loop()])


def while_loop():
    fs = []
    n = 0
    while n < 3:
        fs.append(lambda: n)
        n += 1
    return [f() for f in fs]


print(while_loop())


# capturing a fresh scope per iteration via a factory
def factory(v):
    return lambda: v


print([f() for f in [factory(k) for k in 'abc']])


# nonlocal counters, shared between closures
def counter():
    n = 0

    def inc(step=1):
        nonlocal n
        n += step
        return n

    def get():
        return n

    def reset():
        nonlocal n
        n = 0
    return inc, get, reset


inc, get, reset = counter()
inc()
inc(5)
print(get())
reset()
print(get(), inc())
inc2, get2, _ = counter()
inc2()
print(get(), get2())


# three and four levels of nesting
def a():
    x = 1

    def b():
        y = 2

        def c():
            nonlocal x
            x += 10

            def d():
                z = 3

                def e():
                    return x + y + z
                return e()
            return d()
        return c
    return b


print(a()()())


def outer():
    v = 'outer'

    def mid():
        def inner():
            return v
        return inner
    v = 'rebound'
    return mid()


print(outer()())


# nonlocal skips an intermediate level that does not bind the name
def level1():
    target = 'L1'

    def level2():
        def level3():
            nonlocal target
            target = 'set by L3'
        level3()
        return target
    r = level2()
    return r, target


print(level1())


# an inner nonlocal rebinding is visible to sibling closures
def siblings():
    data = []
    total = 0

    def add(v):
        nonlocal total
        data.append(v)
        total += v

    def report():
        return list(data), total
    add(1)
    add(2)
    return report()


print(siblings())


# cell semantics: the closure follows rebinding and deletion
def rebinding():
    x = 1

    def get():
        return x
    r = [get()]
    x = 2
    r.append(get())
    del x
    try:
        get()
    except NameError as e:
        r.append(type(e).__name__ + ': ' + str(e))
    x = 3
    r.append(get())
    return r


for item in rebinding():
    print(item)


# closures see assignments made after their definition
def later():
    def g():
        return z
    z = 3
    return g()


print(later())


# closure over a parameter
def adder(n):
    def add(x):
        return x + n
    return add


add3 = adder(3)
print(add3(4), adder(10)(1))


# a closure that modifies a mutable captured object without nonlocal
def accumulate():
    acc = []

    def push(v):
        acc.append(v)
        return len(acc)
    return push, acc


push, acc = accumulate()
push('a')
push('b')
print(acc)


# closures created inside comprehensions capture the comprehension variable
def comp_closures():
    return [(lambda: k * 2) for k in range(3)], {k: (lambda: k) for k in 'xy'}


lst, dct = comp_closures()
print([f() for f in lst], {k: f() for k, f in dct.items()})


# generator closures share the cell with the enclosing function
def gen_counter():
    n = 0

    def g():
        nonlocal n
        while n < 3:
            n += 1
            yield n
    return g, lambda: n


g, peek = gen_counter()
it = g()
print(next(it), peek(), next(it), peek(), list(it), peek())


# methods of a class defined in a function close over the function's locals
def make_class():
    val = 0

    class K:
        def bump(self):
            nonlocal val
            val += 1
            return val

        def peek(self):
            return val
    return K


K = make_class()
k = K()
k.bump()
print(k.bump(), K().peek())


# closure over a name that is also a parameter of the inner function
def shadow(x):
    def inner(x):
        return x * 2
    return inner(x + 1), x


print(shadow(1))


# recursive inner function referring to itself through the closure
def make_fact():
    def fact(n):
        return 1 if n <= 1 else n * fact(n - 1)
    return fact


print(make_fact()(10))
