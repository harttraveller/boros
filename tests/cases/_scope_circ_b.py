print('b: start')
import _scope_circ_a
print('b: a is partially initialised:', hasattr(_scope_circ_a, 'A1'), hasattr(_scope_circ_a, 'A2'))
from _scope_circ_a import A1
B1 = 'b1:' + A1


def b_func():
    return 'b_func sees ' + _scope_circ_a.A2
