# Since Python 3.12 (PEP 709) list/set/dict comprehensions in exec/eval code
# are inlined, so they can read names from an explicit locals mapping.
# (Generator expressions still cannot.)
try:
    print('1', eval('[x * i for i in range(3)]', {}, {'x': 2}))
except NameError as e:
    print('1 NameError:', e)
ns = {}
try:
    exec('x = 3\ny = [x * i for i in range(3)]\nz = {k: x for k in "ab"}', {}, ns)
    print('2', ns)
except NameError as e:
    print('2 NameError:', e)
try:
    print(eval('list(x * i for i in range(3))', {}, {'x': 2}))
except NameError as e:
    print('3 NameError:', e)


def f():
    k = 4
    # eval inside a comprehension inside a function sees the function's locals
    return [eval('i * k') for i in range(3)]


try:
    print('4', f())
except NameError as e:
    print('4 NameError:', e)


def g():
    base = 10

    def inner():
        base  # free variable
        return [eval('base + j') for j in range(2)], [sorted(locals()) for j in range(1)]
    return inner()


try:
    print('5', g())
except NameError as e:
    print('5 NameError:', e)
