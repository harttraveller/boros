import _scope_lazy
from _scope_lazy import lazy_thing, eager

print(_scope_lazy.lazy_abc, lazy_thing, eager, _scope_lazy._loaded)
print(dir(_scope_lazy), getattr(_scope_lazy, 'lazy_q', None), hasattr(_scope_lazy, 'other'))
try:
    _scope_lazy.other
except AttributeError as e:
    print('AttributeError:', e)
try:
    from _scope_lazy import other
except ImportError as e:
    print('ImportError:', str(e).split(' (')[0])
