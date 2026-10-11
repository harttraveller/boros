# __closure__ is a tuple of cells (one per free variable, sorted by name)
# and __code__.co_freevars names them.


def outer():
    b = 2
    a = 1

    def inner():
        return a + b
    return inner


f = outer()
print(type(f.__closure__).__name__, len(f.__closure__))
print([c.cell_contents for c in f.__closure__])
print(f.__code__.co_freevars)


def no_free():
    return 1


print(no_free.__closure__)
print(outer.__closure__)


def counter():
    n = 0

    def inc():
        nonlocal n
        n += 1
        return n
    return inc


inc = counter()
cell = inc.__closure__[0]
print(cell.cell_contents)
inc()
inc()
print(cell.cell_contents, type(cell).__name__)


def unbound_cell():
    def g():
        return late
    c = g.__closure__[0]
    try:
        c.cell_contents
    except ValueError as e:
        print('ValueError:', e)
    late = 'now'
    return c.cell_contents


print(unbound_cell())
