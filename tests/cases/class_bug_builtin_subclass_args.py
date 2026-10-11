# Instances of str/int/list subclasses passed as arguments to host methods
# and functions that require the exact builtin type.

class S(str):
    pass


class I(int):
    pass


class L(list):
    pass


print(S('a,b').split(S(',')), S('abc').replace(S('b'), S('X')), 'abc'.startswith(S('ab')))
print(int(S('12')), float(S('1.5')), 'x'.center(I(5), S('*')))
print([1, 2, 3][I(1):I(2)], list(L([1, 2])), tuple(L([3])), sorted(L([2, 1])))
print({'k': 1}[S('k')], 'abc'.find(S('c')), str(S('s')), I(3).to_bytes(I(2), 'big'), bytes(S('x'), 'ascii'))
