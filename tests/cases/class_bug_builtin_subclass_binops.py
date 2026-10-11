# Operators between two instances of builtin subclasses (both operands are
# interpreted instances wrapping a host int/str/list/dict).

class I(int):
    pass


class S(str):
    pass


class L(list):
    pass


class D(dict):
    pass


a, b = I(2), I(3)
print(a + b, a * b, b - a, a ** b, b // a, b % a, divmod(b, a), a & b, a | b, a << b)
print(a < b, a <= b, a > b, a == I(2), a != I(2), a == b)
print(sorted([I(3), I(1), I(2)]), max(I(3), I(4)), min(I(5), I(6)))
print(len({I(1), I(1), 1}), I(5) in [I(5)], [I(1), I(2)].index(I(2)))
print(S('a') + S('b'), S('a') < S('b'), S('a') == S('a'), S('ab') > S('a'), S('a') in S('cab'))
print(L([1]) + L([2]), L([1]) == L([1]), L([1]) < L([2]))
print(D(a=1) == D(a=1), D(a=1) | D(b=2))
print(type(a + b).__name__, type(S('a') + S('b')).__name__, type(L([1]) + L([2])).__name__)
