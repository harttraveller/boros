before = set(globals())
from _scope_star_all import *
added = sorted(set(globals()) - before - {'before'})
print(added)
print(public_a, _semi_private)
try:
    public_b
except NameError as e:
    print('NameError:', e)
before = set(globals())
from _scope_star_noall import *
added = sorted(set(globals()) - before - {'before'})
print(added)
print(x1, x2, func(), Klass.__name__)
try:
    _hidden
except NameError as e:
    print('NameError:', e)
# star import of a host module
from math import *
print(floor(2.5), sqrt(16.0), pi > 3)
from string import *
print(ascii_lowercase[:5], capwords('hello world'))
