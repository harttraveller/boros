# Host library code that type-checks its arguments (C-level PyUnicode_Check,
# PyDict_Check, isinstance in json) must accept instances of builtin
# subclasses, including when they are nested inside containers.
import json


class S(str):
    pass


class L(list):
    pass


class D(dict):
    pass


class I(int):
    pass


print('-'.join(['x', S('y')]), ''.join(L(['a', S('b')])))
print(list(map(str.upper, [S('a'), 'b'])), sorted([S('b'), 'a'], key=str.lower))
print(json.dumps(D(a=1)), json.dumps(L([1, I(2)])), json.dumps(S('s')), json.dumps({'k': I(3)}))
print(json.dumps({S('key'): 1}), isinstance(S('x'), str))
