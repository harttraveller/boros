print('a: start')
A1 = 'a1'
import _scope_circ_b
print('a: after importing b, b.B1 =', _scope_circ_b.B1)
A2 = 'a2'


def use_b():
    return _scope_circ_b.b_func()
