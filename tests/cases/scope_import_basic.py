"""Main module docstring."""
import os
print('start')
import _scope_mod
import _scope_mod as m2
from _scope_mod import greet, VALUE as V, Thing

print(_scope_mod is m2)
print(_scope_mod.__name__, os.path.basename(_scope_mod.__file__))
print(greet('x'), V, Thing(3))
print(_scope_mod.bump(), _scope_mod.bump(), _scope_mod.counter)
import _scope_mod  # already loaded: the body must not run again
print(_scope_mod.counter, _scope_mod.get_counter_via_globals())


def f():
    import _scope_mod as inner
    from _scope_mod import bump
    return inner.counter, bump(), 'inner' in locals(), 'bump' in locals()


print(f())
print(_scope_mod.counter)
print('_scope_mod' in dir(), 'm2' in globals())
print(Thing.__module__, greet.__module__, greet.__name__, greet.__qualname__)
print(type(_scope_mod).__name__)
print(repr(_scope_mod.__package__))
print(__name__)
print(os.path.basename(__file__))
_scope_mod.newattr = 5
import _scope_mod as m3
print(m3.newattr)
print(sorted(k for k in vars(_scope_mod) if not k.startswith('__')))
print(sorted(k for k in dir(_scope_mod) if not k.startswith('__')))
print(hasattr(_scope_mod, '_private'), getattr(_scope_mod, 'nope', 'default'))
try:
    _scope_mod.nope
except AttributeError as e:
    print('AttributeError:', e)
# a function's globals are its module's globals
print(greet.__globals__ is vars(_scope_mod), greet.__globals__['VALUE'])
# rebinding a module global from outside is seen by the module's functions
_scope_mod.counter = 100
print(_scope_mod.bump(), _scope_mod.get_counter_via_globals())
# names imported with from-import are copies of the binding
from _scope_mod import counter
_scope_mod.bump()
print(counter, _scope_mod.counter)
# __import__ builtin
m4 = __import__('_scope_mod')
print(m4 is _scope_mod)
import os.path as osp
print(osp is os.path, osp.basename('/a/b.txt'))
import os.path
print(os.path.join('a', 'b'))
here = os.path.dirname(os.path.abspath(__file__)) + os.sep
print(repr(_scope_mod).replace(here, ''))
print('__builtins__' in vars(_scope_mod), callable(_scope_mod.__dict__['greet']))
# a __main__ guard inside exec'd code follows the __name__ in its globals
src = 'if __name__ == "__main__":\n    print("exec guard ran")\nelse:\n    print("exec guard skipped", __name__)\n'
exec(src, {'__name__': '__main__'})
exec(src, {'__name__': 'not_main'})
