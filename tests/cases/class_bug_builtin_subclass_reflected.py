# A builtin on the left, a builtin-subclass instance on the right.

class I(int):
    pass


class S(str):
    pass


class L(list):
    pass


print([0] + L([1]), 'x' + S('y'), 'ab' * I(2), [7] * I(2), (1,) * I(2))
print(3 + I(4), 10 - I(4), 2 ** I(3), 7 // I(2))
