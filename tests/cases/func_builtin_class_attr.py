# Builtin functions stored as class attributes do not bind as methods, while
# plain functions do.


class A:
    check = isinstance
    get = getattr
    has = hasattr
    ln = len
    named = callable

    def __init__(self):
        self.x = 5


a = A()
print(a.ln([1, 2]), a.check(1, int), a.get(a, 'x'), a.has(a, 'x'), a.named(a))
print(A.check('s', str), A.ln('abc'))
